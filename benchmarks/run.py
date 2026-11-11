"""54 executable fixture benchmarks. No LLM-as-judge or invented live results."""
import asyncio
import hashlib
import json
import math
import statistics
import sys
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.config import load_config,ROOT
from app.services.orchestrator import run
from hk_platform.contracts.models import Identity,Request
from hk_platform.ai.gateway import validate_narrative
from domains.hk_eli.executive import TITLES

VARIANTS=['standard','paraphrase','multi_source','missing_data','unauthorized','artifact']
QUESTIONS=['Which underlying allocations warrant review?','Prepare the executive business update.','Draft indicative product terms.',
           'Compare quoted coupons, with return limitations.','Review customer preferences and engagement.',
           'Review the upcoming maturity and rollover pipeline.','Compare branch and client concentrations.',
           'Summarize district and branch performance.','Analyze the digital customer journey.']

def independent_positions(country='HK',currency='HKD'):
    # Independently generated Python reference, never the application's SQL or output.
    return [{'i':i,'notional':(i%10+1)*100000,'underlying':f'SYN-STOCK{i%12}','branch':f'SYN-B{i%6}'} for i in range(120)
            if ('SG' if i%11==0 else 'HK')==country and ('USD' if i%13==0 else 'HKD')==currency]

def verify(code,answer,identity):
    checks=[]
    def check(metric,actual,expected):
        difference=actual-expected if isinstance(actual,(int,float)) and isinstance(expected,(int,float)) else 0 if actual==expected else None
        checks.append({'metric':metric,'actual':actual,'expected':expected,'difference':difference})
        assert math.isclose(actual,expected) if isinstance(actual,float) else actual==expected
    results=answer['analysis']['results'];rows=[v for v in results.values()]
    assert answer['status']=='complete',answer['warnings']
    facts=answer['evidence'];assert facts and {e['source_mode'] for e in facts}=={'MOCK'}
    assert all(e['as_of'] and e['calculation_id'] for e in facts)
    from hk_platform.contracts.models import Narrative,EvidenceRecord
    validate_narrative(Narrative.model_validate(answer['narrative']),[EvidenceRecord.model_validate(e) for e in facts])
    positions=independent_positions(identity.country)
    if code in (1,2):
        expected={}
        for p in positions:expected[p['underlying']]=expected.get(p['underlying'],0)+p['notional']
        expected=sorted(expected.items(),key=lambda x:(-x[1],x[0]))[:10]
        actual=next(v['rows'] for v in rows if v.get('operation')=='concentration')
        check('top10_underlying_notional',[(r['underlying'],r['notional']) for r in actual],expected)
        for r in actual:assert math.isclose(float(r['share']),r['notional']/sum(p['notional'] for p in positions))
    if code==2:assert [s['title'] for s in answer['report_sections']]==TITLES
    if code==3:
        for quote in rows:
            if 'terms' not in quote:continue
            digest=hashlib.sha256(json.dumps(quote['terms'],sort_keys=True).encode()).hexdigest();bucket=int(digest[:8],16)%20
            expected=str((5 if quote['solve_target']=='coupon' else 85)+bucket/10)
            check('synthetic_'+quote['solve_target'],quote['solved_value'],expected)
            assert quote['status']=='indicative_only'
    if code==4:
        actual=next(v['rows'] for v in rows if v.get('operation')=='yield')
        for row in actual:
            ps=[p for p in positions if f"SYN-PRODUCT{p['i']%3}"==row['product']]
            expected=sum((4+(p['i']%9)/2)*p['notional'] for p in ps)/sum(p['notional'] for p in ps)
            check('weighted_coupon_'+row['product'],row['weighted_coupon'],expected)
    if code==5:
        actual=next(v['rows'] for v in rows if v.get('operation')=='client')
        check('client_notional_total',sum(r['notional'] for r in actual),sum(p['notional'] for p in positions))
    if code==6:
        actual=next(v['rows'] for v in rows if v.get('operation')=='maturity')
        expected=sum(p['notional'] for p in positions if p['i']%31!=0 and 0<p['i']%40<=5)
        check('five_day_maturity_notional',sum(r['notional'] for r in actual),expected)
    if code==7:
        actual=next(v['rows'] for v in rows if v.get('operation')=='branch')
        check('branch_notional_total',sum(r['notional'] for r in actual),sum(p['notional'] for p in positions))
    if code==8:
        actual=next(v['rows'] for v in rows if v.get('operation')=='regional')
        check('regional_sales',sum(r['sales'] for r in actual),sum((p['i']%8+1)*100000 for p in positions))
        assert all(r['district']!='SYN-OLD' for r in actual)
    if code==9:
        actual=next(v['rows'] for v in rows if v.get('operation')=='digital')
        eligible=[i for i in range(120) if ('SG' if i%11==0 else 'HK')==identity.country]
        check('digital_stage_events',{r['stage']:r['events'] for r in actual},{'visit':len(eligible),'quote':len(eligible),'trade':sum(i%3==0 for i in eligible)})
    return checks

async def suite(app):
    platform=app.extensions['platform'];identity=Identity.model_validate(app.config['HKELI']['users'][0]);results=[]
    for code in range(1,10):
        for variant in VARIANTS:
            item={'id':f'Q{code}-{variant}','query':f'Q{code}: {QUESTIONS[code-1]}','variant':variant,'expected':'independent Python golden calculation',
                  'source':'MOCK','live_stork_evaluation':'pending','business_quality':'pending review','reviewer':'','sign_off':''}
            started=time.perf_counter()
            try:
                user=identity
                if variant=='unauthorized':user=identity.model_copy(update={'resources':[]})
                if variant=='missing_data':user=identity.model_copy(update={'country':'NO_DATA'})
                request=Request(question=item['query'],formats=['xlsx'] if variant=='artifact' else [])
                if variant=='paraphrase':request.question=f'Q{code}: Please rephrase this review: {QUESTIONS[code-1]}'
                if variant=='multi_source':
                    request.plan=platform['planner'].fixture_plan(request.question)
                    from hk_platform.contracts.models import TaskSpec
                    request.plan.tasks.append(TaskSpec(id='extra',skill_id='eli.sales.performance'))
                answer=await run(platform,user,request,item['id'],threading.Event(),lambda *args:None)
                if variant=='unauthorized':raise AssertionError('Unauthorized execution was allowed')
                if variant=='missing_data':
                    # Q3 mock pricing is identity-scoped and does not use business-country rows.
                    if code!=3:
                        for out in answer['analysis']['results'].values():
                            for row in out.get('rows',[]):
                                assert all(not isinstance(v,(int,float)) or v==0 for v in row.values())
                    item['expected']='no fabricated business rows; pricing remains synthetic identity-scoped'
                else:item['calculation_checks']=verify(code,answer,user)
                if variant=='artifact':assert answer['artifacts']
                item['evidence']=answer['evidence']
                item['actual_results']=answer['analysis']['results']
                item.update(status='pass',evidence_refs=answer['evidence_ids'],llm_calls=answer['metrics']['llm_call_count'],tokens=answer['metrics']['usage'],difference=0)
            except PermissionError:
                item.update(status='pass' if variant=='unauthorized' else 'fail',evidence_refs=[],difference=None)
            except Exception as error:item.update(status='fail',defect=type(error).__name__+': '+str(error)[:200])
            item['latency_seconds']=time.perf_counter()-started;results.append(item)
    return results

def reports(results,out):
    from openpyxl import Workbook
    from pptx import Presentation
    from reportlab.pdfgen import canvas
    out.mkdir(parents=True,exist_ok=True)
    passed=sum(r['status']=='pass' for r in results);times=sorted(r['latency_seconds'] for r in results)
    summary={'executed':len(results),'passed':passed,'failed':len(results)-passed,'p50_seconds':statistics.median(times),'p95_seconds':times[math.ceil(.95*len(times))-1],
        'scope':'Offline fixture execution and deterministic references. Paraphrase variants do NOT evaluate live Stork semantic interpretation.',
        'release_recommendation':'Fixture evaluation only; live integration and business acceptance pending.'}
    (out/'results.json').write_text(json.dumps({'summary':summary,'scenarios':results},indent=2),encoding='utf-8')
    wb=Workbook();wb.remove(wb.active)
    for title,keys in [('Scenario register',['id','query','variant','source']),('Expected results',['id','expected','calculation_checks']),('Actual results',['id','status','difference','calculation_checks']),('Evidence references',['id','evidence_refs']),('Performance',['id','latency_seconds','llm_calls','tokens']),('Quality scores',['id','business_quality']),('Defects',['id','defect']),('Review and signoff',['id','reviewer','sign_off'])]:
        ws=wb.create_sheet(title);ws.append(keys)
        for r in results:ws.append([json.dumps(r.get(k,'')) if isinstance(r.get(k), (list,dict)) else r.get(k,'') for k in keys])
        ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
    wb.save(out/'benchmark.xlsx')
    manifest=wb.create_sheet('Evidence manifest');manifest.append(['Scenario','Evidence ID','Provenance'])
    for item in results:
        for e in item.get('evidence',[]):manifest.append([item['id'],e['id'],json.dumps(e)])
    wb.save(out/'benchmark.xlsx')
    lines=['HK ELI - Management benchmark',f'Executed {len(results)}; passed {passed}; failed {len(results)-passed}',
           f"p50 {summary['p50_seconds']:.3f}s; p95 {summary['p95_seconds']:.3f}s",summary['scope'],summary['release_recommendation'],
           'Critical gates: unauthorized disclosure, fabricated figures and live quotations must fail.',
           'Business scoring pending: accuracy30%, evidence20%, relevance20%, completeness10%, visuals10%, actions10%.',
           'Nine use cases: concentration, executive, pricing, coupon, client, maturity, branch, regional, digital.',
           'All results are synthetic. Tableau, Stork, browser embedding and deployment remain unverified.']
    prs=Presentation()
    for text in lines:
        slide=prs.slides.add_slide(prs.slide_layouts[1]);slide.shapes.title.text=lines[0];slide.placeholders[1].text=text
    from services.artifacts.charts import bar_image
    from pptx.util import Inches
    import io
    measured=next((r['actual_results'] for r in results if r['id']=='Q1-standard' and r.get('actual_results')),None)
    preview=None
    if measured:
        preview=bar_image(next(v for v in measured.values() if v.get('operation')=='concentration'))
        if preview:
            slide=prs.slides.add_slide(prs.slide_layouts[5]);slide.shapes.title.text='Executed synthetic concentration example'
            slide.shapes.add_picture(io.BytesIO(preview),Inches(.5),Inches(1.5),width=Inches(9))
    prs.save(out/'management.pptx')
    pdf=canvas.Canvas(str(out/'management.pdf'))
    import textwrap
    for text in lines:
        y=780
        for line in textwrap.wrap(text,90):pdf.drawString(40,y,line);y-=20
        pdf.showPage()
    if preview:
        from reportlab.lib.utils import ImageReader
        reader=ImageReader(io.BytesIO(preview));w,h=reader.getSize()
        pdf.drawString(40,790,'Executed synthetic concentration example');pdf.drawImage(reader,40,400,width=510,height=510*h/w);pdf.showPage()
    pdf.save()
    return summary

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='var/benchmarks');args=parser.parse_args()
    with TemporaryDirectory() as directory:
        settings=load_config();settings['app']['mode']='fixture';settings['app']['state_dir']=directory
        app=create_app(settings)
        # Explicit benchmark-only synthetic wording; never persisted or used by the app server.
        registry=app.extensions['platform']['services']['artifacts'].templates
        for code in ('D3','D4','D5','D7'):
            registry.disclosures[code]={'approved':True,'version':'benchmark-only',
                'text':code+' SYNTHETIC BENCHMARK DISCLOSURE; not Compliance wording or approval.'}
        try:results=asyncio.run(suite(app))
        finally:app.extensions['jobs'].close()
    summary=reports(results,Path(args.out));print(json.dumps(summary,indent=2));sys.exit(bool(summary['failed']))
