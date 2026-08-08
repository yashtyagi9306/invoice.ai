# Architecture

## End-to-End Flow

```
Vendor Email
    ↓
n8n Trigger (Gmail, polled every minute)
    ↓ filters: subject keyword + attachment present
Attachment Download & Split (one item per valid attachment)
    ↓
FastAPI: POST /process-invoice
    ↓
Document Processing Engine
    ├─ Digital PDF → direct text extraction (pdfplumber)
    └─ Scanned PDF / image → OCR fallback (pdf2image + pytesseract)
    ↓ normalized clean text
AI Extraction (OpenAI Responses API)
    ↓ structured JSON + per-field confidence
Business Rule Validation (deterministic, Python)
    ├─ field presence, date/amount sanity, GST format, tax-rate sanity
    └─ duplicate detection (invoice number, file hash, vendor+amount+date)
    ↓ ValidationReport
AI Risk Analysis (only runs if validation passed)
    ↓ risk level, score, reasoning, suggested action
Unified Risk Report → PostgreSQL (Supabase)
    ↓
Analytics Views (server-side aggregation)
    ↓
REST Analytics API
    ↓
Power BI Dashboard
```

## Component Responsibilities

| Component | Responsibility | Never does |
|---|---|---|
| **n8n workflow** | Trigger, filter, split attachments, call backend, retry, branch on success/failure | Parse documents, run AI, touch the database |
| **Document Processing Engine** (`services/document_processor.py`, `pdf_utils.py`, `ocr_utils.py`, `utils/text_normalizer.py`) | Convert any supported input into clean, normalized text | Know or care where the document came from downstream; never runs OCR on a digital PDF |
| **AI Service** (`ai/openai_service.py`, `ai/prompts.py`) | Sole integration point with OpenAI; structured extraction + risk reasoning | Perform OCR, PDF parsing, math validation, or database writes |
| **Rule Engine** (`services/rule_engine.py`) | Deterministic validation and duplicate detection | Use the LLM for any check it performs |
| **Risk Engine** (`services/risk_engine.py`) | Gate AI risk analysis behind rule-engine success; merge Python + AI results into one report | Replace deterministic validation with AI judgment |
| **Persistence** (`services/persistence.py`, `database/crud.py`) | Map extraction + risk output into the `invoices` table | Contain business logic |
| **Analytics Layer** (`database/analytics.sql`, `database/analytics_repo.py`, `services/analytics_service.py`) | Server-side aggregation (views + a parameterized trend function), shaped into dashboard-ready models | Expose raw invoice text or internal IDs |
| **Power BI** | Visualization only, reading from `v_*` views / `fn_analytics_trends()` | Contain any business logic |

## Design Principles Followed

- **Strict separation of concerns** — each module has exactly one job; the AI layer never touches OCR/PDF parsing, and the document processor never knows AI exists.
- **Deterministic before probabilistic** — the rule engine always runs first and can reject an invoice without ever spending an AI call.
- **Reporting is isolated from operations** — analytics reads from dedicated SQL views, not the operational `invoices` table directly, and has its own read-only data-access module (`analytics_repo.py`) separate from `crud.py`.
- **Fail safe, not silent** — every module catches its own exceptions and returns a typed failure result rather than crashing the request; nothing ever propagates a raw stack trace to the caller.

## Database Schema (summary)

Single `invoices` table (see `backend/database/schema.sql`) holding extracted fields, line items (JSONB), risk score/reasoning, rule violations (JSONB), file hash, and processing status. Duplicate detection is application-layer (not a DB constraint) so that duplicates can still be stored — marked `rejected` — for analytics and audit purposes instead of silently failing an insert.

Reporting views (`backend/database/analytics.sql`): `v_analytics_overview`, `v_vendor_summary`, `v_risk_distribution`, `v_currency_distribution`, `v_rule_violation_frequency`, and function `fn_analytics_trends(granularity)`.
