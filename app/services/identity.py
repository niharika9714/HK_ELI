import importlib
import ipaddress
import os
from urllib.parse import urlsplit
from flask import request,session
from hk_platform.contracts.models import Identity


def local_guard():
    try:local=ipaddress.ip_address(request.remote_addr or '').is_loopback
    except ValueError:local=False
    if not local or urlsplit(request.host_url).hostname not in ('localhost','127.0.0.1','::1') or any(
        key in request.headers for key in ('Forwarded','X-Forwarded-For','X-Forwarded-Host')):
        raise PermissionError('Local demonstration login requires direct localhost access.')


def current_user(config):
    settings=config['identity']
    if settings.get('local_test_enabled') is True:
        local_guard()
        if not session.get('user'):raise PermissionError('Sign in first.')
        profile=next((u for u in config['users'] if u['id']==session['user']),None)
        if not profile:raise PermissionError('Unknown profile.')
        identity=Identity.model_validate(profile)
        identity.tableau_username=os.getenv(settings.get('tableau_username_env','TABLEAU_CONNECTED_USERNAME'),'') or identity.tableau_username
        return identity
    resolver=settings.get('resolver','')
    if not resolver:raise PermissionError('Corporate SSO resolver is not configured.')
    module,function=resolver.split(':',1)
    return Identity.model_validate(getattr(importlib.import_module(module),function)(request))
