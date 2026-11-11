"""Recheck saved-result access before displaying history or building a document."""
from hk_platform.runtime.registry import require,resource


def authorize_answer(identity,answer,platform,fresh_live=False):
    require(identity,answer.get('required_permissions',[]))
    scope=answer.get('authorization_context')
    if scope and scope!={'country':identity.country,'line_of_business':identity.line_of_business}:
        raise PermissionError('Saved result belongs to a different authorization context.')
    for key in answer.get('selected_dashboards',[]):resource(identity,key)
    for task in answer.get('plan',{}).get('tasks',[]):
        require(identity,platform['registry'].resolve(task['skill_id'],task.get('skill_version','1.0.0')).metadata().permissions)
    dashboards=set()
    for e in answer.get('evidence',[]):
        if e['source_id']=='mock:business':require(identity,['analytics.read'])
        if e['source_id']=='mock:pricing':require(identity,['pricing.read'])
        if e['source_mode']=='MOCK' and e['source_id'].startswith('mock:'):resource(identity,e['source_id'])
        if e['source_id']=='mock:business' and identity.country not in e['authorization_scope']:raise PermissionError('Country entitlement changed.')
        if e['source_mode']=='LIVE':
            require(identity,['tableau.read'])
            for key in e['authorization_scope'][1:]:resource(identity,key);dashboards.add(key)
    if fresh_live and dashboards:
        service=platform['services']['tableau']
        with service.lock:service.cache.clear()
        views=service.discover(identity,sorted(dashboards));ids={v['id'] for v in views}
        if any(e['source_mode']=='LIVE' and e['source_id'] not in ids for e in answer.get('evidence',[]) if e['source_type'].startswith('tableau')):
            raise PermissionError('A saved Tableau source is no longer accessible.')
