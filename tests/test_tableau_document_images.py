import asyncio
import io
import pytest
from PIL import Image
from app.services.tableau_documents import document_images,unique_views
from app.services.documents import combine_results


def png():
    data=io.BytesIO();Image.new('RGB',(30,20),'white').save(data,'PNG');return data.getvalue()


def view(filters=None):
    return {'type':'tableau','view_id':'VIEW-1','dashboard_key':'DASH-1',
            'filters':filters or {},'parameters':{},'highlights':{},'url':'https://ignored.example/view'}


def test_filtered_chat_descriptors_export_identical_scopes_and_defaults():
    calls=[]
    class Service:
        def chart_image(self,identity,request):calls.append(request);return png()
    descriptors=[view({'Result':['KO'],'Segment':['PB']}),view({'Result':['KO'],'Segment':['PB']}),view()]
    answer={'visualizations':descriptors,'warnings':[]}
    images=asyncio.run(document_images(Service(),object(),answer,[]))
    assert len(images)==2 and len(calls)==2
    assert calls[0].filters=={'Result':['KO'],'Segment':['PB']}
    assert calls[1].filters=={}
    assert answer['document_chart_snapshots'][0]['filters']==calls[0].filters
    assert answer['visualizations']==descriptors  # Chat keeps interactive descriptors.


def test_saved_context_keeps_distinct_scopes_for_fresh_pngs():
    base={'request_id':'old','status':'complete','evidence':[],'narrative':{},'visualizations':[view({'Result':['KO']})]}
    second=dict(base,visualizations=[view({'Result':['EX']})])
    answer=combine_results([{'id':'one','answer':base},{'id':'two','answer':second}])
    assert len(answer['tableau_views'])==2 and answer['visualizations']==[]
    class Service:
        def chart_image(self,*args):return png()
    assert len(asyncio.run(document_images(Service(),None,answer,[],True)))==2
    assert any('not certified as the same snapshot' in w for w in answer['warnings'])


def test_unsupported_controls_are_not_dropped():
    descriptor=view();descriptor['parameters']={'Period':'Next week'};descriptor['highlights']={'Result':['KO']}
    class Service:
        def chart_image(self,identity,request):
            assert request.parameters==descriptor['parameters'] and request.highlights==descriptor['highlights']
            raise ValueError('export_scope_unverified')
    with pytest.raises(ValueError,match='export_scope'):
        asyncio.run(document_images(Service(),None,{'visualizations':[descriptor]},[]))


def test_non_png_response_is_rejected():
    class Service:
        def chart_image(self,*args):return b'<html>login</html>'
    with pytest.raises(Exception):asyncio.run(document_images(Service(),None,{'visualizations':[view()]},[]))


def test_current_run_png_reuse_requires_exact_scope():
    from app.services.tableau_documents import view_key
    calls=[]
    class Service:
        def chart_image(self,identity,request):calls.append(request.filters);return png()
    exports={view_key(view({'Result':['KO']})):png()}
    answer={'visualizations':[view({'Result':['KO']}),view({'Result':['EX']})]}
    images=asyncio.run(document_images(Service(),None,answer,[],exports=exports))
    assert len(images)==2 and calls==[{'Result':['EX']}]


def test_document_outline_cannot_omit_pngs(app):
    from services.artifacts.templates import prepare_documents,DocumentPlan,SectionPlan
    registry=app.extensions['platform']['services']['artifacts'].templates
    class Gateway:
        async def structured(self,*args):
            return DocumentPlan(template_id='executive-overview',sections=[SectionPlan(section_id=s['id']) for s in registry.get('executive-overview','pptx')['sections'] if s['required']])
    answer={'evidence':[{'id':'F1','metric':'sales','source_mode':'MOCK','value':'100','unit':'HKD','as_of':'2026-11-09'}]}
    with pytest.raises(ValueError,match='omitted requested chart'):
        asyncio.run(prepare_documents(registry,'Executive deck',answer,['pptx'],1,Gateway(),[]))
