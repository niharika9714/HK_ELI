import asyncio
import json
import time
from pathlib import Path
from hk_platform.contracts.models import ExecutionPlan
from hk_platform.runtime.registry import SkillContext
from hk_platform.ai.gateway import narrate
from .documents import document_followup,combine_results,finalize_documents,history_reference


async def run(platform,identity,request,key,cancelled,progress,conversation_context=None):
    async with asyncio.timeout(platform['executor'].timeout):
        return await _run(platform,identity,request,key,cancelled,progress,conversation_context)


async def _run(platform,identity,request,key,cancelled,progress,conversation_context=None):
    started=time.monotonic();services=dict(platform['services']);services.update(question=request.question,usage=[],images=[])
    services['shared_knowledge']=await asyncio.to_thread(services['knowledge'].shared,request.question) if 'knowledge.read' in identity.permissions else {}
    history=(conversation_context or {}).get('history',[])
    services['conversation_history']=history_reference(history)
    if not request.plan and history:
        reused=await document_followup(request.question,history,services.get('gateway'),services['usage'],request.context_turn_ids)
        if reused is not None:
            answer=combine_results(reused)
            answer.update(request_id=key,conversation_id=request.conversation_id,
                requirement_coverage={'status':'saved_result_document','source_turn_ids':[t['id'] for t in reused]},task_statuses={})
            await finalize_documents(platform,identity,request,answer,reused_turns=reused,usage=services['usage'],shared=services['shared_knowledge'])
            answer['metrics']={'latency_seconds':time.monotonic()-started,'llm_call_count':len(services['usage']),'usage':services['usage']}
            return answer
    plan=request.plan or await platform['planner'].plan(request.question,identity,request.dashboards,services,request.formats)
    services['request_coverage']=[c.model_dump() for c in plan.coverage]
    # Explicit plans are a trusted-shape API, never trusted authority.
    for task in plan.tasks:
        source_task=task.parameters.get('source_task')
        if source_task and source_task not in task.dependencies:raise ValueError('Input task must be declared as dependency.')
    context=SkillContext(identity,key,services,cancelled)
    outputs,statuses,warnings=await platform['executor'].execute(plan,context,progress)
    evidence=[e for output in outputs.values() for e in output.evidence]
    ids=[e.id for e in evidence]
    # An evidence record can be repeated across output paths; identical IDs must have identical contents.
    unique={}
    for e in evidence:
        if e.id in unique and unique[e.id]!=e:raise ValueError('Conflicting evidence identity.')
        unique[e.id]=e
    evidence=list(unique.values())
    if any(set(e.input_evidence_ids)-set(unique) for e in evidence):raise ValueError('Missing derived evidence inputs.')
    narrative=await narrate(services.get('gateway'),request.question,evidence,services['usage'],services['shared_knowledge'],services['request_coverage'])
    visuals=[v for output in outputs.values() for v in output.visualizations]
    from .tableau_documents import unique_views
    visuals=unique_views(visuals)+[v for v in visuals if v.get('type')!='tableau']
    warnings.extend(w for output in outputs.values() for w in output.warnings)
    for item in plan.coverage:
        if item.status=='unresolved':warnings.append('Unresolved '+item.requirement_id+': '+item.reason)
    for assessment in plan.source_assessments:
        if assessment.match!='complete_match':warnings.extend([assessment.reason,*assessment.remaining_gaps])
    if services.get('gateway') is None:warnings.append('Offline fixture mode: deterministic evidence statements, not live Stork narration.')
    if any(s in ('failed','partial','skipped') for s in statuses.values()):warnings.append('Some requested tasks are unavailable; independent valid results retained.')
    complete=all(s=='complete' for s in statuses.values()) and all(a.match=='complete_match' for a in plan.source_assessments) and all(c.status=='satisfied' for c in plan.coverage)
    answer={'request_id':key,'status':'complete' if complete else 'partial',
            'message':'Authorized results; see evidence and source-mode disclosures.' if complete else 'Some requirements or tasks remain unresolved; see coverage and limitations.',
            'visualizations':visuals,'analysis':{'results':{k:v.data for k,v in outputs.items() if v.data},'limitations':warnings},
            'narrative':narrative.model_dump(),'evidence':[e.model_dump() for e in evidence],
            'evidence_ids':[e.id for e in evidence],'source_modes':sorted({e.source_mode for e in evidence}),
            'warnings':list(dict.fromkeys(warnings)),'task_statuses':statuses,'plan':plan.model_dump(),
            'source_assessments':[a.model_dump() for a in plan.source_assessments],
            'requirement_coverage':{'status':'checked' if plan.requirements else 'not_assessed','requirements':[r.model_dump() for r in plan.requirements],'coverage':services['request_coverage']},
            'selected_dashboards':request.dashboards,'artifacts':[],
            'conversation_id':request.conversation_id,
            'authorization_context':{'country':identity.country,'line_of_business':identity.line_of_business},
            'required_permissions':sorted({p for t in plan.tasks for p in platform['registry'].resolve(t.skill_id,t.skill_version).metadata().permissions}),
            'knowledge_references':[{k:v for k,v in record.items() if k!='content'} for record in
                services['shared_knowledge'].get('overview',[])+services['shared_knowledge'].get('entries',[])],
            'metrics':{'latency_seconds':time.monotonic()-started,'llm_call_count':len(services['usage']),'usage':services['usage']}}
    if 'Q2'==request.question.split(':',1)[0].strip().upper():
        from domains.hk_eli.executive import build
        answer['report_sections']=build(evidence)
    requests=[out.data['document_request'] for out in outputs.values() if 'document_request' in out.data]
    planned_formats=list(dict.fromkeys(plan.output.formats+[fmt for item in requests for fmt in item['formats']]))
    try:
        await finalize_documents(platform,identity,request,answer,services['images'],bool(requests or plan.output.formats),planned_formats,usage=services['usage'],shared=services['shared_knowledge'],image_exports=services.get('tableau_image_exports'))
    except PermissionError:raise
    except Exception as error:
        answer['status']='partial';answer['warnings'].append('Artifact generation unavailable: '+type(error).__name__+'. Analysis retained.')
    # Compatibility with the old single-view response shape.
    if visuals:
        v=visuals[0];answer.update(visual=v,view_id=v.get('view_id'),dashboard_key=v.get('dashboard_key'))
    answer['citations']=[{'id':e.id,'title':e.calculation_id,'source_mode':e.source_mode} for e in evidence]
    answer['metrics']['latency_seconds']=time.monotonic()-started
    return answer
