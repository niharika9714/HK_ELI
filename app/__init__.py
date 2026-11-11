import json
import logging
import os
import secrets
from pathlib import Path
from flask import Flask,jsonify
from .config import load_config,ROOT
from hk_platform.runtime.jobs import JobManager
from hk_platform.runtime.conversations import Conversations
from hk_platform.runtime.registry import SkillRegistry,Executor
from hk_platform.ai.gateway import StorkGateway
from hk_platform.ai.planner import Planner
from domains.hk_eli.skills import register_skills
from services.knowledge.service import Knowledge
from services.tableau.service import TableauService
from services.analytics.business import BusinessAnalytics
from services.pricing.service import MockPricing
from services.artifacts.service import ArtifactService
from mock_data.generate import initialize
from hk_platform.contracts.errors import PublicError


def create_app(config=None):
    settings=config or load_config();app=Flask(__name__)
    secret=os.getenv('HKELI_SESSION_SECRET','')
    if settings['app']['mode']=='live' and len(secret)<32:raise ValueError('Live mode requires HKELI_SESSION_SECRET of at least 32 characters.')
    app.secret_key=secret or secrets.token_urlsafe(48)
    app.config.update(HKELI=settings,MAX_CONTENT_LENGTH=65536,SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',SESSION_COOKIE_SECURE=settings['app'].get('secure_cookie',False))
    state=Path(settings['app']['state_dir']);state.mkdir(parents=True,exist_ok=True)
    initialize(state/'business.sqlite')
    registry=SkillRegistry();register_skills(registry)
    knowledge=Knowledge(settings['app']['knowledge_root'],settings['app'].get('max_knowledge_characters',80000))
    gateway=StorkGateway(settings['stork']) if settings['app']['mode']=='live' else None
    artifacts=ArtifactService(state/'artifacts',state/'jobs.sqlite',settings['app']['job_ttl_seconds']);artifacts.cleanup()
    services={'business':BusinessAnalytics(state/'business.sqlite'),'pricing':MockPricing(),
              'knowledge':knowledge,'tableau':TableauService(settings,knowledge),'gateway':gateway,'artifacts':artifacts}
    from domains.hk_eli.metrics import load_metrics
    services['metrics']=load_metrics()
    workflows=json.loads((ROOT/'domains/hk_eli/workflows.json').read_text())
    app.extensions['platform']={'services':services,'registry':registry,'workflows':workflows,
        'planner':Planner(registry,gateway,workflows),'executor':Executor(registry,settings['app']['io_concurrency'],settings['app']['run_timeout_seconds'])}
    app.extensions['jobs']=JobManager(state/'jobs.sqlite',settings['app']['job_workers'],settings['app']['max_jobs'],settings['app']['job_ttl_seconds'])
    app.extensions['conversations']=Conversations(state/'jobs.sqlite',settings['app'].get('conversation_ttl_seconds',86400))
    from .controllers.api import bp
    app.register_blueprint(bp)

    @app.errorhandler(PermissionError)
    def denied(error):return jsonify(code='access_denied',error=str(error)),403
    @app.errorhandler(ValueError)
    def invalid(error):return jsonify(code=error.code if isinstance(error,PublicError) else 'invalid_request',error=str(error)),400
    @app.errorhandler(KeyError)
    def absent(error):return jsonify(code='not_found',error='Resource absent or expired.'),404
    @app.errorhandler(OverflowError)
    def busy(error):return jsonify(code='capacity',error='Execution capacity busy.'),429
    @app.after_request
    def headers(response):
        response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY'})
        return response
    return app
