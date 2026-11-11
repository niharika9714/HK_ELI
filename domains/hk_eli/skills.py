import asyncio
import statistics
import uuid
from decimal import Decimal
from typing import Literal
from pydantic import Field
from hk_platform.contracts.models import Strict, SkillMetadata, SkillOutput, QuoteInput, EvidenceRecord, Narrative
from hk_platform.runtime.registry import BaseSkill
from services.tableau.service import ViewRequest
from hk_platform.ai.gateway import narrate
from .skill_guidance import guidance


class BusinessInput(Strict):
    days: int = Field(default=5,ge=1,le=366)
    currency: Literal['HKD','USD'] = 'HKD'


class DiscoveryInput(Strict):
    dashboards: list[str] = Field(max_length=10)


class KnowledgeInput(Strict):
    query: str = Field(default='',max_length=2000)
    record_id: str | None = None
    dashboards: list[str] = []


class InsightInput(Strict):
    question: str = Field(max_length=2000)


class AnalyticsInput(Strict):
    source_task: str
    column: str = Field(max_length=120)
    operation: Literal['sum','compare','trend','rank','anomaly','forecast'] = 'sum'
    limit: int = Field(default=10,ge=1,le=200)
    date_column: str | None = None


class ArtifactInput(Strict):
    formats: list[Literal['docx','pptx','pdf','xlsx']] = Field(default_factory=list,max_length=4)


class Skill(BaseSkill):
    def __init__(self,name,domain,model,function,permissions=None,modes=None,service='analytics'):
        self.input_model=model;self.function=function
        self.meta=SkillMetadata(id=name,domain=domain,**guidance(name),permissions=permissions or ['analytics.read'],
            source_modes=modes or ['MOCK'],service=service,input_schema=model.model_json_schema(),output_schema=SkillOutput.model_json_schema())

    def metadata(self):return self.meta

    async def execute(self,inputs,context):return await self.function(inputs,context)


def register_skills(registry):
    operations={'eli.sales.performance':'sales','eli.rfq.conversion':'rfq','eli.risk.concentration':'concentration',
        'eli.maturity.analyze':'maturity','eli.rollover.opportunity':'rollover','eli.client.engagement':'engagement',
        'eli.regional.performance':'regional','eli.digibank.journey':'digital','eli.product.yield':'yield',
        'eli.branch.concentration':'branch','eli.client.intelligence':'client','eli.sales.trend':'trend'}
    for name,operation in operations.items():
        async def business(i,c,op=operation):
            return await asyncio.to_thread(c.services['business'].run,op,c.identity,i.days,i.currency)
        registry.register(Skill(name,'hk_eli',BusinessInput,business))
    for name,target in [('eli.pricing.solve_coupon','coupon'),('eli.pricing.solve_strike','strike')]:
        async def pricing(i,c,target=target):
            i=i.model_copy(update={'solve_target':target})
            return c.services['pricing'].solve(i,c.identity)
        registry.register(Skill(name,'hk_eli',QuoteInput,pricing,['pricing.read'],service='pricing'))

    async def discover(i,c):
        views=await asyncio.to_thread(c.services['tableau'].discover,c.identity,i.dashboards)
        return SkillOutput(data={'views':views})
    registry.register(Skill('tableau.view.discover','tableau',DiscoveryInput,discover,['tableau.read'],['LIVE'],'tableau'))
    async def embed(i,c):return await asyncio.to_thread(c.services['tableau'].embed,c.identity,i)
    async def analyze(i,c):
        if i.analysis is None:
            return await c.services['tableau'].intelligence(c.identity,i,c.run_id,c.services['question'],c.services.get('gateway'),c.services['usage'],c.services.get('shared_knowledge',{}))
        return await asyncio.to_thread(c.services['tableau'].analyze,c.identity,i,c.run_id)
    async def resolve(i,c):
        view=await asyncio.to_thread(c.services['tableau'].resolve,c.identity,i)
        return SkillOutput(data={'view':view})
    for name,fn in [('tableau.view.resolve',resolve),('tableau.view.embed',embed),('tableau.view.filter',embed),
                    ('tableau.data.analyze',analyze)]:
        registry.register(Skill(name,'tableau',ViewRequest,fn,['tableau.read'],['LIVE'],'tableau'))
    class ComparisonInput(Strict):
        views:list[ViewRequest]=Field(min_length=2,max_length=2)
    async def compare_views(i,c):
        results=await asyncio.gather(*(embed(v,c) for v in i.views))
        return SkillOutput(evidence=[e for out in results for e in out.evidence],visualizations=[v for out in results for v in out.visualizations],
            warnings=['Independent original views. No cross-source totals or inferred joins.'])
    registry.register(Skill('tableau.view.compare','tableau',ComparisonInput,compare_views,['tableau.read'],['LIVE'],'tableau'))
    async def profile(i,c):
        # No raw export crosses task state. Profile operation has its own bounded lifetime.
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from app.services.analysis import Analysis
        def work():
            service=c.services['tableau'];view=service.resolve(c.identity,i)
            with TemporaryDirectory() as directory:
                path=Path(directory)/'data.csv';service.download(c.identity,view,i,path)
                engine=Analysis(path,service.config,view['definition'])
                try:return SkillOutput(data=engine.profile())
                finally:engine.close()
        return await asyncio.to_thread(work)
    for name in ('tableau.data.retrieve','tableau.data.profile'):
        registry.register(Skill(name,'tableau',ViewRequest,profile,['tableau.read'],['LIVE'],'tableau'))
    async def chart_export(i,c):
        image=await asyncio.to_thread(c.services['tableau'].chart_image,c.identity,i)
        provenance=await embed(i,c)
        # Keep binary server-side for report generation, never in LLM prompts or SQLite task payloads.
        c.services.setdefault('images',[]).append(image)
        from app.services.tableau_documents import view_key
        c.services.setdefault('tableau_image_exports',{})[view_key(provenance.visualizations[0])]=image
        return SkillOutput(data={'image_index':len(c.services['images'])-1,'format':'png','source_mode':'LIVE','view_id':i.view_id},evidence=provenance.evidence,visualizations=provenance.visualizations)
    registry.register(Skill('tableau.chart.export','tableau',ViewRequest,chart_export,['tableau.read','artifact.write'],['LIVE'],'tableau'))

    async def knowledge(i,c):
        shared=c.services.get('shared_knowledge',{})
        views=await asyncio.to_thread(c.services['tableau'].discover,c.identity,i.dashboards)
        pack=c.services['knowledge'].load({v['workbook_content_url'] for v in views})
        if i.record_id:
            records=[r for r in pack['views'] if r.get('record_id')==i.record_id]
            return SkillOutput(data={'definitions':records,'shared_business_reference':shared})
        return SkillOutput(data={'documents':c.services['knowledge'].search(pack,i.query),'shared_business_reference':shared})
    for name in ('knowledge.search','knowledge.retrieve','knowledge.definition.resolve'):
        registry.register(Skill(name,'knowledge',KnowledgeInput,knowledge,['knowledge.read'],['LIVE','MOCK'],'knowledge'))

    async def insight(i,c):
        evidence=[e for out in c.outputs.values() for e in out.evidence]
        result=await narrate(c.services.get('gateway'),i.question,evidence,c.services['usage'],c.services.get('shared_knowledge',{}),c.services.get('request_coverage',[]))
        return SkillOutput(data={'narrative':result.model_dump()})
    registry.register(Skill('tableau.insight.generate','tableau',InsightInput,insight,['analytics.read'],['LIVE','MOCK'],'stork'))

    async def analytics(i,c):
        source=c.outputs.get(i.source_task)
        if source is None:raise ValueError('Missing declared input task.')
        rows=source.data.get('rows',[])
        if not rows or any(r.get(i.column) is None for r in rows):raise ValueError('Missing analysis values.')
        vals=[Decimal(str(r[i.column])) for r in rows]
        if any(not v.is_finite() for v in vals):raise ValueError('Nonfinite analysis value.')
        units={e.unit for e in source.evidence if e.value is not None}
        modes={e.source_mode for e in source.evidence}
        if len(modes)!=1:raise ValueError('Mixed live/mock calculation is forbidden.')
        inputs=[e for e in source.evidence if e.metric==i.column]
        if not inputs:raise ValueError('Metric-specific evidence is required.')
        if len({e.unit for e in inputs})!=1 or len({e.as_of for e in inputs})!=1:raise ValueError('Unit or reporting-date mismatch.')
        # Generic sums require an explicit additive output declaration; no inferred money/rate semantics.
        if i.operation=='sum' and i.column not in source.data.get('additive_columns',[]):raise ValueError('Output additivity unapproved.')
        if i.operation=='sum': result=[{'value':str(sum(vals))}]
        elif i.operation=='rank':result=sorted(rows,key=lambda r:Decimal(str(r[i.column])),reverse=True)[:i.limit]
        elif i.operation=='compare':result=[{'minimum':str(min(vals)),'maximum':str(max(vals)),'difference':str(max(vals)-min(vals))}]
        elif i.operation in ('trend','forecast'):
            from datetime import date
            if not i.date_column or any(i.date_column not in row for row in rows):raise ValueError('Time series requires an explicit ISO-date column.')
            dates=[date.fromisoformat(str(row[i.date_column])) for row in rows]
            if len(set(dates))!=len(dates) or dates!=sorted(dates):raise ValueError('Unique ascending time axis required.')
            result=rows if i.operation=='trend' else [{'estimate':str(vals[-1]),'method':'Naive last-observation baseline; estimate only; no market prediction.','last_observation':dates[-1].isoformat()}]
        else:
            mean=sum(vals)/len(vals);sd=Decimal(str(statistics.pstdev(vals)))
            result=[r for r,v in zip(rows,vals) if sd and abs(v-mean)>3*sd]
        e=EvidenceRecord(id='E'+uuid.uuid4().hex,source_type='derived',source_mode=next(iter(modes)),source_id=i.source_task,
            source_version='1.0',as_of=source.evidence[0].as_of,authorization_scope=[c.identity.id],grain='derived output',
            calculation_id=i.operation,input_evidence_ids=[e.id for e in inputs],metric=i.column,unit=inputs[0].unit,
            warnings=['Forecasts/anomalies are descriptive baseline methods, not investment recommendations.'])
        facts=[]
        if i.operation in ('sum','compare','forecast'):
            for key,value in result[0].items():
                try:n=Decimal(str(value))
                except Exception:continue
                if not n.is_finite():continue
                facts.append(e.model_copy(update={'id':'E'+uuid.uuid4().hex,'value':str(value),
                    'statistic':'estimate' if i.operation=='forecast' else key,'calculation_id':i.operation+':'+key}))
        return SkillOutput(data={'rows':result,'method':i.operation,'source_mode':next(iter(modes))},evidence=facts or [e],warnings=e.warnings)
    for name in ('analytics.aggregate','analytics.compare','analytics.trend','analytics.rank','analytics.anomaly','analytics.forecast'):
        operation=name.rsplit('.',1)[1]
        async def bounded_analytics(i,c,operation=operation):
            required='sum' if operation=='aggregate' else operation
            if i.operation!=required:raise ValueError('Operation must match the declared analytics skill.')
            return await analytics(i,c)
        registry.register(Skill(name,'analytics',AnalyticsInput,bounded_analytics,modes=['LIVE','MOCK']))

    async def artifact(i,c):
        # Rendering happens exactly once after all evidence/narration is composed.
        return SkillOutput(data={'document_request':{'formats':list(dict.fromkeys(i.formats))}})
    registry.register(Skill('artifact.generate','artifacts',ArtifactInput,artifact,['artifact.write'],['LIVE','MOCK'],'artifacts'))
    # Validation/publication operate on an existing protected artifact; publishing is draft only.
    class ExistingArtifact(Strict):artifact_id:str
    async def validate_artifact(i,c):
        path,mime,manifest=c.services['artifacts'].get(c.identity.id,i.artifact_id)
        return SkillOutput(data={'id':i.artifact_id,'status':'draft','validated':True})
    for name in ('artifact.validate','artifact.publish_draft'):
        registry.register(Skill(name,'artifacts',ExistingArtifact,validate_artifact,['artifact.write'],['LIVE','MOCK'],'artifacts'))
