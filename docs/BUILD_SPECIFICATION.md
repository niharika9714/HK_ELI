# HK ELI Intelligence Platform — Final Architecture & End-to-End Codex Build Specification

This consolidates the complete hybrid agentic architecture, reusable service contracts, Tableau integration, underlying-data analysis, Stork AI narration, mock business services, document generation, security, deployment and benchmarking into one implementation specification.

The goal is to extend your existing [HK_ELI_Stork_AI repository](https://github.com/niharika9714/HK_ELI_Stork_AI?utm_source=chatgpt.com) into a working enterprise-style intelligence platform, without replacing the Tableau functionality you've already built.

## Final architecture

Chatbot / API / Scheduled Reports

Business users · Charts · Analysis · Pricing · Documents

Stork AI Planning Layer

Intent classification · Semantic discovery · Typed skill plan

Native Python Agentic Runtime

DAG execution · Authorization · Parallelism · Budgets · Recovery

Reusable Skill and Service Layer

Tableau Intelligence

LIVE

Tableau Data Analysis

LIVE / scoped

Knowledge Retrieval

LOCAL

SPE Pricing

MOCK

Sales / RFQ / CRM

MOCK

Risk / Maturity / Market

MOCK

Document Generation

BUILD

Benchmarking

BUILD

Evidence & Financial Validation

Verified calculations · Source lineage · Freshness · Live/mock boundaries

Stork AI Grounded Insight Generation

Explain actual analytical findings, not invent financial metrics

Unified User Response

Tableau charts + narrative + evidence + downloadable reports

The most important addition is that Tableau view selection triggers two coordinated paths: one displays the original Tableau visualization, while the other retrieves sufficiently detailed authorized data, calculates the relevant findings and produces a Stork AI narrative.

Below is the master instruction you can give directly to Codex. It is designed to be self-contained, with implementation milestones, exact architectural constraints and acceptance criteria.

## Master Codex implementation instruction

# MASTER IMPLEMENTATION SPECIFICATION

# HK ELI Intelligence Platform — Enterprise Agentic Analytics & BI

**Version:** 1.0\
**Implementation mode:** End-to-end development in the existing repository\
**Repository:** [https://github.com/niharika9714/HK_ELI_Stork_AI](https://github.com/niharika9714/HK_ELI_Stork_AI)\
**Target:** Local Mac demonstration, subsequently OpenShift deployment\
**Primary users:** HK ELI Sales, Traders, Product Managers, Treasury Specialists, Relationship Managers and Management

---

# 1. Mission

Extend the existing Flask + Stork AI + Tableau application into a modular, reusable, enterprise-grade agentic intelligence platform.

The application must answer natural-language business questions by:

1. Understanding the user's business intent.
2. Discovering and selecting appropriate authorized data sources, Tableau views and analytical skills.
3. Executing a validated multi-source workflow.
4. Displaying relevant native Tableau visualizations when available.
5. Retrieving authorized data behind selected Tableau views at the required analytical grain.
6. Calculating financial metrics, identifying patterns, ranking exposures and detecting exceptions using deterministic analytical functions.
7. Generating evidence-grounded insights and narratives through Stork AI.
8. Supporting pricing ideation through an SPE-compatible service.
9. Generating downloadable DOCX, PPTX, PDF and XLSX artifacts.
10. Maintaining complete evidence provenance, permissions, audit trails and benchmark results.

**A working Tableau dashboard is not a complete answer.** For analytical queries, the platform must also examine the data and explain what it means.

The implementation must be modular enough for Tableau, Stork, knowledge retrieval, analytics, report generation and other skills to be reused in future projects.

---

# 2. Non-negotiable constraints

## 2.1 Existing code preservation

Inspect the entire existing repository before making changes.

Preserve the working:

- Flask application and chat experience.
- Tableau REST API authentication.
- Tableau Connected Apps JWT generation.
- Tableau Embedding API integration.
- Workbook/view discovery.
- Existing `catalogue.json` and semantic registry.
- CSV export functionality.
- Existing Tableau filtering.
- Existing DuckDB analytical safeguards.
- Existing security and entitlement checks.
- Existing `/api/chat`, `/api/jobs/{id}` and `/api/embed-token` behavior.

Do not replace working functionality with stubs.

Refactor behind compatibility adapters where necessary. Run regression tests after each milestone.

## 2.2 Technology stack

Use:

- Python 3.11+
- Flask
- Pydantic v2
- Private Stork AI SDK
- Tableau REST API 3.28
- Tableau Connected Apps and Embedding API v3
- DuckDB for governed analytical calculations
- SQLite for synthetic business data and initial persistent job metadata
- Markdown/JSON for domain knowledge and semantic definitions
- `python-docx`, `python-pptx`, `reportlab`, `openpyxl`
- Pytest for testing
- Structured logging and tracing
- Configurable background execution and worker limits
- Container-compatible configuration for OpenShift

**Do not introduce LangStack, LangChain or LangGraph.**

Do not replace the bank-approved Stork SDK with a public Gemini, Vertex AI, OpenAI or other client.

Do not add Elasticsearch, Redis, Kafka or a vector database unless a concrete requirement justifies it. Use interfaces that allow these systems to be added later.

## 2.3 Stork SDK contract

Preserve the bank-approved SDK invocation pattern:

```
import asyncio
from ada_genai.google_genai import VertexClient

async def generate_with_stork(settings, prompt):
    client = VertexClient()
    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model=settings["model"],
            content=prompt
        ),
        timeout=settings["timeout_seconds"]
    )
    return response.text
```

The existing synchronous wrapper may be retained for compatibility.

The new agentic runtime should call an async-compatible gateway.

The configured model identifier is `gemini-3.5-flash`, subject to verification in the bank environment.

Stork authentication, certificates and proxy settings come from approved environment configuration.

Do not assume the SDK supports native JSON-schema enforcement, tool calling or token usage reporting until verified.

Implement:

- Strict response parsing.
- Pydantic validation.
- Bounded repair attempts.
- Timeout and retry handling.
- Token accounting when exposed by the SDK.
- Clearly labeled token estimates otherwise.
- Prompt-template versioning.

Never log credentials or sensitive raw prompts by default.

---

# 3. Selected architecture

Implement a **Hybrid Service-Oriented Agentic Architecture**.

The architecture consists of:

1. Presentation and API layer.
2. Stork AI control plane.
3. Native Python execution plane.
4. Universal skill registry.
5. Reusable service adapters.
6. HK ELI domain-specific skill pack.
7. Business semantic and metric registry.
8. Evidence and provenance engine.
9. Response and artifact generation layer.
10. Observability, security and benchmarking layer.

Use a modular monolith initially.

Do not prematurely split the application into independently deployed microservices.

## 3.1 Execution principle

**Stork reasons. Python executes. Approved systems provide authoritative data.**

Stork AI may:

- Interpret user intent.
- Select skills.
- Generate typed execution plans.
- Resolve semantic ambiguity.
- Explain verified findings.
- Recommend evidence-supported actions.

Stork AI must not:

- Execute arbitrary Python.
- Generate unrestricted SQL for execution.
- Bypass permissions.
- Invent financial metrics.
- Invent live quotations.
- Modify evidence records.
- Create unrestricted recursive agent loops.
- Decide that synthetic data represents real bank data.

Financial calculations must be performed through approved deterministic operators.

---

# 4. Target repository structure

Adapt the existing repository incrementally toward:

```
HK_ELI_Stork_AI/
├── app/
│   ├── controllers/
│   ├── services/
│   ├── static/
│   └── templates/
│
├── platform/
│   ├── ai/
│   │   ├── stork_gateway.py
│   │   ├── planner.py
│   │   ├── prompts/
│   │   └── response_validator.py
│   ├── runtime/
│   │   ├── executor.py
│   │   ├── dag_validator.py
│   │   ├── skill_registry.py
│   │   ├── job_manager.py
│   │   └── budgets.py
│   ├── contracts/
│   │   ├── skills.py
│   │   ├── plans.py
│   │   ├── evidence.py
│   │   ├── analytics.py
│   │   └── artifacts.py
│   ├── security/
│   │   ├── identity.py
│   │   ├── entitlements.py
│   │   └── authorization.py
│   ├── evidence/
│   │   ├── registry.py
│   │   ├── validator.py
│   │   └── lineage.py
│   └── observability/
│
├── services/
│   ├── tableau/
│   │   ├── interface.py
│   │   ├── live_adapter.py
│   │   ├── catalog.py
│   │   ├── filter_resolver.py
│   │   ├── data_resolver.py
│   │   ├── analyzer.py
│   │   ├── embed.py
│   │   └── chart_export.py
│   ├── knowledge/
│   ├── pricing/
│   │   ├── interface.py
│   │   ├── mock_adapter.py
│   │   └── live_adapter.py
│   ├── data_access/
│   ├── analytics/
│   └── artifacts/
│
├── domains/
│   └── hk_eli/
│       ├── skills/
│       ├── metrics/
│       ├── policies/
│       ├── knowledge/
│       ├── report_specs/
│       └── semantic_catalog/
│
├── mock_data/
│   ├── fixtures/
│   ├── generators/
│   ├── schemas/
│   └── golden_answers/
│
├── benchmarks/
│   ├── cases/
│   ├── runners/
│   ├── evaluators/
│   └── reports/
│
├── shared_template/
├── tests/
├── docs/
├── deployment/
└── config/
```

Preserve existing import paths where needed. Introduce compatibility modules rather than performing an uncontrolled directory migration.

---

# 5. Universal Skill Contract

Every skill must expose:

- Unique skill ID.
- Semantic version.
- Domain.
- Description.
- Typed input schema.
- Typed output schema.
- Required permissions.
- Required capabilities.
- Supported source modes.
- Timeout.
- Retry policy.
- Idempotency.
- Cache policy.
- Execution function.

Define the following conceptual interface using Pydantic and Python ABCs:

```
class BaseSkill(ABC):
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        ...

    @abstractmethod
    async def execute(
        self,
        inputs: SkillInput,
        context: SkillContext
    ) -> SkillOutput:
        ...
```

Implement:

- `SkillRegistry.register()`
- `SkillRegistry.resolve()`
- `SkillRegistry.list_authorized()`
- `SkillRegistry.validate_dependencies()`

The registry must reject duplicate skill versions.

Skills must be discovered through allowlisted metadata. The planner must not import arbitrary Python modules.

The runtime constructs `SkillContext` from trusted identity and execution state, never from user or LLM-supplied identity fields.

## 5.1 Initial skills

Implement these reusable skills:

### Tableau

- `tableau.view.discover`
- `tableau.view.resolve`
- `tableau.view.embed`
- `tableau.view.filter`
- `tableau.data.retrieve`
- `tableau.data.profile`
- `tableau.data.analyze`
- `tableau.insight.generate`
- `tableau.chart.export`
- `tableau.view.compare`

### Knowledge

- `knowledge.search`
- `knowledge.retrieve`
- `knowledge.definition.resolve`

### Analytics

- `analytics.aggregate`
- `analytics.compare`
- `analytics.trend`
- `analytics.rank`
- `analytics.anomaly`
- `analytics.forecast`

### HK ELI

- `eli.sales.performance`
- `eli.rfq.conversion`
- `eli.risk.concentration`
- `eli.maturity.analyze`
- `eli.rollover.opportunity`
- `eli.client.engagement`
- `eli.regional.performance`
- `eli.digibank.journey`
- `eli.product.yield`
- `eli.pricing.solve_coupon`
- `eli.pricing.solve_strike`

### Documents

- `artifact.generate`
- `artifact.validate`
- `artifact.publish_draft`

Each skill must have unit tests and an example request/response fixture.

---

# 6. Stork AI Planner

The planner converts natural-language requests into a typed execution plan.

Create Pydantic models for:

- `UserIntent`
- `ExecutionPlan`
- `TaskSpec`
- `TaskDependency`
- `OutputSpecification`
- `SourceRequirement`
- `PlanValidationResult`

Each task must declare:

- Task ID.
- Skill ID.
- Skill version.
- Validated parameters.
- Dependency IDs.
- Expected output type.

The plan must support multiple sources and multiple Tableau views.

The planner should receive only authorized skill metadata and compact semantic descriptions.

Do not send the entire workbook catalog, raw database schema and full knowledge base in every prompt.

Use hierarchical discovery:

1. Identify domain and intent.
2. Retrieve relevant authorized skill metadata.
3. Retrieve relevant semantic definitions.
4. Generate execution plan.
5. Validate plan.
6. Execute.

Implement bounded repair for malformed plans.

If planning fails, use a deterministic fallback for supported common operations, or return a clear error.

---

# 7. Native Python DAG Executor

Implement a dependency-aware asynchronous execution engine.

Required capabilities:

- Validate task IDs and dependencies.
- Detect dependency cycles.
- Validate skill versions and input schemas.
- Enforce authorization before execution.
- Execute independent I/O tasks concurrently.
- Respect global and per-service concurrency limits.
- Enforce timeouts and execution budgets.
- Support cancellation.
- Retry only safe, idempotent operations.
- Persist task and job state.
- Support partial results with explicit warnings.
- Prevent uncontrolled agent recursion.

Initial configurable limits:

- Maximum 24 tasks per plan.
- Maximum 8 concurrent I/O tasks per application instance.
- Separate concurrency limits for Tableau and Stork.
- Maximum 1 repair attempt for malformed LLM plans.
- Maximum 2 additional reasoning rounds for analytical clarification.

These are development defaults and must be benchmarked.

Use bounded worker execution for CPU-heavy calculations and document generation.

For local development, persistent SQLite-backed jobs are acceptable, provided the implementation handles restart recovery, task ownership and safe state transitions.

Do not assume an in-process background thread is sufficient for reliable multi-replica OpenShift deployment.

---

# 8. Tableau Intelligence Service

This is a critical platform component.

Preserve the existing Tableau implementation and expose a reusable interface.

Required operations:

```
discover_assets(context)
resolve_view(query, context)
get_view_metadata(view_id, context)
resolve_filters(view_id, requested_filters, context)
get_embed_descriptor(view_request, context)
retrieve_view_data(view_request, context)
profile_view_data(dataset, context)
analyze_view_data(analysis_request, context)
export_chart(view_request, context)
compare_views(view_requests, context)
```

## 8.1 Metadata-driven behavior

Use the existing `catalogue.json` as the starting point.

Do not hardcode workbook, worksheet, measure or filter names into orchestration code.

The catalog should contain:

- Workbook IDs and names.
- View IDs and names.
- Domain.
- Supported concepts.
- Dimensions.
- Measures.
- Filters.
- Parameters.
- Date roles.
- Data grain.
- Snapshot semantics.
- Additive and non-additive metrics.
- Authorized data access methods.
- Refresh timestamps.
- Source versions.

Support aliases only when verified.

For example, similar field names such as `predict_result` and `predictive_result` must not be treated as equivalent without metadata confirmation.

## 8.2 Tableau view selection

Implement three matching cases:

**Complete match:** Retrieve the specific authorized Tableau view.

**Partial match:** Use semantic metadata to select the closest appropriate authorized view and apply validated filters.

**No match:** Determine whether approved data can support a custom chart. If so, generate one. Otherwise explain the limitation.

Never fabricate Tableau asset IDs or filter values.

## 8.3 Native embedding

Preserve Tableau Connected Apps authentication.

Support:

- Default filters.
- Modified filters.
- Parameters.
- Highlighting.
- Native Tableau tooltips.
- Independent side-by-side views.
- Hiding unnecessary workbook tabs.
- Per-view state isolation.

Do not expose Connected App secrets to the browser.

---

# 9. NEW CORE CAPABILITY — Tableau Data Intelligence & Insight Narration

Whenever the user asks an analytical question involving a Tableau view, execute two coordinated paths.

## Path A — Visualization

1. Resolve authorized Tableau view.
2. Validate requested filters.
3. Apply filters.
4. Generate embedding descriptor.
5. Display the original Tableau chart.

## Path B — Data Intelligence

1. Determine the analytical grain required by the question.
2. Resolve the best authorized data source associated with the selected view.
3. Retrieve the data through approved Tableau REST operations or approved governed data access.
4. Validate schema, grain, filters, date scope, row limits and completeness.
5. Calculate requested metrics using DuckDB/Python.
6. Identify rankings, trends, exceptions, concentrations and other relevant findings.
7. Register all findings in the evidence system.
8. Supply verified findings to Stork AI.
9. Generate an evidence-grounded business narrative.

Both paths should execute concurrently when their dependencies permit.

## 9.1 Data grain is mandatory

A Tableau CSV export may contain aggregated worksheet data rather than underlying transaction records.

Do not assume CSV rows represent individual deals.

Define supported grain levels:

- Dashboard aggregate.
- Worksheet summary.
- Mark-level detail.
- Deal-level detail.
- Approved governed source-level records.

The data resolver must determine whether the available data is sufficient for the requested calculation.

If the user requests individual maturing deals but the available Tableau view exposes only branch-level totals, the platform must:

- Search for an authorized detail view or approved data source.
- Use it if available.
- Otherwise disclose that deal-level analysis cannot be verified.

Never infer deal-level results from aggregated rows.

## 9.2 Chart and data consistency

The embedded chart and analytical dataset must agree on:

- Effective filters.
- Reporting period.
- Business timezone.
- Snapshot date.
- Organizational scope.
- Currency.
- Metric definitions.
- Source freshness.

If equivalent scope cannot be established, show an explicit mismatch warning.

Do not silently present a chart and narrative as reconciled when they use different populations.

## 9.3 Example acceptance scenario

**User:** "Show deals maturing in the next 5 days and summarize the key risks."

Expected workflow:

1. Interpret the date window using the approved business calendar and timezone.
2. Resolve an authorized maturity Tableau view.
3. Apply the appropriate maturity filters.
4. Embed the Tableau view.
5. Retrieve authorized deal-level data.
6. Calculate:
   - Number of maturing deals.
   - Total notional.
   - Maturity distribution.
   - Exposure by underlying.
   - Exposure by branch.
   - Available risk indicators.
   - Relevant review flags.
7. Generate a Stork AI narrative using validated calculations.
8. Display the chart, summary, key figures and evidence.
9. Clearly disclose missing data and unsupported risk calculations.

The runtime must calculate figures. Stork explains them.

## 9.4 Bounded analytical follow-up

Allow Stork AI to request additional approved analytical operations if the first result is insufficient.

For example:

- Group maturities by branch.
- Rank underlying exposures.
- Compare maturity notional against the prior period.
- Inspect flagged contracts.

Do not allow arbitrary SQL execution.

All follow-up operations must pass the same permission, schema and budget checks.

## 9.5 Tableau response contract

Return a structured result containing:

```
{
  "request_id": "example-id",
  "visualizations": [],
  "analysis": {
    "metrics": {},
    "findings": [],
    "limitations": []
  },
  "narrative": {
    "summary": "",
    "insights": [],
    "recommended_actions": []
  },
  "evidence_ids": [],
  "source_modes": ["LIVE"],
  "warnings": []
}
```

The frontend must render the analytical summary alongside the Tableau visualization.

For purely navigational queries, such as "Open the maturity dashboard," the data-analysis path may be skipped.

---

# 10. Financial Analysis and Semantic Registry

Create a versioned business semantic registry.

Each metric must define:

- Metric ID.
- Business name.
- Description.
- Formula.
- Source fields.
- Data grain.
- Date role.
- Currency.
- Aggregation rules.
- Additivity.
- Null handling.
- Snapshot handling.
- Approved filters.
- Business owner.
- Version.

Initial metric families:

- Outstanding notional.
- Revenue.
- RFQ conversion.
- Customer count.
- Concentration.
- Worst-of exposure.
- Maturity notional.
- Rollover rate.
- Product yield.
- Coupon.
- Strike.
- KO/KI indicators.
- Client engagement.
- Channel conversion.

Use deterministic functions for calculations.

Do not sum non-additive metrics or duplicate snapshot totals.

Do not mix currencies without an approved FX conversion policy.

Forecasts must be explicitly labeled as estimates and include their methodology and assumptions.

Where metric definitions are unconfirmed, implement versioned synthetic demonstration definitions and label them as unapproved business assumptions.

---

# 11. Evidence and Provenance Engine

Every material financial claim must have traceable evidence.

Implement a shared `EvidenceRecord` containing:

- Evidence ID.
- Source type.
- Source mode: LIVE or MOCK.
- Source ID.
- Source version.
- Retrieval timestamp.
- Business as-of timestamp.
- Applied filters.
- Authorization scope.
- Data grain.
- Metric definition version.
- Value and unit.
- Input evidence IDs.
- Calculation ID.
- Data classification.
- Warnings.

The runtime, not Stork AI, generates evidence IDs.

Derived metrics must reference their input evidence.

Narratives must reference evidence IDs for material claims.

Evidence references must be available in the UI and artifact manifest.

## 11.1 Hybrid live/mock isolation

The selected demonstration strategy is:

**Live Tableau + clearly labeled synthetic business services.**

Rules:

- Live Tableau data remains live.
- Synthetic business datasets remain synthetic.
- Do not fabricate relationships between live Tableau customers and synthetic CRM customers.
- Do not join live and synthetic records using coincidentally matching identifiers.
- Do not create a combined live/mock financial KPI unless an explicitly approved demonstration-only transformation defines its meaning.
- Mixed-source responses must disclose the different source modes.
- Mock pricing outputs must never be represented as live tradeable quotes.

For benchmarks, use a fully synthetic, independently reproducible fixture set when exact expected answers are required. This benchmark fixture mode is separate from the live demonstration flow.

---

# 12. Identity, Authorization and Entitlements

Implement a centralized entitlement registry.

The initial local demonstration identity includes:

- Username.
- Country.
- Line of business.
- Group membership.
- Allowed skills.
- Allowed resources.

Create a configurable demonstration profile with broad access for the authorized demo user.

Do not hardcode an authentication bypass into production code.

Implement three permission levels:

1. Platform permissions.
2. Domain/skill permissions.
3. Source/resource permissions.

Tableau must independently enforce its native workbook/view permissions and row-level security.

An application entitlement must never override Tableau authorization.

The entitlement registry may use Python dictionaries for efficient in-memory lookup and SQLite for persistence.

All cache and artifact access must be authorization-aware.

For future OpenShift deployment, provide an interface for corporate SSO integration using verified identity claims.

---

# 13. Knowledge Retrieval

Initial knowledge sources:

- Markdown.
- JSON.
- Approved local files.

Use direct retrieval and lightweight indexing.

Support:

- Domain-scoped search.
- Exact definition lookup.
- Document versioning.
- Source citations.
- Content hashes.
- Weekly manual refresh.
- Configurable storage roots.

Keep repository-bundled knowledge accessible under Linux/OpenShift.

Do not assume Mac-specific paths.

Do not introduce a vector database solely for architectural appearance.

Allow a future Elasticsearch adapter without changing skill contracts.

Treat retrieved document content as untrusted data, not executable instructions.

---

# 14. SPE Pricing Service

Create a reusable pricing interface with mock and live implementations.

Initial supported operations:

- Solve coupon.
- Solve strike.

Use the provided indicative request fields:

- Entity.
- Product.
- Issue date lag.
- Currency.
- Underlying basket.
- Tenor.
- Strike.
- KI type and level.
- KO type and level.
- Coupon frequency.
- Price.
- Solve target.

The actual SPE request and response schema is not fully confirmed. Treat the supplied structure as a draft contract, not a verified production API specification.

## 14.1 Mock pricing

Create deterministic synthetic quote fixtures.

For identical inputs and fixture version, return identical results.

Include:

- Quote ID.
- Synthetic pricing inputs.
- Solved value.
- Timestamp.
- Expiry.
- Source mode MOCK.
- Indicative-only status.
- Approval requirement.
- Pricing methodology disclaimer.

Do not claim the mock engine represents actual market pricing.

## 14.2 Missing parameters

Support controlled defaults from a versioned product policy.

Stork may extract user-supplied parameters and propose missing values only from approved defaults.

Disclose applied defaults.

Ask for clarification when essential parameters remain ambiguous.

Do not invent issuer-specific terms or live market inputs.

A quotation must not be represented as executable or tradeable without the approved pricing and trading workflow.

---

# 15. Synthetic Business Data Services

Create deterministic SQLite datasets for:

1. Sales transactions.
2. RFQs.
3. Outstanding ELI positions.
4. Customer profiles.
5. Client engagement events.
6. Maturity schedules.
7. Rollover opportunities.
8. Branch and district hierarchy.
9. Digibank channel activity.
10. Market observations.
11. Product reference data.
12. Risk thresholds and synthetic business rules.

Use seeded generators and versioned fixtures.

Maintain consistent synthetic identifiers across these mock tables.

Include realistic edge cases:

- Duplicate RFQs.
- Multiple transactions per client.
- Multiple underlyings per product.
- Different currencies.
- Missing dates.
- Zero denominators.
- Stale prices.
- Changing branch ownership.
- Snapshot duplication.
- Unauthorized records.
- Expired quotations.

Create an independently calculated golden-answer dataset.

Every synthetic analytical output must identify its source, dataset version and mock status.

---

# 16. HK ELI Business Skills and Nine Queries

Implement all nine core use cases.

## Q1 — Concentration

Top 10 underlying exposures, individual and worst-of concentration, risk breaches, maturities and affected customers.

## Q2 — Executive Business Review

Sales, RFQ conversion, engagement, concentration, maturity, rollover, district/branch performance, forecast and management actions.

Support the 14-section ELI Executive Business Update specification:

1. Executive Summary.
2. As-of Business Date.
3. Business Financials.
4. Sales Momentum.
5. Top Underlying and Sector.
6. RFQ Demand Analysis.
7. Worst-of Underlying Exposure.
8. Stock Concentration.
9. Exercise Stock Analysis.
10. Maturity Calendar.
11. Rollover Summary.
12. Customer Status.
13. Management Actions.
14. Executive Conclusion.

## Q3 — Product Ideation

Generate indicative ELI product ideas based on underlying basket, tenor, coupon and pricing constraints.

Use SPE-compatible pricing skills.

## Q4 — Yield and Return Dashboard

Display relevant Tableau views and explain supported yield, return and product performance measures.

## Q5 — Client Intelligence

Analyze synthetic client trading patterns, preferences and engagement, with entitlement-aware access.

## Q6 — Maturity and Rollover

Identify upcoming maturities, rollover opportunities and contracts requiring review or repricing.

## Q7 — Concentration by Client and Branch

Analyze asset concentration, organizational distribution and supported risk thresholds.

## Q8 — Regional Performance

Analyze district/branch performance, team contribution and pipeline.

## Q9 — Digibank Analytics

Analyze channel sales, conversion and customer journey events.

For each use case, implement:

- Intent examples.
- Required skills.
- Source requirements.
- Expected analytical outputs.
- Evidence requirements.
- Visualization behavior.
- Failure behavior.
- Mock fixtures.
- Automated tests.

---

# 17. Unified Chat Response

The chatbot must support multiple content types in one answer.

A response may include:

- Narrative text.
- KPI summaries.
- Native Tableau visualizations.
- Two or more side-by-side Tableau views.
- Custom interactive charts.
- Tables.
- Source citations.
- Warnings.
- Downloadable reports.

Implement a typed response envelope.

The frontend must not rely on parsing arbitrary Markdown to discover charts or artifacts.

## 17.1 Chart behavior

When an appropriate Tableau view exists:

- Prefer native Tableau embedding.
- Preserve published chart appearance.
- Apply approved filters.
- Hide unnecessary tabs.
- Preserve native tooltips.

When no appropriate view exists:

- Retrieve approved data.
- Validate chart compatibility with available dimensions and measures.
- Generate an appropriate custom chart.
- Provide tooltips and source references.

When the user requests a different chart type:

- Validate whether the data supports the requested visualization.
- Create the custom chart if valid.
- Otherwise explain the limitation.

---

# 18. Artifact Generation

Implement downloadable:

- DOCX.
- PPTX.
- PDF.
- XLSX.

Use a shared validated report model.

The report model must contain:

- Title.
- Reporting period.
- As-of date.
- Sections.
- Verified metrics.
- Tables.
- Chart references.
- Evidence references.
- Source-mode disclosures.
- Disclaimers.
- Approval status.

Use the `shared_template` directory when templates are provided.

Support configurable template paths for local Mac and OpenShift.

For Tableau charts:

- Export the authorized filtered chart as an image.
- Prefer PNG for clarity.
- Support JPEG conversion where requested.
- Preserve source references.
- Embed the static image in generated documents.

Validate that report figures match the analytical evidence.

Generated artifacts must have:

- Unique artifact ID.
- Authorized owner.
- Content type.
- Retention policy.
- Draft/released status.
- Evidence manifest.
- Protected download endpoint.

Do not allow a failed report-generation step to destroy already validated analytical results.

---

# 19. Caching, Timeouts and Failure Handling

Implement source-specific policies.

## Caching

- Tableau catalog: short-lived, refreshable metadata cache.
- Tableau data: source-refresh-aware and authorization-scoped.
- Knowledge: version/content-hash based.
- Synthetic analytics: dataset-version based.
- Pricing: expiry-aware; no unsafe cross-user reuse.
- Artifacts: owner-scoped storage.

Cache keys must include relevant permissions, source versions, filters and reporting scope.

Reauthorize cached results before serving them.

## Failures

- Tableau unavailable: report unavailable live evidence.
- Tableau export incomplete: reject unsupported analytical claims.
- Stork timeout: bounded retry and explicit failure.
- Pricing unavailable: no fabricated live quote.
- Unauthorized data: deny without leakage.
- Missing required metrics: mark incomplete.
- Invalid calculations: reject.
- Partial source failure: return only independently valid findings.
- Document generation failure: preserve analytical results.

All failures must be observable through structured logs and task statuses.

---

# 20. API Contracts

Preserve existing endpoints.

Add versioned APIs:

```
POST /api/v1/requests
GET  /api/v1/runs/{run_id}
GET  /api/v1/runs/{run_id}/evidence

GET  /api/v1/skills

GET  /api/v1/tableau/assets
POST /api/v1/tableau/resolve
POST /api/v1/tableau/embed
POST /api/v1/tableau/analyze

POST /api/v1/pricing/solve

POST /api/v1/artifacts
GET  /api/v1/artifacts/{artifact_id}

GET  /api/v1/health
GET  /api/v1/ready
```

Define Pydantic request and response models.

Enforce authorization, CSRF protection where applicable, input validation and resource limits.

Do not expose raw source credentials or unrestricted query execution.

---

# 21. Observability and Audit

Every run must record:

- Run ID.
- User authorization scope.
- Request type.
- Plan version.
- Skills invoked.
- Source modes.
- Source versions.
- Task statuses.
- Execution timings.
- Retries.
- Validation failures.
- Evidence IDs.
- Artifact IDs.
- Stork model.
- LLM call count.
- Actual or estimated token usage.
- Total latency.

Use correlation IDs across services.

Support export of sanitized execution traces for debugging and benchmarking.

Do not log raw sensitive client records by default.

---

# 22. Benchmarking and Business Acceptance

Build a repeatable benchmark suite based on the nine business queries.

Create 54 initial scenarios: six variants for each query.

Variants:

1. Standard query.
2. Paraphrased query.
3. Multi-source query.
4. Missing-data scenario.
5. Unauthorized-access scenario.
6. Complex visualization/artifact scenario.

Add cross-cutting tests for outages, stale data, large exports, prompt injection, concurrent requests and invalid pricing inputs.

## 22.1 Automated evaluation

Measure:

- Exact financial calculation accuracy.
- Evidence completeness.
- Source and filter correctness.
- Plan validity.
- Skill selection.
- Authorization.
- Mock/live isolation.
- Artifact integrity.
- End-to-end success.
- p50/p95 latency.
- Stork call counts.
- Input/output tokens where available.
- Retry and failure rates.

Use independent expected-answer calculations rather than evaluating only with an LLM.

## 22.2 Business scoring

Initial scoring weights:

- Financial and analytical accuracy: 30%.
- Evidence and traceability: 20%.
- Business relevance: 20%.
- Completeness: 10%.
- Visualization and artifact quality: 10%.
- Actionability: 10%.

Treat critical failures as mandatory gates.

Unauthorized disclosure, invented material figures and fabricated live quotations must fail regardless of aggregate score.

## 22.3 Business benchmark deliverables

Generate:

**Benchmark Workbook (XLSX)**

- Scenario register.
- Expected results.
- Actual results.
- Evidence references.
- Calculation differences.
- Latency.
- Token usage.
- Quality scores.
- Defects.
- Reviewer comments.
- Sign-off.

**Management Benchmark Deck (PPTX/PDF)**

- Project scope.
- Nine use cases.
- Test coverage.
- Accuracy and quality results.
- Performance.
- Example visualizations.
- Evidence traceability.
- Open issues.
- Release recommendation.

Never populate benchmark dashboards with invented test results. Show pending values until tests execute.

---

# 23. Security Requirements

Implement:

- Verified identity context.
- Resource-level authorization.
- Tableau native permission enforcement.
- Row-level security preservation.
- Restricted data minimization.
- Prompt-injection resistance.
- Source allowlists.
- Parameterized analytical execution.
- No arbitrary LLM-generated SQL.
- No arbitrary filesystem access.
- Protected artifact downloads.
- Safe temporary-file handling.
- Secret-free logs.
- Configurable retention.
- Cache isolation.

Audit the existing repository for accidentally committed secrets or sensitive configuration.

Do not print discovered secrets.

If credentials appear to have been committed, document remediation and recommend rotation.

Do not delete or rewrite repository history automatically.

---

# 24. Deployment Requirements

## Local Mac

Provide:

- Dependency installation.
- Environment configuration example.
- Synthetic dataset initialization.
- Mock pricing startup.
- Flask startup.
- Worker startup if required.
- Test commands.
- Benchmark commands.
- Troubleshooting instructions.

## OpenShift

Provide:

- Containerfile.
- Non-root execution support.
- Environment-driven configuration.
- Health/readiness probes.
- CA certificate handling.
- Corporate proxy configuration.
- Secrets integration.
- Persistent artifact storage abstraction.
- Persistent job-store abstraction.
- Deployment manifests or Helm-compatible configuration.

Do not assume local SQLite is suitable for multi-replica production deployment.

For OpenShift, document the required migration to an approved shared database and durable job system before scaling horizontally.

---

# 25. Implementation Milestones

Implement sequentially.

## M0 — Baseline and repository audit

Inspect repository, run existing tests, document architecture and migration plan.

**Exit:** Existing functionality understood and baseline recorded.

## M1 — Contracts and skill registry

Implement universal skill contracts, registry, entitlement models and tests.

**Exit:** Typed skills can be registered, resolved and authorized.

## M2 — Tableau service refactor

Wrap existing Tableau integration behind reusable interfaces.

Add filter metadata, multi-view support and chart export.

**Exit:** Existing Tableau workflows still pass regression tests.

## M3 — Tableau Data Intelligence

Implement authorized data retrieval, grain validation, deterministic analysis, evidence registration and Stork insight narration.

**Exit:** A selected Tableau view can produce both a native chart and an accurate analytical explanation.

## M4 — Stork planner and DAG runtime

Implement typed planning, validation, task dependencies, bounded concurrency, persistent jobs and failure handling.

**Exit:** Multi-skill workflows execute safely.

## M5 — Evidence and semantic registry

Implement metric definitions, evidence lineage, source classification and financial reconciliation.

**Exit:** Material claims can be traced to verified inputs.

## M6 — Synthetic business services

Implement SQLite datasets, domain analytics and mock pricing.

**Exit:** All nine business queries have deterministic synthetic coverage.

## M7 — Artifact generation

Implement DOCX, PPTX, PDF and XLSX output with templates and evidence manifests.

**Exit:** All four formats open correctly and reconcile with analytical results.

## M8 — Frontend integration

Integrate native Tableau charts, side-by-side views, analytical narratives, custom charts, citations and downloads.

**Exit:** The user can complete all nine demonstration workflows from the chat UI.

## M9 — Benchmarking

Implement 54 golden scenarios, automated evaluation and management reporting.

**Exit:** Benchmark results are reproducible and business review materials are generated.

## M10 — Deployment readiness

Provide local startup, container packaging, OpenShift configuration and operational documentation.

**Exit:** Local deployment works end to end; OpenShift prerequisites and remaining environment dependencies are explicit.

---

# 26. Mandatory End-to-End Acceptance Scenarios

At minimum, demonstrate:

### Scenario A — Tableau + narration

User asks for deals maturing in five days.

System selects a Tableau maturity view, applies filters, retrieves sufficiently detailed authorized data, calculates maturity statistics and generates a grounded narrative.

### Scenario B — Side-by-side dashboards

User compares two Tableau views.

System displays both independently, preserves each filter state and explains supported differences.

### Scenario C — Custom chart

User requests a visualization not available in Tableau.

System retrieves approved data, validates dimensions/measures, creates a custom chart and provides evidence.

### Scenario D — Multi-source executive review

System combines permitted live Tableau findings with separately labeled synthetic business analysis, without creating misleading cross-source financial totals.

### Scenario E — Product ideation

System extracts product terms, applies approved defaults, invokes deterministic mock pricing and clearly labels the quotation as synthetic and indicative.

### Scenario F — Document generation

System produces a downloadable executive report with verified figures, chart images, disclaimers and an evidence manifest.

### Scenario G — Unauthorized access

System refuses restricted resources even if the LLM attempts to request them.

### Scenario H — Incomplete Tableau data

System displays the authorized chart but refuses to invent unsupported deal-level analysis.

### Scenario I — Performance and regression

Existing Tableau functionality continues to work, while new workflows meet agreed correctness and performance gates.

---

# 27. Required Development Practices

Before each milestone:

1. Inspect relevant existing code.
2. Identify backward-compatibility requirements.
3. Write or update tests.
4. Implement the smallest coherent change.
5. Run tests.
6. Document results and remaining limitations.

Do not claim a live integration is working unless it has been exercised successfully.

If bank-only systems are unavailable, implement a contract-compatible mock and document how to verify the live adapter later.

Do not silently skip required capabilities.

Do not replace incomplete implementations with hardcoded example responses.

Keep configuration separate from code.

Preserve working Tableau behavior throughout.

---

# 28. Required Final Deliverables

Produce:

1. Complete updated project source code.
2. Updated dependency configuration.
3. Local Mac startup scripts.
4. OpenShift-compatible container/deployment configuration.
5. Versioned service contracts.
6. Skill registry and domain skills.
7. Stork AI planner and DAG executor.
8. Reusable Tableau Intelligence Service.
9. Tableau Data Intelligence and Insight Narration.
10. Synthetic business datasets and mock pricing service.
11. Evidence and semantic registry.
12. DOCX/PPTX/PDF/XLSX generation.
13. Integrated chatbot frontend.
14. Automated tests.
15. Nine-query benchmark suite.
16. Benchmark Excel workbook generator.
17. Management PowerPoint benchmark generator.
18. Architecture and operational documentation.
19. Migration and compatibility report.
20. Security review and known limitations.

Include a complete README with reproducible setup and test commands.

---

# 29. Execution Instruction for Codex

Begin by inspecting the existing repository and running its current tests.

Create a milestone checklist in the repository.

Implement M0 through M10 in sequence, making working code changes rather than stopping after an architecture proposal.

After each milestone:

- Run relevant tests.
- Record passing and failing tests.
- Document implementation changes.
- Update the checklist.
- Continue when the milestone's acceptance criteria are satisfied.

If a required live bank dependency is unavailable, implement and test the mock-compatible path, record the live verification as pending, and continue.

Do not bypass critical security or correctness failures merely to advance to the next milestone.

Do not make destructive repository changes or push to the remote repository without explicit authorization.

At completion, provide:

- Files created or modified.
- Architecture summary.
- Test and benchmark results.
- Exact local startup instructions.
- Working demonstration scenarios.
- OpenShift deployment instructions.
- Remaining bank-environment verification requirements.

**Final success criterion:** A user can ask a business question in the existing HK ELI chatbot and receive the most relevant authorized Tableau visualization, accurate data-driven analysis, an evidence-grounded Stork AI narrative and, when requested, a downloadable professional report—while retaining the existing application's functionality.

## How I recommend using this with Codex

Paste the master specification into Codex with your repository open in VS Code. Use Agent mode so Codex can inspect existing files, create modules, run tests and modify the application.

For the first run, have Codex establish the repository baseline before changing code. Then let it implement the milestones in order, verifying each one. This reduces the chance that a broad refactor breaks the existing Tableau Connected Apps integration.

There are three things I would insist on seeing in the first working demonstration:

Native Tableau + intelligent narration

A filtered Tableau maturity chart appears with a genuine analysis of its authorized data, including the correct figures, source references and business implications.

Multi-skill agentic workflow

A complex question invokes multiple skills, executes independent retrievals concurrently, reconciles the evidence and generates one coherent answer.

Business-ready executive output

The user can generate a management report containing verified metrics, charts, analytical commentary, source disclosures and downloadable files.

One important distinction: the specification is implementation-ready, but actual deployment readiness still depends on testing your private Stork SDK, Tableau permissions and exports, corporate network, and OpenShift environment. Codex should report those verifications separately rather than claiming they passed using mocks.

The key principle for the entire build is: don't create nine isolated chatbots for nine business questions. Build one governed agentic platform with reusable skills, and let the HK ELI domain supply its business definitions, data sources and analytical workflows.