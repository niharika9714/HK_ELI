# Security and release review

Implemented controls: strict typed plan/input contracts, no model code/SQL/import execution, server-derived identity/resources, skill permissions, owner-isolated jobs and drafts, CSRF, secure-cookie option, no-store/referrer/nosniff headers, bounded bodies/rows/cells/prompts/tasks/timeouts, TLS verification, no Tableau redirects, credential-free persisted task state, scoped knowledge retrieval, parameterized queries, spreadsheet formula escaping, TTL/hash checked drafts and no automatic publication.

The local login is explicitly a direct-loopback test mechanism, not corporate authentication. It refuses forwarded requests and external hosts. Shared deployment must disable it and supply a verified SSO resolver and an external session secret. Any reverse proxy identity design needs the company's actual trust contract. The sample OpenShift manifest assumes a separately reviewed config map, secret and private SDK image; none is created with real values.

Review before release:

- Confirm identity issuer/audience/signature/expiry and entitlement mapping with the IdP owner; test revocation and owner/country/resource changes.
- Inspect Connected App scopes, allowed domains, trusted TLS roots and CSV permissions under the actual user; verify native filter/export parity and as-of metadata.
- Approve metric grain/additivity, date windows, null/snapshot policy, basket interpretation and currency handling. Synthetic definitions are not production financial policy.
- Confirm restricted PVC storage, retention, backups, expiry maintenance and audit access. Aggregate results can remain sensitive even though raw Tableau CSV is temporary.
- Install and assess the private SDK through approved internal distribution; confirm data disclosure, exact model, usage accounting and network egress. Full evidence includes bounded authorized dimensions; remote Stork access requires institutional approval.
- Browser-test embeds, mark selection, report layout, accessibility and load errors. Perform image rendering/container build/OpenShift probes with actual infrastructure.
- Run software dependency and image scanning in your approved CI, and business-score benchmark outputs. No vulnerability scan, penetration test or production approval is claimed here.

Immediate critical gates: unauthorized disclosure, fabricated material numbers, or synthetic quotes presented as live quotes block release regardless of benchmark averages. Numeric evidence validation reduces hallucination risk but does not certify arbitrary financial prose. Documents remain drafts for human review.
