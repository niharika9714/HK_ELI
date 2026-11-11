import asyncio
import json
import sqlite3
import time
import pytest
from hk_platform.ai.gateway import parse,validate_narrative,narrate
from hk_platform.contracts.models import Narrative,Claim,EvidenceRecord,QuoteInput
from services.tableau.service import TableauService,ViewRequest
from services.pricing.service import MockPricing,LivePricing
from hk_platform.runtime.jobs import JobManager
from services.knowledge.service import Knowledge

def fact():return EvidenceRecord(id='e1',source_type='test',source_mode='MOCK',source_id='mock:business',source_version='1',as_of='2026-10-15',authorization_scope=['HK'],grain='test',value='100',calculation_id='sum')

def test_grounding_and_json():
    for text in ['{"summary":[],"summary":[]}','{"summary":NaN}','{"summary":[],"sql":"DROP"}']:
        with pytest.raises(ValueError):parse(text,Narrative)
    for n in [Narrative(summary=[Claim(text='100',evidence_ids=['unknown'])]),Narrative(summary=[Claim(text='999',evidence_ids=['e1'])])]:
        with pytest.raises(ValueError):validate_narrative(n,[fact()])
    assert validate_narrative(Narrative(summary=[Claim(text='100',evidence_ids=['e1'])]),[fact()])
    with pytest.raises(ValueError):validate_narrative(Narrative(summary=[Claim(text='Largest allocation is 100',evidence_ids=['e1'])]),[fact()])

def test_narration_outage_keeps_evidence():
    class Broken:
        async def structured(self,*args):raise ConnectionError('private error')
    result=asyncio.run(narrate(Broken(),'test',[fact()],[]))
    assert result.summary[0].evidence_ids==['e1']
    assert 'private' not in result.model_dump_json()

def test_tableau_controls_and_default_scope(settings,identity,monkeypatch,tmp_path):
    service=TableauService(settings,None)
    view={'id':'SYN-VIEW','dashboard':'SYN-DASH','name':'Synthetic worksheet','sheet_type':'worksheet',
          'url':'https://tableau.example.com/views/SYN/Sheet','definition':{'native_controls_verified':True,'filters':{'Result':['KO','EX']},'parameters':{'Period':['5']},'highlights':{'Result':['KO']}}}
    monkeypatch.setattr(service,'discover',lambda identity,selected:[view])
    default=ViewRequest(dashboard='SYN-DASH',view_id='SYN-VIEW')
    visual=service.embed(identity,default).visualizations[0]
    assert visual['filters']=={} and visual['hide_tabs'] is True
    selected=default.model_copy(update={'filters':{'Result':['KO']}})
    assert service.embed(identity,selected).visualizations[0]['filters']=={'Result':['KO']}
    with pytest.raises(ValueError):service.resolve(identity,default.model_copy(update={'filters':{'Result':['UNKNOWN']}}))
    with pytest.raises(PermissionError):service.resolve(identity,default.model_copy(update={'view_id':'outside'}))
    with pytest.raises(ValueError):service.analyze(identity,default,'run')
    assert service.embed(identity,default).visualizations # Analytics failure does not destroy native view.
    with pytest.raises(ValueError):service.download(identity,view,default.model_copy(update={'parameters':{'Period':'5'}}),tmp_path/'x')

def test_download_native_filters_match(settings,identity,monkeypatch,tmp_path):
    from contextlib import contextmanager
    import services.tableau.service as module
    calls=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,n):yield b'Value\n100\n'
    class Transport:
        def get(self,url,**kwargs):calls.append((url,kwargs));return Response()
    class Fake:
        verify=True
        def __init__(self,*args):pass
        @contextmanager
        def session(self):yield Transport(),'https://tableau.example.com/api/3.28/sites/SYN'
        def check(self,response):pass
    monkeypatch.setattr(module,'Tableau',Fake)
    service=TableauService(settings,None)
    req=ViewRequest(dashboard='SYN',view_id='SYN-V',filters={'Result':['KO','EX']})
    path=tmp_path/'export.csv';service.download(identity,{'id':'SYN-V'},req,path)
    assert calls[0][1]['params']=={'vf_Result':'KO,EX'} and calls[0][1]['allow_redirects'] is False
    assert path.read_text().startswith('Value')

def test_pricing_defaults_and_no_live_substitute(identity):
    pricing=MockPricing();terms=QuoteInput(basket=['SYN-STOCK'],tenor_months=6)
    a=pricing.solve(terms,identity);b=pricing.solve(terms,identity)
    assert a.data['solved_value']==b.data['solved_value']
    assert 'ki_level' in a.data['applied_defaults'] and a.data['status']=='indicative_only'
    with pytest.raises(ValueError):LivePricing().solve(terms,identity)

def test_restart_and_expiry(tmp_path):
    path=tmp_path/'jobs.sqlite';manager=JobManager(path)
    with manager.db() as db:db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?)',('run','owner','running',time.time(),time.time()+30,None,'[]'))
    manager.close();new=JobManager(path)
    try:
        assert new.get('owner','run')['status']=='interrupted'
        with pytest.raises(KeyError):new.get('other','run')
        with new.db() as db:db.execute('UPDATE jobs SET expires=0')
        with pytest.raises(KeyError):new.get('owner','run')
    finally:new.close()

def test_knowledge_scope_and_capacity(tmp_path):
    (tmp_path/'catalog.json').write_text(json.dumps({'views':[{'workbook_content_url':'SYN-A','view_name':'A'},{'workbook_content_url':'SYN-B','view_name':'B'}]}))
    knowledge=Knowledge(tmp_path)
    assert [v['view_name'] for v in knowledge.load({'SYN-A'})['views']]==['A']
    with pytest.raises(ValueError):Knowledge(tmp_path,10).load({'SYN-A'})

def test_actual_profile_drives_bounded_analysis(settings,identity,monkeypatch):
    service=TableauService(settings,None)
    view={'id':'SYN-VIEW','name':'Synthetic worksheet','definition':{'verified_export':True,'currency':'HKD','as_of':'2026-10-15',
        'data_grain':'worksheet_summary','columns':{'Notional':{'type':'number','unit':'hkd','additive':True}}}}
    monkeypatch.setattr(service,'resolve',lambda *args:view)
    def download(identity,view,request,path):path.write_text('ActualCategory,Notional\na,10\nb,20\na,30\n')
    monkeypatch.setattr(service,'download',download)
    class ModelDouble:
        calls=0
        async def structured(self,instructions,payload,model,usage):
            self.calls+=1;assert payload['actual_profile']['row_count']==3
            assert payload['shared_business_reference']=={'test_reference':'PB means the reviewed business segment'}
            assert 'grants no permissions' in instructions
            assert 'ActualCategory' in payload['actual_profile']['columns']
            with pytest.raises(ValueError):model.model_validate({'action':'analyze','measure':'Invented'})
            return model.model_validate({'action':'analyze','view_id':'SYN-VIEW','dimensions':['ActualCategory'],'measure':'Notional','aggregation':'sum','chart':'bar'})
    gateway=ModelDouble();result=asyncio.run(service.intelligence(identity,ViewRequest(dashboard='SYN',view_id='SYN-VIEW'),'run','Show notional by actual category',gateway,[],{'test_reference':'PB means the reviewed business segment'}))
    assert gateway.calls==1 and result.data['input_rows']==3
    assert {r['ActualCategory']:r['value'] for r in result.data['rows']}=={'a':'40.00000000','b':'20.00000000'}
    assert result.data['executed_analysis']['measure']=='Notional'
