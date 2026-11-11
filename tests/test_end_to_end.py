import json
import pytest
from conftest import login,wait

@pytest.mark.parametrize('code',range(1,10))
def test_nine_scenarios(client,code):
    headers=login(client)
    response=client.post('/api/v1/requests',json={'question':f'Q{code}: synthetic scenario'},headers=headers)
    assert response.status_code==202,response.json
    result=wait(client,response.json['run_id'])
    assert result['status']=='completed',result
    answer=result['answer'];assert answer['status']=='complete',answer['warnings']
    assert answer['evidence'] and answer['source_modes']==['MOCK']
    assert all(e['value'] is None or isinstance(e['value'],str) for e in answer['evidence'])
    assert len(answer['report_sections'])==14 if code==2 else True
    assert 'secret' not in json.dumps(answer).lower()

def test_csrf_owner_and_local_guard(client):
    assert client.post('/api/login',json={'user_id':'synthetic-hk-rm'}).status_code==403
    headers=login(client)
    key=client.post('/api/chat',json={'question':'Q1'},headers=headers).json['job_id'];wait(client,key)
    login(client,'synthetic-sg-rm')
    assert client.get('/api/jobs/'+key).status_code==404
    assert client.get('/api/session',headers={'X-Forwarded-For':'127.0.0.1'}).status_code==403

def test_page_and_skills(client):
    assert client.get('/').status_code==200
    login(client)
    skills=client.get('/api/v1/skills').json['skills']
    assert len(skills)>=33 and all(s['input_schema'] and s['output_schema'] for s in skills)
    assert client.get('/api/v1/ready').json['live_connections']=='not_probed'

def test_unknown_live_question_has_no_silent_mock_fallback(client):
    headers=login(client)
    key=client.post('/api/chat',json={'question':'Give me live prices now'},headers=headers).json['job_id']
    result=wait(client,key);assert result['status']=='failed'

@pytest.mark.parametrize('fmt',['docx','pptx','pdf','xlsx'])
def test_download_artifact(client,fmt):
    headers=login(client)
    key=client.post('/api/chat',json={'question':'Q1','formats':[fmt]},headers=headers).json['job_id']
    answer=wait(client,key)['answer'];assert answer['artifacts'],answer['warnings']
    url=answer['artifacts'][0]['url'];data=client.get(url)
    assert data.status_code==200
    assert len(data.data)>1000
    import io
    if fmt=='docx':
        from docx import Document
        doc=Document(io.BytesIO(data.data));assert doc.inline_shapes
        assert any('Evidence register' in p.text for p in doc.paragraphs)
    elif fmt=='pptx':
        from pptx import Presentation
        prs=Presentation(io.BytesIO(data.data));assert len(prs.slides)>2
        assert any('Evidence appendix' in s.shapes.title.text for s in prs.slides)
    elif fmt=='xlsx':
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(data.data));assert book['Evidence'].max_row>2 and 'Chart 1' in book.sheetnames
    else:assert data.data.startswith(b'%PDF') and b'%%EOF' in data.data[-100:]
    assert client.get(url+'?manifest=true').json['source_modes']==['MOCK']
    login(client,'synthetic-sg-rm');assert client.get(url).status_code==404

def test_explicit_plan_cannot_add_authority(client):
    headers=login(client)
    response=client.post('/api/chat',json={'question':'bad','plan':{'intent':{'question':'bad'},'tasks':[{'id':'t','skill_id':'system.execute','parameters':{}}]}},headers=headers)
    assert response.status_code==400

def test_pricing_input_errors(client):
    headers=login(client)
    assert client.post('/api/v1/pricing/solve',json={'basket':[],'tenor_months':-1},headers=headers).status_code==400
