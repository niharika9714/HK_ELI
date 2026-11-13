import copy
from check_live import preflight


def test_fixture_preflight_lists_missing_configuration_without_secrets(settings,monkeypatch):
    monkeypatch.delenv('HKELI_SESSION_SECRET',raising=False)
    monkeypatch.delenv('TABLEAU_CONNECTED_SECRET_VALUE',raising=False)
    issues,identity=preflight(settings,'synthetic-hk-rm')
    assert issues and any('app.mode' in s for s in issues)
    assert any('secret environment' in s for s in issues)
    assert identity.id=='synthetic-hk-rm'


def test_preflight_enforces_local_identity(settings):
    config=copy.deepcopy(settings);config['identity']['local_test_enabled']=False
    issues,_=preflight(config,'synthetic-hk-rm')
    assert any('corporate SSO' in s for s in issues)
