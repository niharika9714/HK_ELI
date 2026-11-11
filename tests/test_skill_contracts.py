"""Exercise every registered skill through its public typed contract with explicit test doubles."""
import asyncio
import io
import threading
import pytest
from hk_platform.runtime.registry import SkillContext
from hk_platform.contracts.models import SkillOutput,EvidenceRecord

def test_every_skill_executes_with_typed_inputs(app,identity):
    from PIL import Image
    image=io.BytesIO();Image.new('RGB',(20,20),'white').save(image,'PNG')
    class TableauDouble:
        config=app.config['HKELI']
        view={'id':'SYN-VIEW','name':'Synthetic test view','workbook_content_url':'SYN-WB','definition':{'verified_export':True,'columns':{'Value':{'type':'number','unit':'hkd','additive':True}}}}
        def discover(self,*args):return [self.view]
        def resolve(self,*args):return self.view
        def embed(self,*args):return SkillOutput(visualizations=[{'type':'tableau','view_id':'SYN-VIEW'}])
        def analyze(self,*args):return SkillOutput(data={'rows':[{'value':'10'}]})
        def download(self,identity,view,request,path):path.write_text('Group,Value\na,10\nb,20\n')
        def chart_image(self,*args):return image.getvalue()
    platform=app.extensions['platform'];services=dict(platform['services']);services.update(tableau=TableauDouble(),usage=[],question='Synthetic contract test',images=[])
    evidence=[EvidenceRecord(id='test'+str(i),source_type='test',source_mode='MOCK',source_id='mock:business',source_version='1',as_of='2026-10-15',authorization_scope=['HK'],grain='synthetic date',value=str(10+i),metric='value',unit='HKD',calculation_id='test') for i in range(2)]
    source=SkillOutput(data={'rows':[{'date':'2026-01-01','value':'10'},{'date':'2026-01-02','value':'11'}],'additive_columns':['value']},evidence=evidence)
    context=SkillContext(identity,'unit-contract',services,threading.Event(),{'source':source})
    async def scenario():
        covered=set();artifact=None
        for (name,_),skill in platform['registry'].skills.items():
            if name.startswith('eli.pricing'):params={'basket':['SYN-STOCK'],'tenor_months':6}
            elif name.startswith('eli.'):params={}
            elif name=='tableau.view.discover':params={'dashboards':[]}
            elif name=='tableau.view.compare':params={'views':[{'dashboard':'SYN','view_id':'SYN-VIEW'}]*2}
            elif name=='tableau.insight.generate':params={'question':'Summarize supported facts'}
            elif name.startswith('tableau.'):params={'dashboard':'SYN','view_id':'SYN-VIEW'}
            elif name.startswith('knowledge.'):params={'query':'test','dashboards':[]}
            elif name.startswith('analytics.'):
                op=name.rsplit('.',1)[1];params={'source_task':'source','column':'value','operation':'sum' if op=='aggregate' else op,'date_column':'date'}
            elif name=='artifact.generate':params={'formats':['pdf']}
            else:params={'artifact_id':artifact}
            if name=='tableau.data.analyze':params['analysis']={'action':'analyze','view_id':'SYN-VIEW','dimensions':['Group'],'measure':'Value','aggregation':'sum'}
            output=await skill.execute(skill.input_model.model_validate(params),context)
            SkillOutput.model_validate(output);covered.add(name)
            if name=='artifact.generate':
                assert output.data['document_request']['formats']==['pdf']
                from services.artifacts.templates import prepare_documents
                answer={'evidence':[e.model_dump() for e in evidence],'narrative':{}}
                answer['document_plans']=await prepare_documents(services['artifacts'].templates,'PDF',answer,['pdf'])
                artifact=services['artifacts'].generate(identity.id,answer,['pdf'])[0]['id']
        assert len(covered)==len(platform['registry'].skills)
    asyncio.run(scenario())

def test_private_stork_contract_is_mocked_not_network(monkeypatch):
    import sys,types,json
    from hk_platform.ai.gateway import StorkGateway
    from hk_platform.contracts.models import Narrative
    calls=[]
    async def generate_content(**kwargs):
        calls.append(kwargs);return types.SimpleNamespace(text='{"summary":[],"insights":[],"recommended_actions":[]}')
    client=lambda:types.SimpleNamespace(aio=types.SimpleNamespace(models=types.SimpleNamespace(generate_content=generate_content)))
    monkeypatch.setitem(sys.modules,'ada_genai',types.ModuleType('ada_genai'))
    module=types.ModuleType('ada_genai.google_genai');module.VertexClient=client
    monkeypatch.setitem(sys.modules,'ada_genai.google_genai',module)
    gateway=StorkGateway({'model':'TEST-MODEL','timeout_seconds':1});usage=[]
    async def scenario():
        for i in range(6):await gateway.structured('test',{'source':'SYNTHETIC'},Narrative,usage)
        with pytest.raises(ValueError):await gateway.structured('test',{},Narrative,usage)
    asyncio.run(scenario())
    assert len(calls)==6 and set(calls[0])=={'model','content'}
    assert all(u['status']=='completed' and 'estimated' in u['accounting'] for u in usage)
