# Source-independent business knowledge

Edit these four Markdown files under the configured `app.knowledge_root` (default `knowledge/mock-ui`):

| File | Purpose |
|---|---|
| `domain/business-overview.md` | Short platform/business context, always included |
| `domain/business-conventions.md` | Short general interpretation conventions, always included |
| `domain/glossary.md` | Business terms, aliases and ambiguity notes, retrieved by question relevance |
| `domain/acronyms.md` | Acronyms, short phrases, expansions and ambiguity notes, retrieved by question relevance |

The supplied ELI/PB/KO expansions are illustrative general terminology. Confirm your organisation's usage before relying on them. Add approved context rather than guessing exact Tableau field names, entitlement mappings or payoff formulas.

One glossary/acronym entry must start with a level-two heading:

```markdown
## YOUR_TERM
Meaning: Your business-owner-reviewed definition.
Aliases: Common acronyms, synonyms and short phrases.
Context: Where this meaning applies.
Ambiguity: Other meanings or when to ask for clarification.
Owner/version: Your reviewing team and definition version.
```

Retrieval uses lexical overlap with the question, weighting headings more strongly than body text. Aliases belong in the entry body. It is a lightweight bounded retriever, not an embedding search service or a phrase whitelist for model intent. Terms with no lexical/alias overlap are not automatically retrieved. Keep related phrases in each entry and split long entries so that their qualifications remain intact.

Flow: the orchestrator selects a shared-reference snapshot before any domain classification or skill choice, including explicit-plan requests. The classifier, planner, actual-profile analytical interpretation, insight/report narration and final narrator receive that same snapshot. It requires `knowledge.read` permission but **does not require a Tableau connection, catalog.json, discovered workbook or selected dashboard**. Fixture routing remains deterministic; it does not suddenly start calling a model.

Budgets: each overview/conventions file is at most **1,600 characters**; a retrieved entry is at most **1,200 characters**, including its heading. At most **six entries** are selected. The total serialized shared context, including provenance and policy, is at most **8,000 characters**. The combined shared source text must fit `max_knowledge_characters` (default 80,000). Oversized baseline/source files fail explicitly; entries exceeding the entry/selection/prompt budget are omitted whole and `omitted_relevant_count` discloses the omission. Definitions are never cut midway through a caveat to fit a prompt.

Edits are read on the next request, with content hashes recorded for traceability; an in-flight run keeps its original snapshot. Responses expose `knowledge_references` (reference/section, heading if present, SHA-256). The UI shows these separately under Business terminology references. Reference entries never become numerical `EvidenceRecord` items or authorize new claim numbers. Existing evidence-reference, numeric and statistical-role validation remains in force.

Only put reference suitable for **all users with knowledge.read** in these four files. No client records, confidential dashboard descriptions, credentials, current balances, or source-specific entitlements belong here. Shared prose is reference data, never executable instructions or authority to grant access, approve formulas/filters, infer units/grain or invent financial figures. Numerical explanations still require executed evidence IDs, and ambiguous terms should prompt clarification.

Source-specific material stays separate: `views/` and `catalog.json` describe exact reviewed published views; `lineage/` and other scoped documents describe their sources. Shared files are excluded from source-specific retrieval to avoid injecting the same context twice. New shared reference content does not change dashboard/resource authorization, LIVE/MOCK isolation, metric contracts or published default filters.
