import pytest
from services.analytics.business import BusinessAnalytics
from domains.hk_eli.metrics import load_metrics
from app.services.analysis import Analysis
from app.models import Plan
from conftest import login,wait

def test_distinct_rfq_currency_and_maturity(app,identity):
    business=app.extensions['platform']['services']['business']
    rows=business.run('rfq',identity).data['rows'][0]
    eligible=[i for i in range(120) if i%11!=0]
    assert rows['rfqs']==len(eligible)
    assert rows['won']==sum(i%3==0 for i in eligible) # Repeated RFQ event rows must not inflate conversion.
    for currency in ('HKD','USD'):
        result=business.run('client',identity,currency=currency)
        expected=sum((i%10+1)*100000 for i in eligible if ('USD' if i%13==0 else 'HKD')==currency)
        assert sum(r['notional'] for r in result.data['rows'])==expected
        assert all(e.unit in (currency,'number') for e in result.evidence)
    result=business.run('maturity',identity,days=5)
    assert all('2026-10-15'<r['maturity']<='2026-10-20' for r in result.data['rows'])

def test_mixed_currency_total_refused(tmp_path,settings):
    path=tmp_path/'mixed.csv';path.write_text('Currency,Notional\nHKD,10\nUSD,20\n')
    contract={'verified_export':True,'currency_column':'Currency','columns':{'Notional':{'type':'number','unit':'number','additive':True}}}
    engine=Analysis(path,settings,contract)
    try:
        with pytest.raises(ValueError):engine.execute(Plan(action='analyze',measure='Notional',aggregation='sum'))
        assert len(engine.execute(Plan(action='analyze',dimensions=['Currency'],measure='Notional',aggregation='sum'))['rows'])==2
    finally:engine.close()

def test_versioned_metric_policy():
    definitions=load_metrics();assert len(definitions)==14
    assert all(m.version and m.approval=='unapproved synthetic assumption' for m in definitions.values())
    assert not definitions['coupon'].additive and not definitions['concentration'].additive

def test_public_failure_diagnostic(client):
    headers=login(client)
    key=client.post('/api/chat',json={'question':'unrecognized fixture'},headers=headers).json['job_id']
    result=wait(client,key)
    assert result['error']['code']=='fixture_scenario_required'
    assert 'Q1' in result['error']['message']
