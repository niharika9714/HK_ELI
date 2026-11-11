# Nine workflows and source expectations

Every offline request begins with its Q code; natural-language paraphrases without codes require live Stork. All listed business source operations are MOCK. Tableau display/data can be requested in live mode against independently authorized published assets; missing sources stay limitations.

| Code / intent example | Required skills | Defined output and limits |
|---|---|---|
| Q1: Review top underlying exposures | `eli.risk.concentration` | Top ten primary allocations, full-denominator shares, worst-of flagged subset, affected synthetic client IDs, upcoming maturity notional and synthetic threshold flag; not full basket look-through |
| Q2: Prepare executive update | Sales, RFQ, concentration, maturity, rollover, engagement, regional, digital, yield, sales trend, forecast | Fourteen explicit sections with evidence; exercise history/team/pipeline remain unavailable; forecast is a naive estimate, not market performance |
| Q3: Draft indicative product terms | Coupon/strike pricing skills | Required basket/tenor, disclosed defaults, deterministic synthetic lookup, expiry and approval requirement; no tradeable/live quote |
| Q4: Compare product coupons | `eli.product.yield` | Min/max and notional-weighted quoted coupon; realized return and performance history unavailable |
| Q5: Review client preferences/engagement | Client intelligence, engagement | Synthetic product/notional allocations and event counts; no suitability conclusion |
| Q6: Review near-term maturity/rollovers | Maturity, rollover | Fixed as-of window excludes as-of/includes end date; eligibility/status are synthetic definitions, not investment advice |
| Q7: Compare branch concentration | Branch concentration | Scoped branch/primary-underlying allocations; cross-currency totals unavailable |
| Q8: Compare regional performance | Regional performance | Temporally correct branch/district sales and revenue; team contribution/pipeline unavailable |
| Q9: Review digital journey | Digibank journey | Distinct synthetic event/client counts by stage; no inferred causal attribution or unapproved customer conversion formula |

Outputs contain source/version/date/scope/calculation evidence. The frontend provides result tables and suitable compact previews; live native matches preserve original Tableau views. Failures distinguish denied access, unavailable metadata/data, timeout and calculation contract rejection. An integration outage does not silently switch sources. Documents are evidence-linked drafts.

Machine-readable workflows: `domains/hk_eli/workflows.json`. Versioned demonstration semantics: `domains/hk_eli/metrics.json`. Benchmarks create six variants per code: standard, paraphrase, multi-source, missing-data, unauthorized and artifact. Tests and benchmark reports record observed results and keep business acceptance pending.
