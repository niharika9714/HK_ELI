"""One validated Tableau scope for interactive chat and static document snapshots."""
import asyncio
import json
from datetime import datetime,timezone
from services.tableau.service import ViewRequest


def view_key(view):
    return json.dumps({k:view.get(k,{}) for k in ('dashboard_key','view_id','filters','parameters','highlights')},sort_keys=True)


def unique_views(views):
    return list({view_key(v):v for v in views if v.get('type')=='tableau'}.values())


async def document_images(service,identity,answer,images,reused=False,exports=None):
    """Re-resolve saved descriptors; never trust their URL or silently relax controls."""
    views=unique_views(answer.get('tableau_views',[])+answer.get('visualizations',[]))
    result=list(images or []);snapshots=[]
    for view in views:
        request=ViewRequest(dashboard=view['dashboard_key'],view_id=view['view_id'],
            filters=view.get('filters',{}),parameters=view.get('parameters',{}),highlights=view.get('highlights',{}))
        # Reuse only an in-run export bound to this exact validated scope.
        raw=(exports or {}).get(view_key(view)) if not reused else None
        if raw is None:raw=await asyncio.to_thread(service.chart_image,identity,request)
        from PIL import Image
        import io
        with Image.open(io.BytesIO(raw)) as image:
            if image.format!='PNG':raise ValueError('Tableau document export is not PNG.')
            image.verify()
        snapshots.append({'image_index':len(result),'view_id':request.view_id,'dashboard':request.dashboard,
            'filters':request.filters,'parameters':request.parameters,'highlights':request.highlights,
            'captured_at':datetime.now(timezone.utc).isoformat(),'source_mode':'LIVE'})
        result.append(raw)
    answer['tableau_views']=views
    answer['document_chart_snapshots']=snapshots
    if reused and snapshots:
        answer['warnings'].append('Tableau PNGs were freshly exported with the original query filters. Saved numerical evidence retains its original reporting dates; images and saved figures are not certified as the same snapshot.')
    return result
