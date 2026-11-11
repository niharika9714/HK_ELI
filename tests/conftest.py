import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from app import create_app
from app.config import load_config
from hk_platform.contracts.models import Identity

@pytest.fixture
def settings(tmp_path):
    config=load_config();config['app']['state_dir']=str(tmp_path/'state');return config

@pytest.fixture
def app(settings):
    app=create_app(settings);app.config['TESTING']=True
    # Synthetic test-only approvals. Production intentionally has no D3/D4 wording.
    templates=app.extensions['platform']['services']['artifacts'].templates
    for code in ('D3','D4','D5','D7'):
        templates.disclosures[code]={'approved':True,'version':'test-only','text':code+' SYNTHETIC TEST DISCLOSURE — not compliance wording'}
    yield app
    app.extensions['jobs'].close()

@pytest.fixture
def client(app):return app.test_client()

@pytest.fixture
def identity(settings):return Identity.model_validate(settings['users'][0])

def login(client,user='synthetic-hk-rm'):
    token=client.get('/api/session').json['csrf']
    response=client.post('/api/login',json={'user_id':user},headers={'X-CSRF-Token':token})
    assert response.status_code==200,response.json
    return {'X-CSRF-Token':response.json['csrf']}

def wait(client,key):
    import time
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        response=client.get('/api/v1/runs/'+key)
        assert response.status_code==200,response.json
        if response.json['status'] not in ('pending','running'):return response.json
        time.sleep(.02)
    raise AssertionError('Run deadline exceeded')
