# Persistent chats and document requests

The workspace now keeps owner-scoped chat sessions in the application SQLite database. A follow-up such as “make a report from that” uses saved verified results from the selected chat. It does not automatically refresh Tableau, rerun business calculations or turn earlier synthetic values into live figures.

Example:

1. Sign in and run `Q1` (or a live authorized analytical question).
2. Ask “Prepare a report from that”. The answer retains the analysis and asks **DOCX, PPTX, PDF or XLSX?** No file is generated yet.
3. Reply “PPTX” or click its format button. The application creates the draft from the saved evidence snapshot.
4. Ask “Make DOCX and XLSX from all results in this chat” to combine saved findings without adding/joining their financial totals.

Explicit format checkboxes/API `formats` take priority. Clear natural-language requests such as Word, PowerPoint, Excel or PDF select their matching formats; presentation/slides/deck imply PPTX and spreadsheet implies XLSX. A generic report/document request never defaults to PDF, even if the model proposes PDF. Ambiguous alternatives such as “PDF or Word” ask for a choice. Only short document-format follow-ups are resumed; this is not a general missing-pricing-input clarification workflow.

`artifact.generate` now records intent and formats instead of writing files during DAG execution. The final document builder invokes the artifact service once, after evidence and narration are composed. Selecting a format in both a skill and `output.formats` therefore does not generate duplicate documents. Repeated separate user requests can intentionally create new drafts. `artifact.validate`/`publish_draft` apply only to an existing artifact ID, not an invented future ID from a deferred generation task.

Live mode uses a bounded follow-up classifier to distinguish document reuse from requests for new calculations, filters, dates or instruments. It sees at most 10,000 characters of history metadata/brief existing summaries, not raw CSV, image bytes or all prior result rows. The analytical classifier/planner also receives this bounded reference history when a new analysis is needed. Fixture mode supports deterministic common document follow-up wording; it does not claim natural-language model evaluation.

“Latest” means the latest retained result with verified evidence. “All” combines retained results in the current chat, deduplicating identical evidence/results without arithmetic. Explicit `context_turn_ids` can select owned turns within that chat. Other chats are not silently searched; select the desired saved chat first. Source questions, original run IDs, as-of dates, filters, units, LIVE/MOCK labels and evidence IDs remain recorded in document provenance. A regenerated document's timestamp does not make its underlying data current.

Original authenticated Tableau PNG/CSV bytes and embed tokens are not retained in chat history. Historical documents use saved evidence and available generated synthetic previews; they disclose that original live image bytes are not replayed. Producing a current original view/image requires a new authorized request. Browser filter changes do not revise historical saved evidence.

## API

- `POST /api/v1/conversations {}` creates an owned chat; returns `conversation_id`.
- `GET /api/v1/conversations` lists owned unexpired chats.
- `GET /api/v1/conversations/{id}` restores turns and their saved answers.
- `DELETE /api/v1/conversations/{id}` deletes its history; active requests must finish/cancel first. Previously created protected draft files keep their independent expiry.
- `POST /api/chat` or `/api/v1/requests` accepts optional `conversation_id` and `context_turn_ids`. If no ID is provided it creates a new chat, preserving compatibility with stateless clients. The queued response includes `conversation_id`, `turn_id` and `run_id`.
- A terminal job may return an answer with `status="needs_format"` and `clarification={type:"document_format",prompt,options}`. Reply in the **same conversation** with the format; do not resubmit the original analysis.
- `POST /api/v1/artifacts` also uses the same final builder for an explicit owned run; an empty format list returns format clarification rather than silently choosing PDF.

The UI stores only the selected chat ID, keyed by user, in localStorage. Questions/results remain on the server. It restores saved turns after refresh/login, supports new/switch/delete chats, and resumes polling active jobs. Authentication cookies remain separate: configure a stable `HKELI_SESSION_SECRET` for live deployment. Fixture mode's generated session key requires signing in again after an application restart, but owned saved chats still exist until expiry.

## Access and retention

Saved history, result reuse, artifact creation and artifact download recheck current ownership, permissions, resources, country and line of business. Reusing historical live evidence additionally rediscovers current Tableau access without relying on the old discovery cache. A revoked/unavailable live source prevents document reuse rather than falling back to mock data. Snapshots never grant access. Only one active turn per chat is allowed to keep context ordering deterministic.

`app.conversation_ttl_seconds` defaults to **86,400 seconds (24 hours)** from chat creation. Chats retain at most **20 turns** and **8,000,000 serialized answer characters**; each result snapshot is capped at 2,000,000 characters. Oldest turns are removed when those limits are exceeded. There are at most 20 unexpired chats per owner and 1,000 overall. Expired reads are denied immediately; startup/new-chat cleanup and `deployment/maintenance.py` remove expired history. Job/result and artifact expiry remain independent. Use one application instance, as documented for SQLite.

Saved aggregate results can contain sensitive financial/client information. Keep the state volume restricted and approve retention with the business/security owners. This feature has offline and loopback HTTP verification; actual browser interaction, corporate SSO and live Tableau/Stork behavior still require environment validation.
