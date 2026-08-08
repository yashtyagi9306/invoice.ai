# Release Notes

## v1.0.0 — Initial Production Release

Full pipeline implemented and hardened across 9 phases:

- **Phase 1** — Project scaffolding, FastAPI skeleton, Railway readiness
- **Phase 2** — Supabase schema, connection layer, CRUD utilities
- **Phase 3** — n8n email automation (Gmail trigger → filter → split → HTTP call → retry → success/failure branch)
- **Phase 4** — Document processing engine: direct PDF extraction with OCR fallback, text normalization
- **Phase 5** — AI extraction service on the OpenAI Responses API: structured JSON, per-field confidence, single controlled retry
- **Phase 6** — Deterministic business rule engine + duplicate detection (invoice number, file hash, vendor+amount+date); AI risk analysis gated behind validation success
- **Phase 7** — Persistence layer (closing the gap flagged in Phase 6 — nothing wrote to the database before this); server-side analytics views and trend function; REST analytics API
- **Phase 8** — Full production review: fixed silently-dropped logging (root logger was never configured), added optional API-key auth, upload size limits, OCR page caps, client timeouts, a global exception handler, and wired two previously-unused config values into real safety-net behavior
- **Phase 9** — Documentation, deployment guide, resume material, final packaging

## Known Limitations

- Per-vendor trend/frequency analytics (vendor spend *over time*, as opposed to vendor totals) are not implemented — flagged during Phase 7, not built to avoid scope creep.
- No automated test suite (pytest) — this repository was reviewed manually in Phase 8; no live database/OpenAI/n8n environment was available during development to run integration tests.
- Single AI provider (OpenAI) — the AI service is isolated behind one module specifically to make swapping providers straightforward later, but no second provider is implemented.
- Notifications (threshold-based alerts) described in the original architecture were not built as a standalone feature; the corresponding config values (`HIGH_VALUE_THRESHOLD`, `RISK_SCORE_THRESHOLD`) are used internally by the rule/risk engines instead.
