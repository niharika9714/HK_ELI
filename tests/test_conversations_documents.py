import copy
import pytest
from conftest import login,wait
from hk_platform.runtime.conversations import Conversations
from hk_platform.runtime.database import connect


def post(client,headers,question,conversation=None,**kwargs):
    response=client.post('/api/chat',json={'question':question,'conversation_id':conversation,**kwargs},headers=headers)
    assert response.status_code==202,response.json
    result=wait(client,response.json['run_id']);assert result['status']=='completed',result
    return response.json,result['answer']


def test_report_asks_format_and_resumes_saved_evidence(client,app,monkeypatch):
    headers=login(client);queued,source=post(client,headers,'Q1')
    def no_analysis(*args,**kwargs):raise AssertionError('A document follow-up must not rerun analysis')
    monkeypatch.setattr(app.extensions['platform']['services']['business'],'run',no_analysis)
    _,pending=post(client,headers,'Please prepare a report from that',queued['conversation_id'])
    assert pending['status']=='needs_format' and pending['artifacts']==[]
    assert pending['clarification']['options']==['docx','pptx','pdf','xlsx']
    _,document=post(client,headers,'PPTX',queued['conversation_id'])
    assert document['status']=='complete' and [a['format'] for a in document['artifacts']]==['pptx']
    assert document['evidence']==source['evidence']
    manifest=client.get(document['artifacts'][0]['url']+'?manifest=true').json
    assert manifest['document_context']['basis']=='saved verified evidence snapshot'
    assert manifest['evidence']==source['evidence']
    history=client.get('/api/v1/conversations/'+queued['conversation_id']).json['turns']
    assert len(history)==3 and history[-1]['answer']['artifacts']==document['artifacts']


def test_duplicate_planned_generation_is_consolidated_and_ui_format_wins(client,app,monkeypatch):
    headers=login(client);service=app.extensions['platform']['services']['artifacts'];original=service.generate;calls=[]
    def generate(*args,**kwargs):calls.append(args[2]);return original(*args,**kwargs)
    monkeypatch.setattr(service,'generate',generate)
    plan={'intent':{'question':'Prepare report'},'tasks':[{'id':'sales','skill_id':'eli.sales.performance'},
        {'id':'doc','skill_id':'artifact.generate','parameters':{'formats':['pdf','pdf']},'dependencies':['sales']}],
        'output':{'formats':['pdf']}}
    _,answer=post(client,headers,'Prepare report',plan=plan,formats=['docx'])
    assert calls==[['docx']] and len(answer['artifacts'])==1


def test_model_cannot_choose_pdf_for_unspecified_report(client,app,monkeypatch):
    from hk_platform.contracts.models import ExecutionPlan
    headers=login(client)
    async def plan(*args):return ExecutionPlan.model_validate({'intent':{'question':'Review sales and prepare report'},
        'tasks':[{'id':'sales','skill_id':'eli.sales.performance'},{'id':'doc','skill_id':'artifact.generate','parameters':{'formats':['pdf']},'dependencies':['sales']}],
        'output':{'formats':['pdf']}})
    monkeypatch.setattr(app.extensions['platform']['planner'],'plan',plan)
    def no_generation(*args):raise AssertionError('No format was chosen by the user')
    monkeypatch.setattr(app.extensions['platform']['services']['artifacts'],'generate',no_generation)
    _,answer=post(client,headers,'Review sales and prepare report')
    assert answer['status']=='needs_format' and not answer['artifacts'] and answer['evidence']


def test_followup_uses_latest_or_all_results_without_summing(client):
    headers=login(client);queued,first=post(client,headers,'Q1');cid=queued['conversation_id']
    _,second=post(client,headers,'Q4',cid)
    _,latest=post(client,headers,'Make an Excel document from the latest result',cid)
    assert latest['evidence']==second['evidence']
    # Existing generated documents must not duplicate the source evidence in an all-results draft.
    _,combined=post(client,headers,'Make a Word report from all results',cid)
    assert set(combined['evidence_ids'])==set(first['evidence_ids'])|set(second['evidence_ids'])
    assert len(combined['evidence'])==len(first['evidence'])+len(second['evidence'])


def test_context_owner_and_source_revocation(client,app):
    headers=login(client);queued,source=post(client,headers,'Q1');cid=queued['conversation_id']
    other=login(client,'synthetic-sg-rm')
    assert client.get('/api/v1/conversations/'+cid).status_code==404
    assert client.post('/api/chat',json={'question':'Make PDF','conversation_id':cid},headers=other).status_code==404
    headers=login(client);app.config['HKELI']['users'][0]['resources']=[]
    assert client.get('/api/v1/conversations/'+cid).status_code==403
    assert client.post('/api/chat',json={'question':'Make PDF','conversation_id':cid},headers=headers).status_code==403


def test_saved_results_survive_job_expiry_and_conversation_store_restart(client,app):
    headers=login(client);queued,source=post(client,headers,'Q1');cid=queued['conversation_id']
    with app.extensions['jobs'].db() as db:db.execute('DELETE FROM jobs')
    store=app.extensions['conversations'];app.extensions['conversations']=Conversations(store.path,store.ttl)
    _,document=post(client,headers,'Generate PDF from previous result',cid)
    assert document['evidence']==source['evidence'] and document['artifacts'][0]['format']=='pdf'


def test_expired_deleted_and_cross_chat_context_is_not_reused(client,app):
    headers=login(client);queued,_=post(client,headers,'Q1');cid=queued['conversation_id']
    created=client.post('/api/v1/conversations',json={},headers=headers).json['conversation_id']
    assert client.post('/api/chat',json={'question':'Make PDF','conversation_id':created,'context_turn_ids':[queued['turn_id']]},headers=headers).status_code==404
    assert client.delete('/api/v1/conversations/'+created,headers=headers).status_code==200
    assert client.get('/api/v1/conversations/'+created).status_code==404
    with connect(app.extensions['conversations'].path) as db:db.execute('UPDATE conversations SET expires=0 WHERE id=?',(cid,))
    assert client.get('/api/v1/conversations/'+cid).status_code==404


def test_document_access_rechecks_source_permissions(client,app):
    headers=login(client);_,answer=post(client,headers,'Q1',formats=['pdf'])
    app.config['HKELI']['users'][0]['permissions'].remove('analytics.read')
    assert client.get(answer['artifacts'][0]['url']).status_code==403


def test_pending_session_turn_prevents_parallel_context_races(client,app):
    headers=login(client);cid=client.post('/api/v1/conversations',json={},headers=headers).json['conversation_id']
    store=app.extensions['conversations'];turn=store.begin('synthetic-hk-rm',cid,'Reserved test turn')
    assert client.post('/api/chat',json={'question':'Q1','conversation_id':cid},headers=headers).status_code==429
    store.finish(turn,status='cancelled')


def test_live_document_router_receives_bounded_history_and_rejects_invented_turns():
    import asyncio
    from app.services.documents import document_followup,history_reference
    from hk_platform.contracts.models import Narrative
    history=[{'id':'owned','question':'Earlier authorized analysis','status':'completed','answer':{'evidence':[{'id':'e1'}],'narrative':{},'source_modes':['MOCK']}}]
    class Model:
        async def structured(self,instructions,payload,model,usage):
            assert payload['history']==history_reference(history)
            return model(action='document',scope='selected',source_turn_ids=['someone-else'])
    with pytest.raises(ValueError,match='absent'):asyncio.run(document_followup('Write that up',history,Model(),[]))


def test_live_source_is_reauthorized_before_historical_document(app,identity,monkeypatch):
    from app.services.authorization import authorize_answer
    import threading
    platform=app.extensions['platform'];service=platform['services']['tableau']
    identity=identity.model_copy(update={'resources':identity.resources+['SYN-DASH']})
    answer={'authorization_context':{'country':'HK','line_of_business':'Wealth'},'selected_dashboards':['SYN-DASH'],
        'evidence':[{'source_mode':'LIVE','source_type':'tableau_csv','source_id':'REVOKED','authorization_scope':[identity.id,'SYN-DASH']}]}
    calls=[]
    def discover(user,dashboards):calls.append(dashboards);return []
    monkeypatch.setattr(service,'discover',discover)
    with pytest.raises(PermissionError):authorize_answer(identity,answer,platform,True)
    assert calls==[['SYN-DASH']]


def test_multiple_formats_in_one_followup_and_no_pdf_default(client):
    headers=login(client);queued,source=post(client,headers,'Q1')
    _,answer=post(client,headers,'Create DOCX and XLSX from that',queued['conversation_id'])
    assert [a['format'] for a in answer['artifacts']]==['docx','xlsx']
    _,pending=post(client,headers,'Make a report',queued['conversation_id'])
    assert pending['status']=='needs_format' and not pending['artifacts']


def test_document_generation_requires_artifact_permission(client,app):
    headers=login(client);queued,_=post(client,headers,'Q1')
    app.config['HKELI']['users'][0]['permissions'].remove('artifact.write')
    response=client.post('/api/chat',json={'question':'Make PDF','conversation_id':queued['conversation_id']},headers=headers)
    assert response.status_code==202
    result=wait(client,response.json['run_id'])
    assert result['status']=='failed' and result['error']['code']=='access_denied'


def test_chat_context_does_not_change_reporting_dates(client):
    headers=login(client);queued,original=post(client,headers,'Q6')
    _,report=post(client,headers,'Generate PDF from previous result',queued['conversation_id'])
    assert {e['as_of'] for e in report['evidence']}=={e['as_of'] for e in original['evidence']}
    assert report['document_context']['source_run_ids']==[original['request_id']]


def test_format_answer_keeps_original_run_provenance(client):
    headers=login(client);queued,original=post(client,headers,'Q1');cid=queued['conversation_id']
    _,pending=post(client,headers,'Prepare a report',cid)
    _,answer=post(client,headers,'PDF',cid)
    assert answer['document_context']['source_run_ids']==[original['request_id']]
    assert answer['document_context']['source_questions']==['Q1']
