# Registered draft document templates

These files are wired into generation. `registry.json` lists enabled templates and per-format defaults. Each `v1/manifest.json` defines sections, layouts, limits and selection guidance; `instructions.md` supplies bounded editorial context. The model selects registered IDs and evidence, while Python enforces layout and access constraints.

| ID | Formats | State |
|---|---|---|
| executive-overview | PPTX | Internal draft, subject to required disclosures |
| business-report | DOCX, PDF | Internal draft, subject to required disclosures |
| analytical-export | XLSX | Internal draft, subject to required disclosures |
| client-briefing | PPTX, DOCX | Disabled pending external wording and client-specific evidence policy |

## Example preparation

The supplied 13-page PDF was read as a draft design reference, not an authorization grant. The nine-slide executive example explicitly labels its figures synthetic. Its 16:9 layout, Arial/red/grey design and reusable patterns informed sanitized draft shells. No sample numbers, old periods, charts or client rows are copied into generated documents. These are reference-inspired layouts, not exact replicas or officially approved branding.

The supplied maturity workbook contains one Summary sheet and five metrics, with no position-detail rows. Its values were not ingested as evidence. Analytical exports contain typed scalar evidence in Data_Evidence, plus README, Summary, Evidence, Limitations and available chart sheets. They cannot reconstruct unseen positions. Original examples remain in Downloads and were not copied into the repository.

No Word example was supplied. Its shell was created using the PDF's A4, margin and font guidance. Client shells are preparation assets only.

## Required disclosures

`disclosures.json` contains the supplied D1/D2/D6 text. D3 (ELI risk), D4 (indicative pricing), D5 (projections) and D7 (external use) remain unconfigured. D3 is required for ELI documents, so generation currently returns **Required disclosure not configured: D3**, preserving the chat analysis. Pricing figures also require D4. No compliance wording has been invented.

Once the responsible owner supplies actual wording, create `shared_template/disclosures.local.json` (gitignored):

```json
{
  "D3": {
    "approved": true,
    "version": "YOUR_OWNER_APPROVED_VERSION",
    "text": "INSERT ACTUAL OWNER-APPROVED WORDING HERE"
  }
}
```

This illustrates configuration only; the placeholder is not real disclosure text. Restart after changes. Tests inject clearly labeled synthetic wording in memory; deployment never inherits it.

## Use and maintain

After an analysis, request an executive deck, detailed Word/PDF report, or Excel export. A generic report asks for format. Explicit formats win. A deck plus Excel uses separate templates with the same evidence. API callers may pass `template_id` alongside existing request fields; it must support every requested format. Omit it for automatic per-format selection. External/client documents are blocked.

Saved-result documents retain original dates, evidence and access checks. Refresh/update requests use ordinary analytical planning. Templates do not call sources to fill missing sections. LIVE image bytes are not retained in conversation history.

Tableau presentation policy: chat stays interactive with the query's validated filters. Documents automatically export PNGs for those same view/filter descriptors, even if no export task was planned. Saved-chat follow-ups freshly export the original scopes after authorization; their new capture times are recorded and disclosed separately from saved numerical reporting dates. Browser changes after the query are not captured. Unsupported REST parameters/highlights stop document generation instead of producing an unfiltered chart. All exported images must appear in PPTX/DOCX/PDF outlines; capacity failures are explicit.

Edit versioned manifests/shells and increment their versions for reviewed changes. Keep PPTX shells free of sample slides; its layouts/theme and manifest coordinates are editable. Keep the DOCX `{{document_body}}` marker and header/footer fields. Keep XLSX's four named sheets free of example rows. Asset/instruction hashes and template versions are recorded in artifact manifests.

`build_assets.py` rebuilds the initial draft assets and base manifests/disclosures: **do not run it over customized templates**. No new runtime packages are required. Development-only PDF inspection used pypdf 7.0.1.

See [implementation, limitations and validation](../docs/DOCUMENT_TEMPLATES.md).
