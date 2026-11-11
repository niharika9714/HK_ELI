# HK ELI Intelligence Platform

Independent Flask application built from the supplied specification. The existing `HK_ELI_Stork_AI` application is unchanged. Start with **fixture mode**, which runs without Tableau or Stork and labels every result MOCK. Production integration code is present; live connectivity and corporate approval are pending.

Document generation now uses a [versioned template registry](shared_template/README.md), evidence-bound outlines and sanitized PPTX/DOCX/XLSX shells. **Configure the required D3 risk disclosure before generating documents**; D4 is additionally required for pricing content. Analytical chat remains available without them. Client briefing is registered but disabled pending external/client-scope approval. See [template implementation and limits](docs/DOCUMENT_TEMPLATES.md).

## Run on Windows

```powershell
Set-Location "C:\Users\nihar\OneDrive\Desktop\Programing Folder\HKELI\HK_ELI_STORK_AI_COMPLETE"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Copy-Item config/config.example.toml config/config.local.toml
.\.venv\Scripts\python.exe run.py
```

Open http://127.0.0.1:8021, select `synthetic-hk-rm`, click **Sign in**, select Q1–Q9 and send. Check report formats before sending to generate protected draft downloads. Q2 produces a fourteen-section executive draft with explicit unavailable sections. HK and SG fixture profiles have separate country scopes. Local login accepts direct localhost access only, including when used with live Tableau for a trusted single-user test.

For a stable local server: `powershell -File deployment/start.ps1`. For line debugging, open **this folder** in VS Code, select the `.venv` interpreter, place breakpoints and start **HKELI local Flask debug**. The launch configuration uses Flask as a module, avoiding relative-import errors. Do not use the debugger for shared deployments.

Mac: `python3.11 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.lock`, copy the example configuration, then `bash deployment/start-mac.sh`.

## What is implemented

- Versioned typed skill registry and native Python DAG; schema/permission checks, dependency cycle checks, task timeouts, bounded retries, cancellation, per-application task slots and separate Tableau/Stork limits.
- Persistent SQLite job metadata, owner checks, progress trace, expiry and restart interruption. Single application instance; active tasks are not replayed after a restart.
- Independent native Tableau display and data intelligence skills. Exact discovered IDs, published defaults, reviewed native filters/parameters and worksheet mark selection; separate REST export with matching native filters. Tabs hidden in Embedding v3.
- Full received CSV analysis in DuckDB: checked column identifiers, typed filters, approved sums/calendar grouping, snapshot/null/currency guards and bounded output. CSV files exist only in an operation's temporary directory.
- Evidence records, numerical grounding checks, derived lineage, explicit LIVE/MOCK separation and source disclosures. Optional Stork narration failure preserves valid data and charts.
- Twelve synthetic business tables plus fixture metadata, nine scenario workflows, indicative mock pricing, fourteen-section executive draft, and DOCX/PPTX/PDF/XLSX generation with evidence manifests and owner/TTL/integrity checks.
- Browser chat, task progress, cancellation, evidence inspector, original Tableau embeds, result tables and compact bar previews.
- Repeatable 54-scenario offline benchmark, independent Python expectations, benchmark XLSX and management PPTX/PDF. See [verification](docs/VERIFICATION.md) for measured scope and pending checks.

## Enable live integrations

Read [live setup](docs/LIVE_SETUP.md) before switching `app.mode` to `live`. Install your company's **private** `ada_genai` distribution through its approved package source. No public package name or authentication contract is assumed. The integration uses `from ada_genai.google_genai import VertexClient` and the supplied asynchronous `generate_content(model=..., content=...)` contract. The configured model identifier is from your specification and must be verified with your environment.

Live mode uses Stork planning; it does not fall back to fixture routing on an outage. Business SQLite and mock pricing remain explicitly MOCK and require their own permissions. Live SPE pricing deliberately reports unavailable until the actual bank contract is supplied.

## Validate

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe benchmarks/run.py
```

Outputs: `var/benchmarks/results.json`, `benchmark.xlsx`, `management.pptx`, `management.pdf`. These are generated synthetic artifacts, excluded from Git. Live Stork semantic interpretation, authenticated browser rendering, actual Tableau exports, SSO, live SPE and OpenShift operation require environment verification. Benchmark paraphrases retain scenario codes in fixture mode and therefore do **not** measure language understanding.

See [architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [security](docs/SECURITY.md), [milestones](docs/MILESTONES.md), and the preserved [build specification](docs/BUILD_SPECIFICATION.md).

Shared business context, glossary and acronym authoring now works independently of Tableau. Edit the four files in `knowledge/mock-ui/domain/`; see [shared knowledge](docs/SHARED_KNOWLEDGE.md) for the prompt flow, reference provenance and bounded retrieval rules.

Live planning now supports multiple domains, richer skill guidance and structurally checked requirement coverage. See [planning](docs/PLANNING.md) for exact parameter/source bindings, unresolved requirements, compatibility and the limits of semantic validation. General missing-pricing-input clarification remains deferred.

Saved chats and document-format clarification are implemented. Ask “prepare a report from that”, then select DOCX/PPTX/PDF/XLSX; the draft reuses authorized saved evidence without rerunning the analysis. Document generation is consolidated into one final builder. See [chat sessions and documents](docs/CHAT_DOCUMENTS.md) for history, format precedence, provenance, access checks and retention limits.
