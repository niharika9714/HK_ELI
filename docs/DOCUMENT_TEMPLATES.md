# Document template integration

## Six implemented additions

1. **Registry:** `services/artifacts/templates.py` loads administrator-owned, versioned manifests, bounded instructions, assets and local disclosures. Template paths must stay inside shared_template.
2. **Selection:** explicit formats win; live planning receives a registered format-specific menu. Optional API Request.template_id takes priority. Fixture mode uses deterministic defaults, not live model interpretation. External/client requests are blocked until approved wording and client-specific evidence rules exist.
3. **Evidence-based outline:** typed DocumentPlan selects section IDs, evidence IDs and available image indices. Unknown/duplicate sections, omitted required sections, invalid evidence/images and format mismatches fail. The outline cannot introduce numerical prose, formulas or source calls. Shared business definitions reach it as reference context. Word and PDF share an outline when requested together.
4. **Renderers:** `services/artifacts/template_renderers.py` loads sanitized files, applies fixed layouts, paginates bounded content and inserts evidence/disclosures. The existing finalization service remains the only generation path.
5. **Scope and refresh:** saved-result follow-ups reuse original evidence/dates with fresh authorization. Refresh/update/new analytical requests return through ordinary source planning. Missing required sections explain the gap. Templates never grant access or create missing calculations.
6. **Validation/traceability:** owner/TTL/hash checks and download reauthorization remain. Artifact manifests include template/version, asset and instruction hashes, disclosure versions and outlines. Rendering failures preserve analysis. Failed multi-format sets are rolled back.

## Configuration

### Tableau chat versus documents

`app/services/tableau_documents.py` enforces a single view/control scope: chat renders the interactive embed; document finalization exports the original Tableau PNG using the same exact filters. Duplicate identical descriptors are exported once; distinct filtered instances remain separate. `tableau.chart.export` also returns its interactive descriptor for chat. The document builder does not depend on that skill being chosen by the model. Saved conversations retain scoped descriptors, not binary images; follow-ups reauthorize and freshly export them, with capture timestamps and a warning that saved numerical evidence is a different snapshot. No embed HTML/JWT enters a document. Requested image omissions fail outline validation. Image bytes must decode as PNG.

Existing REST export guards deliberately reject unsupported parameters/highlights; unsupported scope never falls back to defaults. Query filters are authoritative, not later browser interactions. Per-view/filter/capture metadata is retained in artifact manifests. See [Tableau Query View Image](https://help.tableau.com/current/api/rest_api/en-us/REST/rest_api_ref_workbooks_and_views.htm#query_view_image) for the export API. Numerical data is not refreshed by this image operation.

See shared_template/README.md for D3/D4 disclosure setup. D3 is intentionally missing until supplied by its owner; generation is blocked, analysis remains usable. D1/D2/D6 come from the supplied draft specification. Client briefing stays disabled even if someone merely adds D7 text; it still needs a reviewed client-scope export policy.

`config/config.example.toml` adds bounded `stork.max_model_calls = 12` to accommodate analysis plus up to four document outputs and repairs. Gateway callers without that setting retain the previous six-call default. Existing live local configuration may need the new setting. No credentials were added.

## Reference decisions and limits

The PDF is a draft design specification, not evidence of Compliance or Brand approval. Sanitized shells follow its broad style without copying sample figures or padding thin evidence to artificial minimum lengths. No official logo or Word example was supplied. The maturity example is a summary, not a position list; no values from it were persisted.

- PPTX uses manifest-controlled title/body/chart/footer geometry and the shell's dimensions/layout. It currently renders evidence lists and individual images, not every reference KPI-card, table or paired-chart design. It uses factual section titles rather than newly generated takeaway claims. Body/appendix limits refuse oversized outputs; text budgets do not replace PowerPoint visual review.
- DOCX loads the shell, replaces its body/header/footer fields and inserts sections, figures and evidence. Word updates page fields. Text input is bounded; Word/font-dependent pagination is not certified against the reference's 20-page ceiling.
- PDF uses ReportLab and the shared outline; it is not DOCX conversion or a guaranteed page-identical copy. Native PDF uses Helvetica rather than requiring Arial installation. Bookmarks and exact Word fidelity remain unimplemented.
- XLSX has real number/date cells, blank missing numeric values with Status reasons, escaped formula-like strings, visible sheets, filters and source-mode tags. Precision beyond Excel capacity is retained as labeled text. Derived values remain executed snapshots; no unapproved spreadsheet formulas are invented. Data_Evidence contains scalar findings, not unseen raw rows. Available images retain separate Chart sheets.
- `freshness_days` is null until an owner supplies a limit; configured limits add stale warnings. Null never means freshness approval. Missing metric formula/owner definitions are disclosed. Prepared-by uses the authenticated app identity. Unknown reporting periods remain unknown.
- Documents always remain DRAFT. Neither templates nor the LLM can set APPROVED. External release and current financial completeness are not claimed.

## Verification

Official APIs were checked against [python-pptx slide layouts](https://python-pptx.readthedocs.io/en/latest/user/slides.html), [python-docx existing documents](https://python-docx.readthedocs.io/en/latest/user/documents.html) and [openpyxl workbooks](https://openpyxl.readthedocs.io/en/stable/tutorial.html). Existing runtime dependencies suffice. pypdf 7.0.1 was installed only for development inspection of the PDF.

`tests/test_document_templates.py` checks disclosure blocking with retained analysis, external blocking across follow-ups, path containment, section/evidence/image checks, all four formats from saved results, Excel types/missing cells/formula escaping, sample-value exclusion and a gateway double receiving shared definitions. Test-only synthetic disclosures are never written to deployment configuration.

From the project directory:

```powershell
& '..\.venv\Scripts\python.exe' -m pytest -q
& '..\.venv\Scripts\python.exe' benchmarks/run.py
```

Live Stork template interpretation, Tableau access/image refresh, Office visual/pagination checks, official branding, Compliance text and external release remain unverified.

The benchmark CLI installs explicitly synthetic disclosure wording into its temporary in-memory registry so artifact execution can be exercised. It does not modify deployment disclosure files or constitute approval. Running the normal app without D3 continues to block documents.
