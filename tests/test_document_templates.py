"""Offline acceptance for template routing, grounding, disclosure gates and rendered files."""
import asyncio
import copy
from datetime import datetime
import pytest
from services.artifacts.templates import TemplateRegistry,DocumentPlan,SectionPlan,prepare_documents
from conftest import login
from test_conversations_documents import post


def test_missing_required_disclosure_preserves_answer(client,app):
    app.extensions['platform']['services']['artifacts'].templates.disclosures['D3']={'approved':False,'text':''}
    headers=login(client);queued,source=post(client,headers,'Q1')
    _,answer=post(client,headers,'Generate an executive deck',queued['conversation_id'])
    assert answer['status']=='partial' and answer['artifacts']==[]
    assert answer['evidence']==source['evidence']
    assert 'Required disclosure not configured: D3' in answer['message']


def test_registry_blocks_external_paths_and_unknown_ids():
    registry=TemplateRegistry()
    with pytest.raises(ValueError,match='outside'):registry.path('../../secret')
    with pytest.raises(ValueError,match='Unknown'):registry.get('invented','pptx')
    with pytest.raises(ValueError,match='disabled'):registry.get('client-briefing','pptx')
    assert registry.disclosures['D3']['approved'] is False


def test_plan_checks_required_sections_evidence_and_images(app):
    registry=app.extensions['platform']['services']['artifacts'].templates
    manifest=registry.get('executive-overview','pptx')
    bad=DocumentPlan(template_id='executive-overview',sections=[SectionPlan(section_id='summary',evidence_ids=['invented'])])
    with pytest.raises(ValueError,match='evidence'):registry.validate_plan(bad,manifest,{},0)
    bad.sections[0].evidence_ids=[]
    with pytest.raises(ValueError,match='Required'):registry.validate_plan(bad,manifest,{},0)
    bad.sections.append(SectionPlan(section_id='charts',image_indices=[0]))
    with pytest.raises(ValueError,match='chart'):registry.validate_plan(bad,manifest,{},0)


def test_all_formats_use_registry_and_saved_evidence(client,app):
    from pptx import Presentation
    from docx import Document
    from openpyxl import load_workbook
    headers=login(client);queued,source=post(client,headers,'Q1')
    _,answer=post(client,headers,'Generate PowerPoint, Word, PDF and Excel from that',queued['conversation_id'])
    assert answer['status']=='complete',answer.get('warnings')
    assert len(answer['artifacts'])==4
    service=app.extensions['platform']['services']['artifacts']
    for artifact in answer['artifacts']:
        path,_,manifest=service.get('synthetic-hk-rm',artifact['id'])
        assert manifest['template']['template_version']=='1'
        assert manifest['evidence']==source['evidence']
        assert manifest['template']['disclosures']
        if artifact['format']=='pptx':
            prs=Presentation(path);text='\n'.join(sh.text for slide in prs.slides for sh in slide.shapes if sh.has_text_frame)
            assert 'Evidence appendix' in text and 'DRAFT' in text
            assert '1,250m' not in text and '24.5%' not in text
            assert len(prs.slides)<=60
        elif artifact['format']=='docx':
            text='\n'.join(p.text for p in Document(path).paragraphs)
            assert 'Evidence register' in text and '{{' not in text
        elif artifact['format']=='xlsx':
            wb=load_workbook(path)
            assert {'README','Summary','Evidence','Limitations','Data_Evidence'}<=set(wb.sheetnames)
            assert isinstance(wb['Data_Evidence']['C2'].value,(int,float))
            assert isinstance(wb['Data_Evidence']['E2'].value,datetime)
            assert all(ws.sheet_state=='visible' for ws in wb)
            assert wb['Data_Evidence'].tables and wb['Data_Evidence'].freeze_panes=='A2'
        else:assert path.read_bytes().startswith(b'%PDF')


def test_external_request_cannot_be_exported_as_internal(client):
    headers=login(client);queued,_=post(client,headers,'Q1')
    _,answer=post(client,headers,'Make a client briefing as PowerPoint',queued['conversation_id'])
    assert not answer['artifacts'] and 'Client briefing disabled' in answer['message']
    _,again=post(client,headers,'PPTX',queued['conversation_id'])
    assert not again['artifacts'] and 'Client briefing disabled' in again['message']


def test_live_document_outline_uses_bounded_facts_and_shared_definitions(app):
    registry=app.extensions['platform']['services']['artifacts'].templates
    fact={'id':'F1','value':'100','metric':'sales','unit':'HKD','source_mode':'MOCK','as_of':'2026-11-09'}
    class Gateway:
        async def structured(self,instructions,payload,model,usage):
            assert payload['shared_business_reference']=={'entries':[{'term':'RFQ'}]}
            assert payload['facts'][0]['value']=='100' and 'rows' not in payload
            manifest=registry.get('executive-overview','pptx')
            return DocumentPlan(template_id=manifest['id'],sections=[SectionPlan(section_id=s['id'],evidence_ids=['F1']) for s in manifest['sections'] if s['required']])
    plans=asyncio.run(prepare_documents(registry,'Executive deck',{'evidence':[fact]},['pptx'],gateway=Gateway(),usage=[],shared={'entries':[{'term':'RFQ'}]}))
    assert plans['pptx']['template_id']=='executive-overview'


def test_formula_injection_and_missing_numeric_cells(client,app):
    from openpyxl import load_workbook
    headers=login(client);_,source=post(client,headers,'Q1')
    answer=copy.deepcopy(source);answer['narrative']={}
    answer['evidence']=answer['evidence'][:2]
    answer['evidence'][0].update(metric='=HYPERLINK("malicious")',value=None)
    service=app.extensions['platform']['services']['artifacts']
    answer['document_plans']=asyncio.run(prepare_documents(service.templates,'Excel',answer,['xlsx']))
    artifact=service.generate('synthetic-hk-rm',answer,['xlsx'])[0]
    path,_,_=service.get('synthetic-hk-rm',artifact['id']);wb=load_workbook(path)
    assert wb['Data_Evidence']['B2'].data_type=='s'
    assert wb['Data_Evidence']['C2'].value is None
    assert wb['Data_Evidence']['H2'].value.startswith('Missing')


def test_multi_format_failure_rolls_back_all_files(client,app,monkeypatch):
    from hk_platform.runtime.database import connect
    headers=login(client);queued,source=post(client,headers,'Q1')
    service=app.extensions['platform']['services']['artifacts'];original=service._write
    def write(fmt,*args):
        if fmt=='xlsx':raise ValueError('Synthetic layout failure')
        return original(fmt,*args)
    monkeypatch.setattr(service,'_write',write)
    _,answer=post(client,headers,'Generate Word and Excel',queued['conversation_id'])
    assert answer['status']=='partial' and not answer['artifacts']
    assert answer['evidence']==source['evidence']
    assert list(service.root.iterdir())==[]
    with connect(service.db_path) as db:assert db.execute('SELECT count(*) FROM artifacts').fetchone()[0]==0


def test_explicit_template_and_new_format_do_not_inherit_old_choice(client):
    headers=login(client);queued,_=post(client,headers,'Q1')
    _,word=post(client,headers,'Make a Word report',queued['conversation_id'],template_id='business-report')
    assert word['artifacts'][0]['template_id']=='business-report'
    _,deck=post(client,headers,'Generate an executive deck from that',queued['conversation_id'])
    assert deck['artifacts'][0]['template_id']=='executive-overview'


def test_docx_and_pdf_share_one_live_outline(app):
    registry=app.extensions['platform']['services']['artifacts'].templates;calls=[]
    class Gateway:
        async def structured(self,instructions,payload,model,usage):
            calls.append(payload)
            return DocumentPlan(template_id='business-report',sections=[SectionPlan(section_id=s['id'],evidence_ids=['F1']) for s in registry.get('business-report','docx')['sections'] if s['required']])
    facts=[{'id':'F1','value':'100','metric':'sales','unit':'HKD','source_mode':'MOCK','as_of':'2026-11-09'}]
    plans=asyncio.run(prepare_documents(registry,'Word and PDF',{'evidence':facts},['docx','pdf'],gateway=Gateway(),usage=[]))
    assert len(calls)==1 and plans['docx']['plan']==plans['pdf']['plan']
