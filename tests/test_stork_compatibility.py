import asyncio
import sys
import types
import pytest
from app.integrations.stork_config import credentials
from app.integrations.vertex_adapter import generate_async
from conftest import login


def test_legacy_environment_names_and_missing_values(monkeypatch,tmp_path):
    cert=tmp_path/'ca.pem';cert.write_text('synthetic file, no TLS connection performed')
    settings={'one_bank_id_env':'One_Bank_ID','one_bank_password_env':'One_BANK_PASSWORD','ssl_cert_file_env':'SSL_CERT_FILE'}
    monkeypatch.setenv('One_Bank_ID','SYN-USER');monkeypatch.setenv('One_BANK_PASSWORD','SYN-SECRET');monkeypatch.setenv('SSL_CERT_FILE',str(cert))
    assert credentials(settings)=={'one_bank_id':'SYN-USER','one_bank_password':'SYN-SECRET','ssl_cert_file':str(cert)}
    monkeypatch.delenv('One_BANK_PASSWORD')
    with pytest.raises(ValueError,match='One_BANK_PASSWORD') as error:credentials(settings)
    assert 'SYN-SECRET' not in str(error.value)


def test_legacy_sync_adapter_runs_outside_async_loop(monkeypatch):
    module=types.ModuleType('synthetic_legacy_adapter')
    def generate(settings,prompt):
        async def work():return 'synthetic response'
        assert settings['one_bank_id']=='SYN-USER'
        assert prompt=='test without credentials'
        return asyncio.run(work())
    module.generate=generate;monkeypatch.setitem(sys.modules,module.__name__,module)
    monkeypatch.setenv('One_Bank_ID','SYN-USER')
    settings={'adapter':module.__name__+':generate','one_bank_id_env':'One_Bank_ID','timeout_seconds':2}
    assert asyncio.run(generate_async(settings,'test without credentials'))=='synthetic response'


def test_local_tableau_username_profile_fallback(client,app,monkeypatch):
    monkeypatch.delenv('TABLEAU_CONNECTED_USERNAME',raising=False)
    app.config['HKELI']['users'][0]['tableau_username']='synthetic-profile-user'
    login(client)
    from app.services.identity import current_user
    with client.session_transaction() as session:session['user']='synthetic-hk-rm'
    with app.test_request_context('/',base_url='http://localhost',environ_base={'REMOTE_ADDR':'127.0.0.1'}):
        from flask import session
        session['user']='synthetic-hk-rm'
        assert current_user(app.config['HKELI']).tableau_username=='synthetic-profile-user'
        monkeypatch.setenv('TABLEAU_CONNECTED_USERNAME','synthetic-environment-user')
        assert current_user(app.config['HKELI']).tableau_username=='synthetic-environment-user'
