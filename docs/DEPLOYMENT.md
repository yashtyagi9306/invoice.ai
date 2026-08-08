# Deployment Guide

## Local Installation

1. **Clone & enter the backend**
   ```bash
   git clone <repo-url> && cd invoice-ai/backend
   ```
2. **Python environment**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **System dependencies for OCR** (not pip-installable)
   - `tesseract-ocr` (pytesseract needs the binary)
   - `poppler-utils` (pdf2image needs `pdftoppm`)

   macOS: `brew install tesseract poppler`
   Ubuntu/Debian: `sudo apt-get install tesseract-ocr poppler-utils`
4. **Environment variables** — copy `.env.example` to `.env` and fill in values. Full reference: [`ENVIRONMENT.md`](ENVIRONMENT.md).
5. **Supabase setup**
   - Create a project at supabase.com
   - Open the SQL editor and run `backend/database/schema.sql`, then `backend/database/analytics.sql`
   - Copy the project URL and service role key into `.env`
6. **OpenAI setup** — create an API key at platform.openai.com, add to `.env`
7. **Run locally**
   ```bash
   uvicorn main:app --reload
   ```
   Visit `http://localhost:8000/health` to confirm it's up.
8. **n8n setup**
   - Import `n8n/invoice-email-workflow.json` into n8n (Cloud or self-hosted)
   - Connect a Gmail OAuth2 credential to the Gmail Trigger node
   - Set the `BACKEND_URL` (and `BACKEND_API_KEY` if used) environment variables in n8n
   - Activate the workflow

## Railway Deployment

1. Push the repository to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo**, select this repo.
3. Set the root directory to `backend/` (or leave as-is and Railway will use the `Procfile` at the repo root, which already targets `backend.main:app`).
4. Add all variables from [`ENVIRONMENT.md`](ENVIRONMENT.md) under **Variables**.
5. Add a build step or use a custom Dockerfile if you need `tesseract-ocr` and `poppler-utils` installed on the image — Railway's default Nixpacks Python builder does not include them by default. The simplest fix is an `apt` packages file (`Aptfile` / Nixpacks `nixPkgs`) listing `tesseract` and `poppler_utils`.
6. Deploy. Railway will run the `Procfile`'s `web` process: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
7. Once live, verify:
   ```bash
   curl https://<your-app>.up.railway.app/health
   # {"status": "ok"}
   ```
8. Update `BACKEND_URL` in n8n to point at this Railway URL, and reactivate the workflow.

## Power BI Connection

1. Open Power BI Desktop → **Get Data → PostgreSQL database**.
2. Server: your Supabase project's Postgres host (found in Supabase → Project Settings → Database).
3. Database: `postgres`. Use the same credentials as your service role, or a dedicated read-only Postgres role if you prefer least-privilege.
4. Import (not DirectQuery, for simplicity) the following objects:
   - `v_analytics_overview`
   - `v_vendor_summary`
   - `v_risk_distribution`
   - `v_currency_distribution`
   - `v_rule_violation_frequency`
5. For time-series pages, add a **native SQL query**: `select * from fn_analytics_trends('month')` (swap the granularity as needed, or parameterize with a Power BI parameter).
6. Build the five dashboard pages (Executive Overview, Vendor Insights, Financial Trends, Risk Dashboard, Operational Dashboard) from these tables — no DAX business logic should be required beyond basic visuals, since all aggregation already happened in Postgres.

## Verification Checklist (post-deploy)

- [ ] `GET /health` returns `200`
- [ ] `POST /process-invoice` with a sample PDF returns `200` with a populated `invoice_data` and `risk_report`
- [ ] The invoice appears in the Supabase `invoices` table
- [ ] `GET /analytics/overview` reflects the new row (`total_invoices` incremented)
- [ ] Power BI refresh pulls the updated numbers
- [ ] Sending a real test email to the monitored mailbox triggers the full n8n → backend → DB flow end-to-end

## Deployment Troubleshooting

| Symptom | Likely cause |
|---|---|
| `500` on `/process-invoice` for every request | Missing/incorrect `SUPABASE_URL`/`SUPABASE_KEY`/`OPENAI_API_KEY` |
| OCR fallback always fails | `tesseract`/`poppler` binaries missing on the deployment image |
| n8n gets `401` from the backend | `BACKEND_API_KEY` set on the backend but not sent (or mismatched) in n8n's `BACKEND_API_KEY` variable |
| Duplicate invoices not detected | `schema.sql`/`analytics.sql` not re-run after a schema change, or `file_hash`/`rule_violations` columns missing on an older table |
| Power BI shows stale data | Using Import mode — trigger a manual refresh, or switch to DirectQuery for near-real-time |
