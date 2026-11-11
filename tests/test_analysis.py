import pytest
from app.services.analysis import Analysis
from app.models import Plan

def test_full_100000_rows(tmp_path,settings):
    path=tmp_path/'large.csv'
    with path.open('w') as f:
        f.write('Sector,Notional\n')
        for i in range(100000):f.write(f'S{i%4},10\n')
    contract={'verified_export':True,'columns':{'Notional':{'type':'number','unit':'hkd','additive':True}},'grain':'synthetic position'}
    engine=Analysis(path,settings,contract)
    try:
        result=engine.execute(Plan(action='analyze',dimensions=['Sector'],measure='Notional',aggregation='sum',chart='bar'))
        assert result['input_rows']==100000
        assert all(float(r['value'])==250000 for r in result['rows'])
    finally:engine.close()

@pytest.mark.parametrize('text,columns',[
    ('Metric\n1\n\n',{'Metric':{'type':'number','additive':False}}),
    ('Snapshot,Metric\n2026-01-01,1\n2026-01-02,2\n',{'Metric':{'type':'number','additive':True},'Snapshot':{'type':'date','date_role':'snapshot'}}),
    ('Label,Metric\na,1\nb,\n',{'Metric':{'type':'number','additive':True}})])
def test_unsafe_totals_rejected(tmp_path,settings,text,columns):
    path=tmp_path/'input.csv';path.write_text(text)
    engine=Analysis(path,settings,{'verified_export':True,'columns':columns})
    try:
        with pytest.raises(ValueError):engine.execute(Plan(action='analyze',measure='Metric',aggregation='sum'))
    finally:engine.close()

def test_sql_identifiers_and_counts_rejected(tmp_path,settings):
    path=tmp_path/'input.csv';path.write_text('Metric\n1\n')
    e=Analysis(path,settings,{})
    try:
        with pytest.raises(ValueError):e.execute(Plan(action='analyze',measure='Metric; DROP TABLE data'))
        with pytest.raises(ValueError):e.execute(Plan(action='analyze',aggregation='count'))
    finally:e.close()
