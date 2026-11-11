import hmac
import secrets
import asyncio
from flask import Blueprint,current_app,jsonify,render_template,request,session,send_file
from hk_platform.contracts.models import Request,ExecutionPlan,TaskSpec,UserIntent,QuoteInput,Strict
from hk_platform.runtime.registry import require,resource
from app.services.identity import current_user,local_guard
from app.services.orchestrator import run
from services.tableau.service import ViewRequest
from app.services.authorization import authorize_answer
from app.services.documents import finalize_documents

bp=Blueprint('api',__name__)
def config():return current_app.config['HKELI']
def platform():return current_app.extensions['platform']
def user():return current_user(config())


@bp.before_request
def csrf():
    if request.path in ('/api/v1/health','/api/v1/ready'):return
    if config()['identity'].get('local_test_enabled'):local_guard()
    if request.method in ('POST','DELETE') and not hmac.compare_digest(request.headers.get('X-CSRF-Token',''),session.get('csrf','!')):
        raise PermissionError('Invalid CSRF token; reload session.')


@bp.get('/')
def index():return render_template('index.html')


@bp.get('/api/session')
def bootstrap():
    session.setdefault('csrf',secrets.token_urlsafe(32))
    profiles=[{k:u[k] for k in ('id','country','line_of_business')} for u in config()['users']] if config()['identity'].get('local_test_enabled') else []
    return jsonify(csrf=session['csrf'],mode=config()['app']['mode'],profiles=profiles,local_test=bool(profiles))


@bp.post('/api/login')
def login():
    if not config()['identity'].get('local_test_enabled'):raise PermissionError('Use corporate SSO.')
    local_guard();key=(request.get_json() or {}).get('user_id')
    if key not in {u['id'] for u in config()['users']}:raise PermissionError('Unknown configured profile.')
    session.clear();session.update(user=key,csrf=secrets.token_urlsafe(32));return jsonify(csrf=session['csrf'])


@bp.post('/api/logout')
def logout():session.clear();return jsonify(status='signed_out')


@bp.get('/api/dashboards')
def dashboards():
    identity=user()
    ds=[{'key':d['key'],'label':d['label']} for d in config()['dashboards'] if d['key'] in identity.resources and identity.country in d['countries'] and identity.line_of_business in d['lines_of_business']]
    return jsonify(user={'id':identity.id,'country':identity.country,'line_of_business':identity.line_of_business},dashboards=ds)


def submit(value):
    identity=user()
    for key in value.dashboards:resource(identity,key)
    if value.plan:platform()['registry'].validate_dependencies(value.plan,identity)
    runtime=platform()
    store=current_app.extensions['conversations'];jobs=current_app.extensions['jobs']
    conversation=value.conversation_id or store.create(identity.id)
    history=store.get(identity.id,conversation)
    for turn in history:
        if turn['answer']:authorize_answer(identity,turn['answer'],runtime)
    if value.context_turn_ids and not set(value.context_turn_ids).issubset({t['id'] for t in history}):raise KeyError('Chat context is not available.')
    value=value.model_copy(update={'conversation_id':conversation})
    turn=store.begin(identity.id,conversation,value.question)
    try:
        history=[t for t in store.get(identity.id,conversation) if t['id']!=turn]
        for prior in history:
            if prior['answer']:authorize_answer(identity,prior['answer'],runtime)
    except BaseException:store.finish(turn,status='failed');raise
    async def execute(key,event,progress):
        try:
            answer=await run(runtime,identity,value,key,event,progress,{'history':history,'turn_id':turn})
            if event.is_set():raise asyncio.CancelledError()
            answer.update(conversation_id=conversation,turn_id=turn)
            store.finish(turn,answer)
            return answer
        except BaseException:
            store.finish(turn,status='cancelled' if event.is_set() else 'failed');raise
    try:key=jobs.submit(identity.id,execute)
    except BaseException:store.finish(turn,status='failed');raise
    store.bind(turn,key)
    return jsonify(job_id=key,run_id=key,conversation_id=conversation,turn_id=turn,status='pending'),202


@bp.post('/api/chat')
@bp.post('/api/v1/requests')
def chat():return submit(Request.model_validate(request.get_json()))


def owned_run(key):
    identity=user();result=current_app.extensions['jobs'].get(identity.id,key)
    answer=result.get('answer')
    if answer:authorize_answer(identity,answer,platform())
    return result


@bp.get('/api/v1/conversations')
def conversations():return jsonify(conversations=current_app.extensions['conversations'].list(user().id))


@bp.post('/api/v1/conversations')
def create_conversation():return jsonify(conversation_id=current_app.extensions['conversations'].create(user().id)),201


@bp.get('/api/v1/conversations/<key>')
def conversation(key):
    identity=user();turns=current_app.extensions['conversations'].get(identity.id,key)
    for turn in turns:
        if turn['answer']:authorize_answer(identity,turn['answer'],platform())
    return jsonify(conversation_id=key,turns=turns)


@bp.delete('/api/v1/conversations/<key>')
def delete_conversation(key):
    current_app.extensions['conversations'].delete(user().id,key);return jsonify(status='deleted')


@bp.get('/api/jobs/<key>')
@bp.get('/api/v1/runs/<key>')
def job(key):return jsonify(owned_run(key))


@bp.post('/api/v1/runs/<key>/cancel')
def cancel(key):return jsonify(current_app.extensions['jobs'].cancel(user().id,key))


@bp.get('/api/v1/runs/<key>/evidence')
def evidence(key):return jsonify(evidence=owned_run(key).get('answer',{}).get('evidence',[]))


@bp.get('/api/v1/runs/<key>/trace')
def trace(key):
    result=owned_run(key)
    return jsonify(run_id=key,status=result['status'],trace=result['trace'],metrics=result.get('answer',{}).get('metrics',{}))


@bp.get('/api/v1/skills')
def skills():return jsonify(skills=[m.model_dump() for m in platform()['registry'].list_authorized(user())])


@bp.get('/api/v1/tableau/assets')
def assets():
    identity=user();require(identity,['tableau.read'])
    return jsonify(assets=platform()['services']['tableau'].discover(identity,request.args.getlist('dashboard')))


@bp.post('/api/embed-token')
@bp.post('/api/v1/tableau/embed')
def embed():
    identity=user();require(identity,['tableau.read'])
    data=dict(request.get_json() or {})
    if 'dashboards' in data:
        selected=data.pop('dashboards')
        if len(selected)!=1:raise ValueError('Provide exactly one dashboard for this embed.')
        data['dashboard']=selected[0]
    value=ViewRequest.model_validate(data);service=platform()['services']['tableau']
    if config()['app']['mode']!='live':raise ValueError('Live Tableau is disabled in offline fixture mode.')
    descriptor=service.embed(identity,value).visualizations[0]
    return jsonify(token=service.token(identity,value),expires_in=300,visual=descriptor)


@bp.post('/api/v1/tableau/resolve')
def resolve():
    identity=user();require(identity,['tableau.read'])
    return jsonify(view=platform()['services']['tableau'].resolve(identity,ViewRequest.model_validate(request.get_json())))


def skill_request(name,params):
    return submit(Request(question=name,plan=ExecutionPlan(intent=UserIntent(question=name),tasks=[TaskSpec(id='task',skill_id=name,parameters=params)])))


@bp.post('/api/v1/tableau/analyze')
def analyze():return skill_request('tableau.data.analyze',ViewRequest.model_validate(request.get_json()).model_dump())


@bp.post('/api/v1/pricing/solve')
def pricing():
    value=QuoteInput.model_validate(request.get_json())
    return skill_request('eli.pricing.solve_'+value.solve_target,value.model_dump(exclude_unset=True))


class ArtifactRequest(Strict):
    run_id:str
    formats:list[str]


@bp.post('/api/v1/artifacts')
def artifacts():
    identity=user();require(identity,['artifact.write']);value=ArtifactRequest.model_validate(request.get_json())
    answer=owned_run(value.run_id).get('answer')
    if not answer:raise ValueError('Run is not complete.')
    document=Request(question='Generate document',formats=value.formats)
    source={'id':answer.get('turn_id',value.run_id),'answer':answer}
    result=asyncio.run(finalize_documents(platform(),identity,document,answer,reused_turns=[source]))
    return jsonify(artifacts=result['artifacts'],clarification=result.get('clarification'))


@bp.get('/api/v1/artifacts/<key>')
def download(key):
    identity=user();require(identity,['artifact.write']);path,mime,manifest=platform()['services']['artifacts'].get(identity.id,key)
    authorize_answer(identity,manifest,platform(),True)
    if request.args.get('manifest')=='true':return jsonify(manifest)
    return send_file(path,mimetype=mime,as_attachment=True,download_name='HKELI-draft'+path.suffix)


@bp.get('/api/v1/health')
def health():return jsonify(status='ok')


@bp.get('/api/v1/ready')
def ready():
    with current_app.extensions['jobs'].db() as db:db.execute('SELECT 1')
    return jsonify(status='ready',mode=config()['app']['mode'],live_connections='not_probed')
