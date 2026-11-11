import asyncio
import copy
import threading
import pytest
from hk_platform.contracts.models import ExecutionPlan,SkillOutput,EvidenceRecord,Narrative,Claim
from hk_platform.runtime.coverage import validate_coverage
from app.services.orchestrator import run
from hk_platform.contracts.models import Request


def filter_plan():
    return {'intent':{'question':'Show only KO'},'tasks':[{'id':'view','skill_id':'tableau.view.embed',
        'parameters':{'dashboard':'SYN','view_id':'SYN-VIEW','filters':{'Result':['KO']}}}],
        'requirements':[{'id':'ko','quote':'only KO','kind':'condition','interpretation':'Retain only KO','expected_value':['KO']}],
        'coverage':[{'requirement_id':'ko','status':'satisfied','task_ids':['view'],
            'bindings':[{'task_id':'view','parameter_path':'/filters/Result'}],'reason':'Exact verified native filter'}]}


def test_rich_guidance_for_every_production_skill(app):
    for skill in app.extensions['platform']['registry'].skills.values():
        meta=skill.metadata()
        assert meta.description!=meta.id.replace('.',' ')
        assert meta.use_when and meta.do_not_use_when and meta.limitations and meta.capabilities
        for example in meta.examples:
            assert example['synthetic_example']
            skill.input_model.model_validate(example['parameters'])


@pytest.mark.parametrize('mutation',['missing','wrong_value','bad_quote','unknown_task','unknown_path','duplicate','one_binding_for_two_views'])
def test_coverage_rejects_dropped_or_forged_conditions(mutation):
    raw=filter_plan()
    if mutation=='missing':raw['coverage']=[]
    elif mutation=='wrong_value':raw['tasks'][0]['parameters']['filters']['Result']=['EX']
    elif mutation=='bad_quote':raw['requirements'][0]['quote']='invented condition'
    elif mutation=='unknown_task':raw['coverage'][0]['task_ids']=['missing']
    elif mutation=='unknown_path':raw['coverage'][0]['bindings'][0]['parameter_path']='/filters/Missing'
    elif mutation=='duplicate':raw['coverage']*=2
    else:
        extra=copy.deepcopy(raw['tasks'][0]);extra['id']='second';raw['tasks'].append(extra)
        raw['coverage'][0]['task_ids'].append('second')
    with pytest.raises(ValueError):validate_coverage(ExecutionPlan.model_validate(raw))


def test_inventory_cannot_be_rewritten_and_source_cannot_be_relabelled():
    plan=ExecutionPlan.model_validate(filter_plan());validate_coverage(plan)
    original=copy.deepcopy(plan.requirements);plan.requirements[0].expected_value=['EX']
    with pytest.raises(ValueError):validate_coverage(plan,expected_requirements=original)
    raw=filter_plan()
    raw['requirements'][0].update(kind='source',expected_value='LIVE')
    raw['tasks'][0]['source_mode']='MOCK';raw['coverage'][0]['bindings']=[{'task_id':'view','target':'task','parameter_path':'/source_mode'}]
    with pytest.raises(ValueError):validate_coverage(ExecutionPlan.model_validate(raw))


QUESTION='Show maturity view and mock six-month quote for SYN-STOCK0'
REQUIREMENTS=[
    {'id':'view','quote':'maturity view','kind':'output','interpretation':'Original Tableau maturity view'},
    {'id':'quote','quote':'mock six-month quote','kind':'output','interpretation':'Indicative mock coupon'},
    {'id':'tenor','quote':'six-month','kind':'pricing_input','interpretation':'Six month tenor','expected_value':6},
    {'id':'basket','quote':'SYN-STOCK0','kind':'pricing_input','interpretation':'Requested synthetic underlying','expected_value':['SYN-STOCK0']}]


class MultiModel:
    def __init__(self,outage=False,allow_mock=True,forged=False):self.calls=[];self.outage=outage;self.allow_mock=allow_mock;self.forged=forged
    async def structured(self,instructions,payload,model,usage):
        self.calls.append((model.__name__,payload))
        if model.__name__=='Discovery':return model.model_validate({'domains':['tableau','hk_eli'],'concepts':['maturity','coupon'],
            'allow_mock_sources':self.allow_mock,'requirements':REQUIREMENTS})
        if model.__name__=='ExecutionPlan':
            tasks=[{'id':'pricing','skill_id':'eli.pricing.solve_coupon','parameters':{'basket':['SYN-STOCK0'],'tenor_months':6},'source_mode':'MOCK'}]
            coverage=[{'requirement_id':r['id'],'status':'satisfied','task_ids':['pricing'],'reason':'Requested synthetic quote',
                'bindings':[{'task_id':'pricing','parameter_path':'/tenor_months' if r['id']=='tenor' else '/basket'}] if r['id'] in ('tenor','basket') else []} for r in REQUIREMENTS[1:]]
            if self.outage:
                coverage.insert(0,{'requirement_id':'view','status':'unresolved','reason':'Tableau discovery unavailable; original view cannot be identified.'})
            else:
                tasks.insert(0,{'id':'view','skill_id':'tableau.view.embed','parameters':{'dashboard':'SYN-DASH','view_id':'SYN-VIEW'},'source_mode':'LIVE'})
                coverage.insert(0,{'requirement_id':'view','status':'satisfied','task_ids':['view'],'reason':'Exact discovered view'})
            if self.forged:tasks.append({'id':'unadvertised','skill_id':'knowledge.search','parameters':{}})
            return model.model_validate({'intent':{'question':QUESTION},'tasks':tasks,'requirements':payload['requirements'],'coverage':coverage,
                'source_assessments':[{'match':'no_match' if self.outage else 'complete_match','reason':'Discovery unavailable' if self.outage else 'Discovered exact original view'}]})
        fact=payload['facts'][0];return Narrative(summary=[Claim(text=fact['value'],evidence_ids=[fact['id']])])


def prepare(app,identity,monkeypatch,model):
    platform=app.extensions['platform'];platform['planner'].gateway=model;platform['services']['gateway']=model
    identity=identity.model_copy(update={'resources':identity.resources+['SYN-DASH']})
    def discover(user,selected):
        assert selected==['SYN-DASH']
        if model.outage:raise TimeoutError('sensitive upstream detail')
        return [{'id':'SYN-VIEW','name':'Synthetic maturity view','dashboard':'SYN-DASH','workbook_content_url':'SYN-WB','definition':{}}]
    def embed(user,request):
        e=EvidenceRecord(id='live-view',source_type='tableau_embed',source_mode='LIVE',source_id='SYN-VIEW',source_version='1',
            as_of='unknown',authorization_scope=[user.id,'SYN-DASH'],grain='published view',calculation_id='display')
        return SkillOutput(evidence=[e],visualizations=[{'type':'tableau','view_id':'SYN-VIEW','source_mode':'LIVE'}])
    monkeypatch.setattr(platform['services']['tableau'],'discover',discover)
    monkeypatch.setattr(platform['services']['tableau'],'embed',embed)
    return platform,identity


@pytest.mark.parametrize('outage',[False,True])
def test_multi_domain_branches_preserve_live_mock_and_partial_results(app,identity,monkeypatch,outage):
    model=MultiModel(outage);platform,identity=prepare(app,identity,monkeypatch,model)
    answer=asyncio.run(run(platform,identity,Request(question=QUESTION,dashboards=['SYN-DASH']), 'test',threading.Event(),lambda *args:None))
    assert answer['status']==('partial' if outage else 'complete')
    assert answer['source_modes']==(['MOCK'] if outage else ['LIVE','MOCK'])
    assert answer['analysis']['results']['pricing']['status']=='indicative_only'
    assert answer['requirement_coverage']['status']=='checked'
    ids={m['id'] for m in model.calls[1][1]['skills']}
    assert {'eli.pricing.solve_coupon','tableau.view.embed'}.issubset(ids)
    assert 'knowledge.search' not in ids
    if outage:
        assert any('Unresolved' in w for w in answer['warnings'])
        assert 'sensitive upstream detail' not in str(model.calls)
        assert model.calls[1][1]['source_availability'][0]['status']=='unavailable'


@pytest.mark.parametrize('allow_mock,forged',[(False,False),(True,True)])
def test_planner_cannot_call_unadvertised_or_unapproved_mock_skills(app,identity,monkeypatch,allow_mock,forged):
    model=MultiModel(allow_mock=allow_mock,forged=forged);platform,identity=prepare(app,identity,monkeypatch,model)
    with pytest.raises(PermissionError):asyncio.run(run(platform,identity,Request(question=QUESTION,dashboards=['SYN-DASH']), 'test',threading.Event(),lambda *args:None))


def test_unresolved_missing_pricing_terms_does_not_invoke_pricing(app,identity,monkeypatch):
    requirement={'id':'quote','quote':'mock quote','kind':'output','interpretation':'Requested quote missing basket and tenor'}
    class Model:
        async def structured(self,instructions,payload,model,usage):
            if model.__name__=='Discovery':return model.model_validate({'domains':['hk_eli'],'concepts':['pricing'],'allow_mock_sources':True,'requirements':[requirement]})
            return model.model_validate({'intent':{'question':'Prepare mock quote'},'tasks':[],'requirements':[requirement],
                'coverage':[{'requirement_id':'quote','status':'unresolved','reason':'Basket and tenor are missing; no quote was requested from the service.'}]})
    platform=app.extensions['platform'];platform['planner'].gateway=Model()
    def forbidden(*args):raise AssertionError('Pricing must not run with missing inputs')
    monkeypatch.setattr(platform['services']['pricing'],'solve',forbidden)
    answer=asyncio.run(run(platform,identity,Request(question='Prepare mock quote'), 'missing',threading.Event(),lambda *args:None))
    assert answer['status']=='partial' and answer['evidence']==[] and answer['task_statuses']=={}


def test_planner_catalog_deduplicates_schemas_without_losing_guidance(app,identity):
    import json
    from hk_platform.ai.planner import Planner
    skills=app.extensions['platform']['registry'].list_authorized(identity)
    catalog,schemas=Planner.skill_catalog(skills)
    assert len(catalog)==len(skills) and len(schemas)<len(catalog)
    assert len(json.dumps({'skills':catalog,'input_schemas':schemas}))<60000
    for entry,original in zip(catalog,skills):
        assert entry['use_when']==original.use_when
        assert schemas[entry['input_schema_ref']]==original.input_schema


def test_runtime_rejects_mixed_mode_relabelling(app,identity):
    from hk_platform.runtime.registry import Executor,SkillContext,SkillRegistry
    from domains.hk_eli.skills import Skill,BusinessInput
    async def wrong(i,c):return SkillOutput(data={'source_mode':'LIVE'})
    registry=SkillRegistry();registry.register(Skill('test','analytics',BusinessInput,wrong))
    plan=ExecutionPlan.model_validate({'intent':{'question':'test'},'tasks':[{'id':'t','skill_id':'test','source_mode':'MOCK'}]})
    out,statuses,_=asyncio.run(Executor(registry).execute(plan,SkillContext(identity,'test',{},threading.Event())))
    assert statuses['t']=='failed' and not out


def test_no_unauthorized_tableau_discovery_for_a_classified_branch(app,identity,monkeypatch):
    model=MultiModel();platform,identity=prepare(app,identity,monkeypatch,model)
    identity=identity.model_copy(update={'permissions':[p for p in identity.permissions if p!='tableau.read']})
    def forbidden(*args):raise AssertionError('Unauthorized discovery must not run')
    monkeypatch.setattr(platform['services']['tableau'],'discover',forbidden)
    with pytest.raises(PermissionError):asyncio.run(run(platform,identity,Request(question=QUESTION,dashboards=['SYN-DASH']), 'test',threading.Event(),lambda *args:None))


def test_missing_coverage_is_rejected_before_any_service_execution(app,identity,monkeypatch):
    model=MultiModel();platform,identity=prepare(app,identity,monkeypatch,model)
    original=model.structured
    async def broken(instructions,payload,schema,usage):
        result=await original(instructions,payload,schema,usage)
        if schema.__name__=='ExecutionPlan':result.coverage=[]
        return result
    model.structured=broken
    def forbidden(*args):raise AssertionError('Pricing cannot run on an uncovered plan')
    monkeypatch.setattr(platform['services']['pricing'],'solve',forbidden)
    with pytest.raises(ValueError,match='coverage'):asyncio.run(run(platform,identity,Request(question=QUESTION,dashboards=['SYN-DASH']), 'test',threading.Event(),lambda *args:None))
