"""Office-laptop diagnostics. Never print credentials, JWTs, exports or SDK responses."""
import argparse
import asyncio
import importlib.util
import json
import os
from app.config import load_config
from hk_platform.contracts.models import Identity


def preflight(config, user_id):
    problems=[]
    if config['app']['mode']!='live':problems.append('Set app.mode=live.')
    if len(os.getenv('HKELI_SESSION_SECRET',''))<32:problems.append('Set HKELI_SESSION_SECRET (at least 32 characters).')
    if config['identity'].get('local_test_enabled') is not True:
        problems.append('This probe supports local single-user testing only; corporate SSO must be tested through the authenticated app.')
    profile=next((u for u in config['users'] if u['id']==user_id),None)
    if not profile:problems.append('Selected user profile is absent.')
    tableau=config['tableau']
    for key in ('server','client_id','secret_id'):
        if not tableau.get(key) or 'example.com' in tableau.get(key,''):problems.append('Configure tableau.'+key+'.')
    if not os.getenv(tableau['secret_value_env'],''):problems.append('Set the configured Connected App secret environment variable.')
    username=os.getenv(config['identity'].get('tableau_username_env','TABLEAU_CONNECTED_USERNAME'),'') or (profile or {}).get('tableau_username','')
    if not username:problems.append('Set the configured Tableau username environment variable.')
    dashboards=config.get('dashboards',[])
    if not dashboards:problems.append('Configure at least one authorized dashboard.')
    if profile:
        for d in dashboards:
            if d['key'] not in profile.get('resources',[]):problems.append('Selected profile lacks a configured dashboard resource.')
            if profile['country'] not in d['countries'] or profile['line_of_business'] not in d['lines_of_business']:
                problems.append('Selected profile country/LOB does not match a configured dashboard.')
    if not config['stork'].get('model'):problems.append('Configure stork.model.')
    from app.integrations.stork_config import credentials
    try:credentials(config['stork'])
    except ValueError as error:problems.append(str(error))
    try:sdk=importlib.util.find_spec('ada_genai.google_genai') is not None
    except (ModuleNotFoundError,ValueError):sdk=False
    if not sdk:problems.append('Install the company-approved ada_genai SDK.')
    return problems,Identity.model_validate(dict(profile,tableau_username=username)) if profile else None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user',required=True,help='Local configured user ID')
    parser.add_argument('--tableau',action='store_true',help='Make real Tableau sign-in/discovery/sign-out requests')
    parser.add_argument('--stork',action='store_true',help='Send one nonfinancial synthetic diagnostic prompt to Stork')
    args=parser.parse_args()
    try:
        config=load_config();problems,identity=preflight(config,args.user)
        print(json.dumps({'stage':'local_configuration','status':'incomplete' if problems else 'pass','issues':problems}))
        if problems:return 1
        failed=False
        if args.tableau:
            try:
                from services.knowledge.service import Knowledge
                from services.tableau.service import TableauService
                views=TableauService(config,Knowledge(config['app']['knowledge_root'])).discover(identity,[d['key'] for d in config['dashboards']])
                print(json.dumps({'stage':'tableau_discovery','status':'pass' if views else 'no_configured_views','view_count':len(views)}))
                failed=not views
            except Exception as error:
                print(json.dumps({'stage':'tableau_discovery','status':'failed','error_type':type(error).__name__}))
                failed=True
        if args.stork:
            try:
                from app.integrations.vertex_adapter import generate_async
                text=asyncio.run(generate_async(config['stork'],'Synthetic connectivity diagnostic. Reply with exactly HKELI_CONNECTION_OK. No financial or user data is provided.'))
                ok=isinstance(text,str) and text.strip()=='HKELI_CONNECTION_OK'
                print(json.dumps({'stage':'stork_response','status':'pass' if ok else 'unexpected_response'}))
                failed=failed or not ok
            except Exception as error:
                print(json.dumps({'stage':'stork_response','status':'failed','error_type':type(error).__name__}))
                failed=True
        return int(failed)
    except Exception as error:
        print(json.dumps({'stage':'configuration','status':'failed','error_type':type(error).__name__}))
        return 1


if __name__=='__main__':raise SystemExit(main())
