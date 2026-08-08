# Resume Material

## Project Title
**Invoice AI — Intelligent Invoice Processing & Analytics Platform**

## One-Line Summary
An automated pipeline that turns inbound vendor invoice emails into validated, fraud-screened, analytics-ready records using OCR, an LLM extraction service, a deterministic business-rule engine, and AI risk scoring — with zero manual data entry.

## Technology Stack
Python, FastAPI, n8n, OpenAI (Responses API, structured JSON output), pdfplumber, pdf2image, pytesseract, Pydantic, PostgreSQL (Supabase), Power BI, Railway.

## Resume Bullet Points

- Designed and built an end-to-end invoice automation platform (email → OCR → LLM extraction → validation → fraud risk scoring → database → BI dashboards) processing PDFs and scanned images with zero manual entry.
- Built a modular FastAPI backend with strict separation of concerns across five layers (document processing, AI extraction, deterministic validation, AI risk analysis, analytics), each independently testable and swappable.
- Implemented a hybrid document-processing engine that routes digital PDFs to direct text extraction and only falls back to OCR (pdf2image + pytesseract) when needed, cutting unnecessary OCR calls and processing time.
- Engineered a structured AI extraction service on the OpenAI Responses API returning per-field confidence scores, validated against a strict Pydantic schema with automatic retry on malformed output.
- Built a deterministic rule engine (field validation, GST format checks, total-consistency checks, three-way duplicate detection by invoice number/file hash/vendor+amount+date) that gates all AI risk analysis calls, cutting AI spend on invalid invoices to zero.
- Designed a server-side analytics layer (PostgreSQL views + a parameterized trend function) exposed through a REST API and consumed directly by Power BI, keeping all aggregation logic out of the dashboard layer.
- Automated the entire intake workflow in n8n (Gmail trigger, subject/attachment filtering, per-attachment processing, retry-with-backoff, success/failure branching) requiring zero manual monitoring.

## Interview Explanation (60–90 seconds)

"I built an invoice processing platform that automates a task finance teams usually do by hand: reading vendor invoices and getting the data into a system. When an invoice email arrives, n8n picks it up automatically, filters for the right kind of email, and sends the attachment to a FastAPI backend I built.

The backend has a few distinct stages. First, a document processing engine — it tries to extract text directly from the PDF, and only falls back to OCR if the PDF is actually a scanned image, so I'm not wasting time or compute on documents that don't need it. That clean text goes to an AI extraction service that calls OpenAI's structured output API and returns a typed JSON object — vendor, amounts, line items, everything — each field with a confidence score, validated against a strict schema.

Here's the part I think is the most interesting design decision: before any AI opinion on risk or fraud, the invoice goes through a deterministic Python rule engine — missing fields, bad totals, duplicate invoices by number, file hash, or vendor-and-amount match. Only if it passes those checks does it go to a second AI call for contextual risk reasoning — things like unusual payment terms or vendor inconsistencies that a rule can't easily catch. That ordering matters both for cost — I'm not spending AI tokens on invoices that are already invalid — and for trust, because the parts that should be deterministic actually are.

Everything gets stored in Postgres, and I built a reporting layer as SQL views so Power BI never touches business logic directly — it just reads pre-aggregated data. The whole thing is deployed on Railway with optional API-key auth, upload limits, and logging that never touches sensitive invoice content."

## Metrics to Personalize Before Sharing

Swap in real numbers once you've run this against actual invoices, e.g.: "processed N invoices," "reduced manual entry time by X%," "flagged N duplicate/high-risk invoices automatically." Placeholder numbers were intentionally not fabricated here.
