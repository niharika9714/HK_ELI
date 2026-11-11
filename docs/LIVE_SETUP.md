# Live integration setup

The example configuration runs standalone fixtures. It contains no working Tableau endpoint, view IDs, private credentials or corporate SSO implementation. Configure these locally; do not copy secrets into this document or commit `config.local.toml`.

1. Copy `config/config.example.toml` to `config/config.local.toml`. Set `[app] mode = "live"` and configure the state/knowledge paths. The app reads `HKELI_CONFIG` if set; otherwise it reads this local file. Relative paths resolve against the new application's root.
2. Set a session secret and Tableau credentials in the same PowerShell session that starts the app:

```powershell
$env:HKELI_SESSION_SECRET = '<a locally generated random value, at least 32 characters>'
$env:TABLEAU_CONNECTED_USERNAME = '<your authorized Tableau username>'
$env:TABLEAU_CONNECTED_SECRET_VALUE = '<Connected App secret VALUE>'
$env:TABLEAU_CA_BUNDLE = (Resolve-Path '.\SSL.pem').Path
```

`TABLEAU_CA_BUNDLE` may be blank for default verified roots, an absolute CA path, or PEM CA text. Do not disable TLS validation. No private key belongs in this bundle. `$PWD` means the current directory; `Resolve-Path` resolves a real certificate file before export. Install the private Stork SDK using your company's approved distribution and authentication instructions. The project does not guess a public pip package or copy SDK credentials.

3. Configure `[tableau] server`, `site`, `client_id`, `secret_id`, and REST version `3.28`. The server is a trusted HTTPS origin. Verify the Connected App REST scopes (`tableau:content:read`, `tableau:views:download`) and separate browser embedding scope (`tableau:views:embed`). Allow the web application's domain in Tableau. REST login success does not prove browser embedding access.
4. Add dashboard definitions **before any TOML table header** using inline tables, or append `[[dashboards]]` tables after the users. Remove the initial `dashboards = []` when adding array tables:

```toml
[[dashboards]]
key = "your-authorized-dashboard-key"
label = "Your dashboard label"
countries = ["HK"]
lines_of_business = ["Wealth"]
workbook_name = "EXACT PUBLISHED WORKBOOK NAME"
dashboard_view_name = "EXACT PUBLISHED DASHBOARD NAME"
worksheet_names = ["EXACT PUBLISHED WORKSHEET NAME"]
```

Add that dashboard key to the configured test user's `resources`. The service discovers the actual workbook/view IDs and URLs through REST; neither the model nor local examples invent them. Workbooks are selected by exact published name in this compatibility adapter; ambiguous names fail. Give workbooks unique names or extend the adapter to match reviewed content URLs before deployment.

5. Populate `knowledge/mock-ui/catalog.json` from reviewed metadata. Keep `views/` descriptions, `domain/` glossary, `lineage/` sources, and optional `documents/` context separate. Each view record matches `workbook_content_url` plus exact `view_name` and may reference a `source_document` such as `views/maturity-details.md`.

Example structure, deliberately without real asset identities:

```json
{
  "schema_version": "1.0",
  "concepts": [],
  "views": [{
    "record_id": "reviewed-record-id",
    "workbook_content_url": "exact-discovered-content-url",
    "view_name": "exact-published-worksheet-name",
    "purpose": "Business purpose, supported grain and terminology",
    "source_document": "views/maturity-details.md",
    "native_controls_verified": false,
    "filters": {}, "parameters": {}, "highlights": {},
    "verified_export": false,
    "data_grain": "worksheet_summary",
    "grain": "Unknown until the CSV is inspected",
    "as_of": "", "currency": "", "columns": {}
  }]
}
```

Mark controls verified only after testing exact published field names and values. Example `filters` shape is `{"Predict Result":["KO","EX"]}` **only if those names/values were actually verified**. An empty requested filter object sends published defaults. Parameters use strings; highlights use categorical value lists and represent native mark selection, not filtered financial totals. Dashboard highlight is refused because worksheet membership is not inferred.

For numerical analysis, inspect the actual export and review `verified_export`, reporting `as_of`, `currency`, optional `currency_column`, and `columns`. A numeric definition is `{"type":"number","unit":"hkd","additive":true}`; a date definition includes `date_role` of `event` or `snapshot`. Do not mark coupons/rates additive. Supported grains are dashboard aggregate, worksheet summary, mark detail, deal detail and governed records. Requesting detail from a summary requires a separately authorized detail view with `scope_equivalence_verified=true`. Dashboard CSV may represent only its first worksheet; never assert complete component coverage without review.

The `as_of` metadata is an administrator assertion, not automatic proof of export freshness. Refresh reviewed metadata with the underlying reporting cycle. The service deliberately rejects parameter-dependent CSV/image exports until equivalence is verified. Browser filters/selections do not update saved narratives or reports. Re-query to obtain a new scoped analysis.

6. Verify the Stork model identifier locally. `gemini-3.5-flash` is the supplied contract, not a claim that this model is available to your SDK/account. Structured outputs have one repair attempt, a six-call run budget and bounded prompts. SDK token totals are currently estimates labeled as such; exact usage requires the company's response contract.
7. For shared deployment, set `local_test_enabled=false`, `secure_cookie=true`, and provide `identity.resolver="your_module:resolve_identity"`. This callable receives a Flask request and returns the exact `Identity` model: id, country, line_of_business, tableau_username, groups, permissions and resources. It must independently verify the company's session/token signature, issuer, audience and expiry, then map entitlements server-side. Never trust a username header supplied directly by a browser. No corporate IdP contract was provided, so this project does not fabricate one.

Live smoke checks: session/entitlements → selected workbook discovery → original worksheet embed with tabs hidden → exact native filter → corresponding full CSV and grain/units → narration → report containing original REST PNG → permission revocation → timeout/no-data behavior. Record observed version, date and result in `VERIFICATION.md`. These checks have not been run against your bank environment.

Official integration references checked during implementation: [Tableau workbook/view REST methods](https://help.tableau.com/current/api/rest_api/en-us/REST/rest_api_ref_workbooks_and_views.htm), [Embedding configuration](https://help.tableau.com/current/api/embedding_api/en-us/docs/embedding_api_configure.html), [categorical filters](https://help.tableau.com/current/api/embedding_api/en-us/docs/embedding_api_filter.html), and [Embedding v3 migration: parameters and mark selection](https://help.tableau.com/current/api/embedding_api/en-us/docs/embedding_api_migration_guide.html).
