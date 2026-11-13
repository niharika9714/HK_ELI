# Reuse the working older application's connection setup

The COMPLETE application now supports the older project's Stork environment-name fields and trusted adapter path. The older application is unchanged. No secrets or local connection values were copied.

Update **COMPLETE/config/config.local.toml**, keeping its existing sections and runtime limits:

```toml
[stork]
one_bank_id_env = "One_Bank_ID"
one_bank_password_env = "One_BANK_PASSWORD"
ssl_cert_file_env = "SSL_CERT_FILE"
adapter = "app.integrations.vertex_adapter:generate"
model = "YOUR-COMPANY-ENABLED-MODEL"
timeout_seconds = 30
concurrency = 2
max_prompt_characters = 120000
max_model_calls = 12
```

The named environment variables are checked before SDK construction. SSL_CERT_FILE must point to an existing certificate file. The SDK still reads its own process environment; no guessed constructor/authentication parameters were introduced. If you customize environment-variable names, ensure the bank SDK is actually configured to read those names; the application does not alias them into SDK-specific environment names.

The default adapter retains the supplied async `VertexClient().aio.models.generate_content(model=..., content=...)` contract. The legacy configured path ending in `:generate` is recognized without nesting asyncio.run. An administrator-configured alternative module:function may be synchronous or asynchronous; synchronous adapters run in a thread with a bounded await. Python cannot forcibly stop a synchronous SDK call when the await expires, so custom synchronous adapters must enforce their own network timeouts. Never point adapter at untrusted user input.

In the VS Code PowerShell terminal used to start the app:

```powershell
$env:One_Bank_ID = Read-Host 'Bank ID'
$env:One_BANK_PASSWORD = Read-Host 'Bank password'
$env:SSL_CERT_FILE = (Resolve-Path '.\SSL.pem').Path
$env:TABLEAU_CA_BUNDLE = (Resolve-Path '.\SSL.pem').Path
$env:TABLEAU_CONNECTED_USERNAME = 'YOUR-PROVISIONED-TABLEAU-USERNAME'
$env:TABLEAU_CONNECTED_SECRET_VALUE = Read-Host 'Connected App secret value'
```

Values remain in the local process environment. `.env.example` documents names, but the app does not automatically load `.env`. Company policy may require a secret manager rather than interactive entry.

Copy the non-secret Tableau server/site/API version/client ID/secret ID values into COMPLETE's `[tableau]`. Keep secret_value_env and ca_bundle_env as variable **names**, not secret values. Both projects already use Connected App HS256 JWT sign-in, verified TLS, independent embed JWTs and scoped discovery/exports. COMPLETE preserves its stricter response bounds, token checks and current filter-aware image/document behavior; the older transport is not copied over those safeguards.

For trusted local testing, `[identity].local_test_enabled = true`. A `[[users]].tableau_username` can supply the older profile-style identity when TABLEAU_CONNECTED_USERNAME is empty; a nonempty environment setting takes priority. This fallback never applies to corporate SSO. Keep explicit user permissions/resources and country/LOB/dashboard checks.

Do not overwrite the entire new config with the old one. The old `mode="demo"` becomes `mode="fixture"` for offline use or `mode="live"` for Stork calls. Old `name`/dashboard aggregate metadata do not replace the new typed identity permissions, resource scopes, knowledge catalog or verified per-view export contracts. Both versions support exact workbook-name discovery; COMPLETE additionally supports workbook content URL when the name is blank.

Run `python check_live.py --user YOUR-CONFIGURED-USER`, followed by `--tableau` and `--stork` separately in the office environment. The diagnostic now checks the configured Stork credential variables too. Browser embedding, real SDK authentication, actual model availability and office Tableau access remain unverified here.
