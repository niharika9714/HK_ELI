import asyncio
import hashlib
import json
import threading
import time
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlsplit
from typing import Literal
from pydantic import Field
from hk_platform.contracts.models import Strict, SkillOutput, EvidenceRecord
from hk_platform.runtime.registry import resource
from app.integrations.tableau import Tableau
from app.services.analysis import Analysis
from app.models import Plan
from hk_platform.contracts.errors import PublicError
from services.knowledge.service import reference_instructions


async def drain_thread(function,*args):
    """Keep temporary-file lifetime valid if a synchronous operation is cancelled."""
    import asyncio
    task=asyncio.create_task(asyncio.to_thread(function,*args))
    try:return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            value=await task
            if hasattr(value,'close'):value.close()
        except Exception:pass
        raise


class ViewRequest(Strict):
    dashboard: str = Field(max_length=120)
    view_id: str = Field(pattern=r'^[\w-]{1,100}$')
    filters: dict[str,list[str]] = Field(default_factory=dict,max_length=8)
    parameters: dict[str,str] = Field(default_factory=dict,max_length=8)
    highlights: dict[str,list[str]] = Field(default_factory=dict,max_length=1)
    analysis: Plan | None = None
    required_grain: Literal['dashboard_aggregate','worksheet_summary','mark_detail','deal_detail','governed_records'] = 'worksheet_summary'


class TableauService:
    def __init__(self,config,knowledge):
        self.config,self.knowledge=config,knowledge
        self.cache={};self.lock=threading.Lock();self.limiter=threading.BoundedSemaphore(2)

    def discover(self,identity,selected):
        dashboards=[]
        for key in selected:
            resource(identity,key)
            d=next((d for d in self.config['dashboards'] if d['key']==key),None)
            if not d or identity.country not in d['countries'] or identity.line_of_business not in d['lines_of_business']:
                raise PermissionError('Dashboard entitlement denied.')
            dashboards.append(d)
        if not dashboards:return []
        cache_key=hashlib.sha256(json.dumps([identity.model_dump(),selected,dashboards,self.config['tableau']],sort_keys=True).encode()).hexdigest()
        with self.lock:
            hit=self.cache.get(cache_key)
            if hit and hit[0]>time.monotonic():return json.loads(json.dumps(hit[1]))
        with self.limiter:
            result=Tableau(self.config,identity.model_dump()).catalog(dashboards)
        pack=self.knowledge.load({v['workbook_content_url'] for v in result})
        for view in result:
            records=[r for r in pack['views'] if r.get('workbook_content_url')==view['workbook_content_url'] and r.get('view_name')==view['name']]
            if len(records)>1:raise ValueError('Ambiguous knowledge identity.')
            view['definition']=records[0] if records else {}
        with self.lock:
            if len(self.cache)>100:self.cache.clear()
            self.cache[cache_key]=(time.monotonic()+30,result)
        return result

    def resolve(self,identity,request):
        views=self.discover(identity,[request.dashboard])
        view=next((v for v in views if v['id']==request.view_id),None)
        if not view:raise PermissionError('View outside authorized discovered scope.')
        contract=view['definition']
        if request.highlights and str(view.get('sheet_type','')).lower()=='dashboard':
            raise ValueError('Highlight requires a separately published worksheet; dashboard membership is not inferred.')
        for kind,requested in [('filters',request.filters),('parameters',request.parameters),('highlights',request.highlights)]:
            if requested and not contract.get('native_controls_verified',False):raise PublicError('native_control_unsupported')
            for field,values in requested.items():
                allowed=contract.get(kind,{}) .get(field,[])
                values=values if isinstance(values,list) else [values]
                if not values or not set(values).issubset(allowed):raise PublicError('native_control_unsupported')
        return view

    def embed(self,identity,request):
        view=self.resolve(identity,request)
        provenance=EvidenceRecord(id='E'+uuid.uuid4().hex,source_type='tableau_embed',source_mode='LIVE',source_id=view['id'],
            source_version=view['definition'].get('source_version','unknown'),as_of=view['definition'].get('as_of') or 'unknown',
            filters={'filters':request.filters,'parameters':request.parameters,'highlights':request.highlights},
            authorization_scope=[identity.id,request.dashboard],grain=view['definition'].get('grain','published view; export grain unverified'),
            unit='display',metric='original_view',calculation_id='original_view_descriptor',dimensions={'view_name':view['name']})
        return SkillOutput(evidence=[provenance],visualizations=[{'type':'tableau','view_id':view['id'],'dashboard_key':request.dashboard,'url':view['url'],
            'title':view['name'],'filters':request.filters,'parameters':request.parameters,'highlights':request.highlights,
            'hide_tabs':True,'source_mode':'LIVE','scope_note':'Original published view. Browser changes do not refresh the saved narrative.'}])

    def token(self,identity,request):
        self.resolve(identity,request)
        return Tableau(self.config,identity.model_dump()).jwt(['tableau:views:embed'])

    def download(self,identity,view,request,target,image=False):
        if request.parameters:raise PublicError('export_scope_unverified')
        if request.highlights and image:raise PublicError('export_scope_unverified')
        # One session per bounded operation; no token cache and no redirects.
        client=Tableau(self.config,identity.model_dump())
        with self.limiter,client.session() as (transport,root):
            params={'vf_'+k:','.join(v) for k,v in request.filters.items()}
            url=root+'/views/'+quote(view['id'],safe='')+('/image' if image else '/data')
            started=time.monotonic();size=0
            with transport.get(url,params=params,headers={'Accept':'image/png' if image else '*/*'},stream=True,verify=client.verify,timeout=(5,30),allow_redirects=False) as response:
                client.check(response)
                with open(target,'wb') as output:
                    for chunk in response.iter_content(65536):
                        size+=len(chunk)
                        if size>self.config['app']['max_export_bytes'] or time.monotonic()-started>60:raise ValueError('Export capacity/deadline exceeded; no partial result.')
                        output.write(chunk)

    def analyze(self,identity,request,run_id):
        view=self.resolve(identity,request);contract=view['definition']
        if not contract.get('verified_export'):raise PublicError('export_contract_unverified')
        grain=contract.get('data_grain','worksheet_summary')
        if request.required_grain in ('deal_detail','governed_records') and grain not in ('deal_detail','governed_records'):
            detail=contract.get('authorized_detail_view')
            if not detail:raise PublicError('detail_grain_unavailable')
            detail_request=request.model_copy(update={'view_id':detail})
            detail_view=self.resolve(identity,detail_request)
            if detail_view['definition'].get('scope_equivalence_verified') is not True:raise PublicError('detail_grain_unavailable')
            view,contract,request=detail_view,detail_view['definition'],detail_request
            if not contract.get('verified_export') or contract.get('data_grain') not in ('deal_detail','governed_records'):raise PublicError('detail_grain_unavailable')
        if request.analysis is None:raise ValueError('A typed analysis plan based on the export schema is required.')
        if request.analysis.view_id!=view['id'] or request.analysis.action!='analyze':raise ValueError('Analysis source mismatch.')
        if request.analysis.filters:raise ValueError('Local-only filters would diverge from the embed; declare equivalent native filters.')
        if not contract.get('as_of') or not contract.get('currency'):raise PublicError('reporting_metadata_missing')
        with TemporaryDirectory(prefix='hkeli-full-') as directory:
            path=Path(directory)/'export.csv';self.download(identity,view,request,path)
            engine=Analysis(path,self.config,contract)
            try:result=engine.execute(request.analysis)
            finally:engine.close()
        return self.analysis_output(identity,request,run_id,view,contract,result)

    @staticmethod
    def analysis_output(identity,request,run_id,view,contract,result):
        evidence=[]
        for i,row in enumerate(result['rows']):
            if row.get('value') is not None:
                evidence.append(EvidenceRecord(id='E'+uuid.uuid4().hex,source_type='tableau_csv',source_mode='LIVE',source_id=view['id'],
                    source_version=contract.get('source_version','unknown'),as_of=contract['as_of'],filters=request.filters,
                    authorization_scope=[identity.id,request.dashboard],grain=contract.get('grain','unknown'),value=row['value'],unit=result['unit'],
                    calculation_id=f'{run_id}:{i}',metric=request.analysis.measure or '',statistic=request.analysis.aggregation,
                    dimensions={k:str(v) for k,v in row.items() if k!='value'},
                    warnings=['Published export completeness asserted by reviewed contract, not underlying database proof.']))
        return SkillOutput(data=result,evidence=evidence,warnings=['Chart/narrative represent initial filters; browser interactions do not update saved findings.'])

    async def intelligence(self,identity,request,run_id,question,gateway,usage,shared_knowledge=None):
        """One bounded model decision over the actual full-export profile; execute the same snapshot."""
        import asyncio
        from pydantic import create_model
        view=await asyncio.to_thread(self.resolve,identity,request);contract=view['definition']
        if not contract.get('verified_export'):raise PublicError('export_contract_unverified')
        if not contract.get('as_of') or not contract.get('currency'):raise PublicError('reporting_metadata_missing')
        if request.required_grain in ('deal_detail','governed_records') and contract.get('data_grain') not in ('deal_detail','governed_records'):
            raise PublicError('detail_grain_unavailable')
        if gateway is None:raise ValueError('Stork is required for an adaptive analytical decision.')
        with TemporaryDirectory(prefix='hkeli-observed-') as directory:
            path=Path(directory)/'export.csv'
            await drain_thread(self.download,identity,view,request,path)
            engine=await drain_thread(Analysis,path,self.config,contract)
            try:
                profile=await drain_thread(engine.profile)
                columns=tuple(profile['columns']);date_columns=tuple(profile['date_columns'])
                Column=Literal[columns]
                DateColumn=Literal[date_columns] if date_columns else Literal['NO_APPROVED_DATE_COLUMN']
                ObservedPlan=create_model('ObservedAnalysisPlan',__base__=Plan,
                    measure=(Column|None,None),dimensions=(list[Column],Field(default_factory=list,max_length=3)),date_column=(DateColumn|None,None))
                decision=await gateway.structured('Return one typed analysis decision using ONLY observed columns and approved metric semantics. '
                    'action=analyze; use the supplied view_id. No invented code, SQL, calculations, dates or units. '
                    'Native filters already apply: filters MUST be empty to preserve the displayed scope. '
                    'Sum only approved additive fields. Rates/unknown grain cannot be counted as deals or summed. '
                    'Choose clarify with explanation if the requested information cannot be obtained. '
                    'The profile covers the full export; raw rows are not supplied. One bounded decision, no repeated model loop.'+reference_instructions(),
                    {'original_question':question,'view_id':view['id'],'actual_profile':profile,'native_filters':request.filters,
                     'shared_business_reference':shared_knowledge or {}},ObservedPlan,usage)
                if decision.action!='analyze' or decision.view_id!=view['id'] or decision.filters:raise PublicError('analysis_contract_rejected')
                result=await drain_thread(engine.execute,decision)
                result['executed_analysis']=decision.model_dump()
                return self.analysis_output(identity,request.model_copy(update={'analysis':decision}),run_id,view,contract,result)
            finally:engine.close()

    def chart_image(self,identity,request):
        view=self.resolve(identity,request)
        with TemporaryDirectory() as directory:
            path=Path(directory)/'chart.png';self.download(identity,view,request,path,image=True)
            return path.read_bytes()
