# Verification record

2026-11-11 Tableau presentation update: **95 tests passed; 54/54 offline benchmarks passed**. Interactive chat descriptors retain requested controls; document finalization automatically exports PNGs with identical view/filter scope independent of model export-task selection. Tests cover descriptor deduplication, distinct filtered scopes, saved descriptor reuse with fresh capture disclosure, invalid PNG rejection, unsupported-control preservation/refusal, required image inclusion, and exact-scope in-run PNG reuse. Real Tableau filter parity, browser interactions and Office appearance remain unverified.

2026-11-11 template update: **89 tests passed; 54/54 offline benchmarks passed**. Registered template selection and typed outlines, sanitized assets, disclosure gating with retained chat evidence, external blocking across follow-ups, required section/evidence/image validation, Excel number/date/missing-value handling and formula escaping, shared Word/PDF outlines, explicit template precedence, and multi-format rollback are covered. The tests and benchmark CLI inject clearly labeled synthetic disclosure wording in memory only. Normal app generation remains blocked until owner-provided D3 (and D4 for pricing) is configured. Live Stork/Tableau, Office visual/pagination, official branding and external release remain unverified. See DOCUMENT_TEMPLATES.md.

2026-11-11 chat/document update: **79 tests passed**, with **54/54 offline benchmarks** retained. New tests cover format clarification/resume, one renderer invocation despite skill/output overlap, explicit UI format precedence, rejection of model-selected defaults, multiple document formats, saved context ownership/revocation/expiry/deletion, job-independent history restoration, concurrent-turn exclusion, live-source rediscovery denial, original reporting dates/evidence IDs and flat original-run provenance. A real loopback HTTP check completed Q1 → generic report request (`needs_format`) → DOCX/XLSX reply → two protected downloads and restored all three turns with the same 50 evidence records. Browser JavaScript interaction and real SSO/Stork/Tableau remain unverified. No raw CSV/image/token persistence was introduced.

2026-11-11 planning update: **64 tests passed; 54/54 offline benchmarks passed**. All 36 registered skills have richer guidance with schema-valid synthetic examples. New simulated-model tests cover multiple domains, preserving independent LIVE/MOCK branches, unavailable Tableau discovery with retained pricing results, missing/changed/forged requirement coverage, concrete parameter preservation, unauthorized skill/discovery rejection, source-mode relabeling and unresolved missing pricing inputs without invoking pricing. No clarification/resume workflow was added. The compact catalog holds 36 skill guides and 10 shared input schemas in 44,572 JSON characters (catalog portion only), avoiding repeated schema prompt inflation. Actual Stork semantic selection and live connections remain unverified.

2026-11-11 update: **46 tests passed** after adding source-independent shared reference. New tests cover no catalog/workbook dependency, bounded whole-entry retrieval, source-document isolation, reference refresh, classifier/planner/narrator propagation, actual-profile analytical propagation, permission gating, and rejection of narrative numbers introduced only by reference text. Real Stork semantic interpretation remains unverified.

Executed on 2026-11-10 on Windows, Python **3.11.4**, using the existing workspace `.venv` interpreter. Exact installed public dependency versions are captured in `requirements.lock`. A fresh independent virtual environment and container build have not been tested.

| Check | Observed result |
|---|---|
| New application `python -m pytest -q` | **40 passed** |
| Registered skill contracts | **36** skills exercised with typed inputs; external services replaced by explicit test doubles |
| `python benchmarks/run.py` | **54/54 offline scenarios passed**, six variants for each of nine use cases |
| Full CSV capacity | All **100,000 rows** read; independent exact aggregate checked; no sampled input |
| Financial boundary checks | Distinct RFQs, country/currency scope, fixed reporting date, maturity boundaries, null/snapshot/additivity/currency refusal |
| Actual-profile analytical decision | One model double sees the actual full-export profile, runtime schema rejects invented columns, and the same CSV snapshot yields checked aggregates |
| Private SDK call contract | Stub verifies `VertexClient().aio.models.generate_content(model=..., content=...)`, bounded calls and estimated-usage labeling; no live SDK connection |
| Reports | DOCX/PPTX/XLSX opened with their libraries; PDF structure checked; image presence, manifests, protected owner access and expiry tested |
| Real loopback HTTP smoke | HTTP page/session/login → Q2 background run → **11 tasks**, **140 evidence records**, **14 report sections**, four protected draft downloads; completed successfully |
| Baseline old app | Existing 24-test suite: 7 failures and 6 errors involving knowledge column contracts; recorded without modifying the old project |

The latest benchmark results and measured p50/p95 timings are in `var/benchmarks/results.json`, alongside `benchmark.xlsx`, `management.pptx` and `management.pdf`. These are generated synthetic artifacts and ignored by Git. The workbook includes expected/actual calculation checks, evidence manifests, timing, defects and pending reviewer/sign-off fields. The management deck/PDF includes an executed synthetic concentration example. Business quality scores remain pending rather than fabricated.

Fixture paraphrases retain Q1–Q9 scenario identifiers. Therefore the benchmark measures deterministic execution, calculations, evidence, missing-data handling, permissions and artifact generation; **it does not measure live Stork language understanding**. Fast fixture latency is not Tableau/Stork latency. Internal token counts are estimates until the private SDK's usage contract is supplied.

Not verified: real corporate SSO, private SDK installation/authentication, the specified model's availability, live Connected App scopes, actual authorized Tableau assets/CSV/images, browser rendering/interactions/third-party cookies, live SPE pricing, bank metric definitions, approved templates, fresh Mac setup, image build, OpenShift operation, security scanning, or production performance. No claim of successful bank connections or deployment is made.

The project is ready for local fixture review. Release recommendation: continue with scoped live integration testing and business/security acceptance; do not treat fixture pass rates as production approval.
