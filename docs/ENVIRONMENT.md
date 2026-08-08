# Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in real values. Never commit `.env` (already in `.gitignore`).

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SUPABASE_URL` | yes | — | Your Supabase project URL, e.g. `https://xxxxx.supabase.co` |
| `SUPABASE_KEY` | yes | — | Supabase **service role** key (server-side only — never expose to a client) |
| `LLM_PROVIDER` | no | `ollama` | Which LLM backend to use. `ollama` runs a local model (free, no internet); `openai` calls the OpenAI API (requires credits) |
| `OLLAMA_BASE_URL` | no | `http://127.0.0.1:11434` | URL of the running Ollama daemon (only used when `LLM_PROVIDER=ollama`) |
| `OLLAMA_MODEL` | no | `llama3.2:3b` | Name of a model already pulled in Ollama, e.g. `llama3.2:3b`, `gemma3:1b` (only used when `LLM_PROVIDER=ollama`) |
| `OPENAI_API_KEY` | only when `LLM_PROVIDER=openai` | — | OpenAI API key used for extraction and risk analysis |
| `HIGH_VALUE_THRESHOLD` | no | `100000` | Grand-total amount above which the rule engine adds a "high-value" warning (currency-agnostic; set to match your typical invoice currency) |
| `RISK_SCORE_THRESHOLD` | no | `70` | Risk score (0–100) at or above which an invoice is force-flagged for manual review, even if the AI suggested approval |
| `BACKEND_API_KEY` | no | unset (auth disabled) | If set, all endpoints except `/health` require header `X-API-Key: <value>`. Recommended for any public deployment |
| `MAX_UPLOAD_SIZE_MB` | no | `15` | Maximum accepted attachment size |

## Example `.env`

```env
SUPABASE_URL=https://abcxyzcompany.supabase.co
SUPABASE_KEY=eyJhbGciOiJI...        # service role key, keep secret

# Pick one LLM provider:
LLM_PROVIDER=ollama                  # default; free, local
# OLLAMA_BASE_URL=http://127.0.0.1:11434
# OLLAMA_MODEL=llama3.2:3b

# ...or use OpenAI (requires credits):
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-proj-...

HIGH_VALUE_THRESHOLD=100000
RISK_SCORE_THRESHOLD=70
BACKEND_API_KEY=a-long-random-string
MAX_UPLOAD_SIZE_MB=15
```

## LLM provider notes

- **Ollama** is the default and is **free** — the model runs on your machine and no API credits are consumed. Make sure `ollama serve` is running (or the Ollama desktop app is open) before starting the backend. Pull models with `ollama pull llama3.2:3b`.
- **Quality vs. speed** with Ollama: small models like `gemma3:1b` are fast but lose accuracy on complex invoices; `llama3.2:3b` is a good balance. For higher accuracy, `ollama pull llama3.1:8b` and set `OLLAMA_MODEL=llama3.1:8b`.
- **OpenAI** is more reliable for production but **requires paid credits on your OpenAI account**. The structured-output mode uses strict JSON Schema, so OpenAI's responses validate cleanly against the Pydantic models.
- The two paths share the same retry loop, the same Pydantic validation, and the same `risk_engine` graceful-failure behavior — if either provider fails, the endpoint still returns `200` with `ai_error` set, and the invoice row is still created if validation passes.

## n8n environment

The workflow (`n8n/invoice-email-workflow.json`) reads two environment variables from the n8n instance itself (Settings → Variables, or your n8n Cloud environment config):

| Variable | Purpose |
|---|---|
| `BACKEND_URL` | Base URL of the deployed FastAPI backend (no trailing slash), e.g. `https://invoice-ai.up.railway.app` |
| `BACKEND_API_KEY` | Same value as the backend's `BACKEND_API_KEY`, if auth is enabled |

Gmail OAuth2 credentials are configured separately in n8n's credential store, not via environment variables.
