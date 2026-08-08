# API Reference

Base URL: your Railway deployment URL (e.g. `https://invoice-ai.up.railway.app`).

## Authentication

All endpoints except `/health` are protected by an **optional** API key. If `BACKEND_API_KEY` is set in the backend's environment, every request must include:

```
X-API-Key: <your key>
```

If `BACKEND_API_KEY` is unset, authentication is disabled (useful for local development). Missing/invalid key returns `401 Unauthorized`.

---

## `GET /health`

Liveness check.

**Response `200`**
```json
{ "status": "ok" }
```

---

## `POST /process-invoice`

Ingests one invoice attachment through the full pipeline: document processing → AI extraction → business validation → AI risk analysis → persistence. Called by the n8n workflow; can also be called directly for testing.

**Request** — `multipart/form-data`

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | yes | `.pdf`, `.png`, `.jpg`, `.jpeg` only. Max size = `MAX_UPLOAD_SIZE_MB` (default 15MB) |
| `sender` | string | yes | Sender email address |
| `subject` | string | yes | Email subject line |
| `received_at` | string | no | ISO timestamp; defaults to server time if omitted |

**Response `200`**
```json
{
  "status": "received",
  "id": "a1b2c3d4-...",
  "invoice_id": "e5f6a7b8-...",
  "filename": "INV-2291.pdf",
  "sender": "billing@acmesupplies.com",
  "subject": "Tax Invoice #INV-2291 - August",
  "received_at": "2026-08-06T09:12:00",
  "document": {
    "document_type": "pdf",
    "extraction_method": "direct",
    "page_count": 1,
    "extracted_text": "...",
    "extraction_status": "success",
    "processing_time_ms": 142,
    "warnings": []
  },
  "invoice_data": { "vendor_name": { "value": "Acme Supplies", "confidence": 0.97 }, "...": "..." },
  "risk_report": {
    "overall_status": "approved",
    "validation": { "passed": true, "violations": [], "warnings": [], "duplicate_matches": [] },
    "risk_assessment": { "risk_level": "low", "risk_score": 12, "reasoning": "...", "suggested_action": "approve", "confidence": 0.9 }
  },
  "ai_error": null
}
```

`invoice_id` is `null` if the record wasn't persisted (see `ai_error`). `risk_report` and `invoice_data` are `null` if document processing failed outright (`document.extraction_status == "failed"` and no text was extracted).

**Errors**

| Status | Cause |
|---|---|
| `400` | Unsupported file type, missing filename, or file exceeds `MAX_UPLOAD_SIZE_MB` |
| `401` | Missing/invalid `X-API-Key` (only if `BACKEND_API_KEY` is configured) |
| `422` | Missing required form fields (FastAPI validation) |
| `500` | Unhandled server error (generic message only — details are server-side logged, never leaked) |

Note: AI/risk/persistence failures do **not** raise an HTTP error — the endpoint still returns `200` with `ai_error` set, so n8n's success/failure branch should check `ai_error` in addition to the HTTP status if it needs finer-grained handling.

---

## `GET /analytics/overview`

Executive KPIs: totals, spend, success rate, risk average, and status breakdown.

**Response `200`** — `OverviewMetrics`
```json
{
  "total_invoices": 128,
  "total_spend": 482310.55,
  "avg_invoice_amount": 3768.05,
  "vendor_count": 24,
  "avg_risk_score": 18.4,
  "approved_count": 101,
  "flagged_count": 14,
  "rejected_count": 9,
  "failed_count": 4,
  "validation_failure_count": 9,
  "manual_review_count": 14,
  "duplicate_invoice_count": 3,
  "avg_processing_time_ms": 1240.5,
  "processing_success_rate": 78.91
}
```

---

## `GET /analytics/vendors`

Per-vendor spend and risk breakdown, sorted by total spend descending.

**Query params**: `limit` (int, 1–50, default 10)

**Response `200`** — array of `VendorMetric`
```json
[
  { "vendor": "Acme Supplies", "invoice_count": 12, "total_spend": 45210.0,
    "avg_invoice_size": 3767.5, "avg_risk_score": 14.2, "high_risk_invoices": 1 }
]
```

---

## `GET /analytics/risk`

Risk distribution, percentage breakdown, and most common rule violations.

**Response `200`** — `RiskMetrics`
```json
{
  "distribution": [{ "risk_bucket": "low", "invoice_count": 90 }],
  "avg_risk_score": 18.4,
  "low_risk_pct": 70.31,
  "medium_risk_pct": 21.09,
  "high_risk_pct": 8.6,
  "top_violations": [{ "violation": "missing_purchase_order", "occurrences": 6 }]
}
```

---

## `GET /analytics/trends`

Spend/invoice-count/tax/discount over time.

**Query params**: `granularity` (`day` | `week` | `month` | `quarter` | `year`, default `month`)

**Response `200`** — array of `TrendPoint`
```json
[{ "period": "2026-07-01", "invoice_count": 22, "total_spend": 88210.5, "total_tax": 6210.0, "total_discount": 400.0 }]
```

**Errors**: `400` for an invalid `granularity` value.

---

## `GET /analytics/financial`

Currency distribution + trend series in one response (for the Financial Trends dashboard page).

**Query params**: `granularity` (same as `/analytics/trends`)

**Response `200`** — `FinancialMetrics`
```json
{
  "currency_distribution": [{ "currency": "INR", "invoice_count": 90, "total_spend": 300000.0 }],
  "trends": [{ "period": "2026-07-01", "invoice_count": 22, "total_spend": 88210.5, "total_tax": 6210.0, "total_discount": 400.0 }]
}
```
