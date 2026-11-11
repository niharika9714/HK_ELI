import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from hk_platform.contracts.models import QuoteInput, EvidenceRecord, SkillOutput
from hk_platform.runtime.registry import resource


class MockPricing:
    version='fixture-pricing-1.0'

    def solve(self, terms: QuoteInput, identity):
        resource(identity,'mock:pricing')
        payload=terms.model_dump()
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        # Deliberately synthetic lookup bucketing, not a financial valuation formula.
        bucket=int(digest[:8],16)%20
        value=str(5+bucket/10) if terms.solve_target=='coupon' else str(85+bucket/10)
        now=datetime.now(timezone.utc)
        quote={'quote_id':'SYN-Q'+digest[:16],'terms':payload,'solved_value':value,'solve_target':terms.solve_target,
               'quoted_at':now.isoformat(),'expires_at':(now+timedelta(minutes=5)).isoformat(),'source_mode':'MOCK',
               'status':'indicative_only','approval_required':True,'version':self.version,
               'disclaimer':'Deterministic synthetic fixture bucketing; no market model or tradeable quote.',
               'applied_defaults':sorted(set(QuoteInput.model_fields)-terms.model_fields_set)}
        e=EvidenceRecord(id='E'+uuid.uuid4().hex,source_type='mock_pricing',source_mode='MOCK',source_id='mock:pricing',source_version=self.version,
                         as_of=now.isoformat(),authorization_scope=[identity.id],grain='synthetic quote',value=value,
                         unit='percent',calculation_id=terms.solve_target,warnings=[quote['disclaimer']])
        return SkillOutput(data=quote,evidence=[e],warnings=[quote['disclaimer']])


class LivePricing:
    def solve(self, terms, identity):
        raise ValueError('Live SPE contract and entitlement mapping are not configured; no quote substituted.')
