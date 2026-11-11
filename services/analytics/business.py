import sqlite3
import uuid
from datetime import date, timedelta
from decimal import Decimal
from hk_platform.contracts.models import EvidenceRecord, SkillOutput
from hk_platform.runtime.registry import resource
from hk_platform.runtime.database import connect


class BusinessAnalytics:
    """Fixed reviewed query templates over synthetic tables. No model SQL."""
    def __init__(self, path): self.path = str(path)

    def run(self, operation, identity, days=5, currency='HKD'):
        resource(identity, 'mock:business')
        with connect(self.path) as db:
            db.row_factory = sqlite3.Row
            version, as_of = db.execute('SELECT version,as_of FROM metadata').fetchone()
            country = identity.country
            end=(date.fromisoformat(as_of)+timedelta(days=days)).isoformat()
            scoped=(country,currency,as_of)
            queries={
                'concentration': ('''SELECT underlying,currency,sum(notional) AS notional,
                    sum(CASE WHEN worst_of=1 THEN notional ELSE 0 END) AS worst_of_notional,
                    count(DISTINCT client) AS clients FROM positions WHERE country=? AND currency=? AND snapshot=?
                    GROUP BY underlying,currency ORDER BY notional DESC,underlying LIMIT 10''',scoped),
                'sales': ('''SELECT branch,currency,sum(amount) AS sales,sum(revenue) AS revenue FROM sales
                    WHERE country=? AND currency=? GROUP BY branch,currency ORDER BY sales DESC,branch''',(country,currency)),
                'rfq': ('''SELECT count(DISTINCT id) AS rfqs,count(DISTINCT CASE WHEN status='won' THEN id END) AS won
                    FROM rfqs WHERE country=?''',(country,)),
                'engagement': ('SELECT kind,count(*) AS events,count(DISTINCT client) AS clients FROM engagement WHERE country=? GROUP BY kind ORDER BY kind',(country,)),
                'maturity': ('''SELECT maturity,currency,count(DISTINCT id) AS deals,sum(notional) AS notional
                    FROM positions WHERE country=? AND currency=? AND snapshot=? AND maturity>? AND maturity<=?
                    GROUP BY maturity,currency ORDER BY maturity''',scoped+(as_of,end)),
                'rollover': ('''SELECT r.status,count(DISTINCT r.position_id) AS opportunities,sum(p.notional) AS notional
                    FROM rollovers r JOIN positions p ON r.position_id=p.id AND r.country=p.country
                    WHERE p.country=? AND p.currency=? AND p.snapshot=? AND r.eligible=1 AND p.maturity>? AND p.maturity<=?
                    GROUP BY r.status''',scoped+(as_of,end)),
                'client': ('''SELECT client,product,currency,sum(notional) AS notional,count(DISTINCT id) AS positions
                    FROM positions WHERE country=? AND currency=? AND snapshot=? GROUP BY client,product,currency ORDER BY notional DESC,client,product''',scoped),
                'branch': ('''SELECT branch,underlying,currency,sum(notional) AS notional FROM positions
                    WHERE country=? AND currency=? AND snapshot=? GROUP BY branch,underlying,currency ORDER BY notional DESC,branch,underlying''',scoped),
                'regional': ('''SELECT s.branch,b.district,s.currency,sum(s.amount) AS sales,sum(s.revenue) AS revenue
                    FROM sales s JOIN branches b ON s.branch=b.id AND s.trade_date BETWEEN b.valid_from AND b.valid_to
                    WHERE s.country=? AND s.currency=? GROUP BY s.branch,b.district,s.currency ORDER BY sales DESC,s.branch''',(country,currency)),
                'digital': ('''SELECT stage,count(DISTINCT id) AS events,count(DISTINCT client) AS clients
                    FROM channel_events WHERE country=? GROUP BY stage ORDER BY stage''',(country,)),
                'yield': ('''SELECT product,currency,count(*) AS positions,min(coupon) AS min_coupon,max(coupon) AS max_coupon,
                    sum(coupon*notional)/nullif(sum(notional),0) AS weighted_coupon FROM positions
                    WHERE country=? AND currency=? AND snapshot=? GROUP BY product,currency ORDER BY product''',scoped),
                'risk': ('''SELECT underlying,sum(ki_flag) AS ki_flags,sum(ko_flag) AS ko_flags FROM positions
                    WHERE country=? AND currency=? AND snapshot=? GROUP BY underlying ORDER BY underlying''',scoped),
                'trend': ('''SELECT trade_date,currency,sum(amount) AS sales FROM sales WHERE country=? AND currency=?
                    GROUP BY trade_date,currency ORDER BY trade_date''',(country,currency))
            }
            if operation not in queries: raise ValueError('Unsupported business operation.')
            sql,params=queries[operation]
            rows=[dict(r) for r in db.execute(sql,params)]
            warnings=['SYNTHETIC demonstration data; definitions are unapproved business assumptions. No live/mock joins.',
                      'Date window uses fixed fixture as-of date '+as_of+'; excludes as-of and includes end date.']
            if operation=='rfq':
                for r in rows: r['conversion']=str(Decimal(r['won'])/Decimal(r['rfqs'])) if r['rfqs'] else None
            if operation=='concentration':
                total=db.execute('SELECT sum(notional) FROM positions WHERE country=? AND currency=? AND snapshot=?',scoped).fetchone()[0] or 0
                threshold=db.execute("SELECT limit_value FROM thresholds WHERE metric='concentration_share'").fetchone()[0]
                for r in rows:
                    r['share']=str(Decimal(r['notional'])/Decimal(total)) if total else None
                    r['review_flag']=bool(total and Decimal(r['share'])>Decimal(str(threshold)))
                    r['affected_clients']=[v[0] for v in db.execute('SELECT DISTINCT client FROM positions WHERE country=? AND currency=? AND snapshot=? AND underlying=? ORDER BY client',scoped+(r['underlying'],))]
                    r['upcoming_maturity_notional']=db.execute('SELECT coalesce(sum(notional),0) FROM positions WHERE country=? AND currency=? AND snapshot=? AND underlying=? AND maturity>? AND maturity<=?',scoped+(r['underlying'],as_of,end)).fetchone()[0]
                warnings.append('Underlying is fixture primary allocation; worst-of is a flagged subset, not full basket look-through. Top 10 subset; shares use full scoped denominator.')
            if operation=='yield': warnings.append('Coupon is not realized return. No return series is available.')
            if operation=='regional':warnings.append('Team contribution and pending sales pipeline are unavailable in the supplied synthetic schema.')
            evidence=[]
            for row_index,row in enumerate(rows):
                for name,value in row.items():
                    if isinstance(value,(int,float,Decimal)) and not isinstance(value,bool) or name in ('share','conversion') and value is not None:
                        evidence.append(EvidenceRecord(id='E'+uuid.uuid4().hex,source_type='sqlite',source_mode='MOCK',source_id='mock:business',
                            source_version=version,as_of=as_of,authorization_scope=[country],grain='synthetic '+operation+' output row',
                            filters={'country':country,'currency':currency,'days':days},value=str(value),unit=currency if name in ('notional','sales','revenue','worst_of_notional','upcoming_maturity_notional') else 'ratio' if name in ('share','conversion') else 'percentage_points' if 'coupon' in name else 'number',
                            calculation_id=f'{operation}:{row_index}:{name}',warnings=warnings,metric=name,
                            statistic='ratio' if name in ('share','conversion','weighted_coupon') else 'minimum' if name.startswith('min_') else 'maximum' if name.startswith('max_') else 'sum' if name in ('notional','sales','revenue','worst_of_notional') else 'count',
                            dimensions={k:str(v) for k,v in row.items() if isinstance(v,str) and k not in ('share','conversion')}))
            additive=[name for name in ('notional','sales','revenue','worst_of_notional') if rows and name in rows[0]]
            return SkillOutput(data={'operation':operation,'rows':rows,'as_of':as_of,'currency':currency,'source_mode':'MOCK',
                'additive_columns':additive,'scope':{'country':country,'currency':currency},
                'limitations':['Empty results are not a zero portfolio.'] if not rows else []},evidence=evidence,warnings=warnings)
