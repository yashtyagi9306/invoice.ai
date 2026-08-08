# n8n Email Ingestion Setup

End-to-end setup for forwarding invoice emails to the FastAPI backend via n8n.

## What This Does

```
Gmail inbox (yashtyagi3333@gmail.com)
    ↓ n8n polls every minute
n8n workflow filters subjects + extracts attachments
    ↓ POSTs each PDF
FastAPI backend on localhost:8000
    ↓ AI extraction + rule engine
Supabase (invoices table)
```

The workflow file is at `n8n/invoice-email-workflow.json` and is ready to import.

---

## Prerequisites

- An n8n Cloud account (<https://n8n.io/cloud>)
- A Google Cloud project (you already have one) with the **Gmail API enabled**
- The FastAPI backend running locally (or deployed — see "Reaching your backend" below)

---

## Step 1 — Enable the Gmail API in your Cloud project

This is already done in your project.

Verify at <https://console.cloud.google.com/apis/library> → search "Gmail API" → ensure it shows "API enabled".

---

## Step 2 — Configure the OAuth consent screen

You have two options for the Gmail account that n8n will monitor.

### Option A: Monitor `yashtyagi3333@gmail.com` (the project owner — recommended for your setup)

Since this account owns the Cloud project, it is **automatically a test user** in the OAuth consent screen. No extra step needed.

When you click "Connect my account" in n8n, sign in to `yashtyagi3333@gmail.com` and grant the `gmail.readonly` permission.

### Option B: Monitor a different Gmail account

If you want n8n to read a different mailbox:

1. Go to **APIs & Services** → **OAuth consent screen** in the Cloud project
2. Scroll to **Test users** → click **+ Add users**
3. Add the email address that owns the mailbox
4. Save

Only the addresses in this list can authorize your app while the consent screen is in **Testing** mode (the default).

---

## Step 3 — Create an OAuth Client ID

1. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
2. Application type: **Web application**
3. Name: anything (e.g. "n8n Invoice")
4. **Authorized redirect URIs**: add your n8n Cloud callback URL — it's the URL of your n8n instance plus `/rest/oauth2-credential/callback`. Example: `https://your-name.n8n.cloud/rest/oauth2-credential/callback`
5. Click **Create**
6. **Copy the Client ID and Client Secret** — you'll paste them in n8n

---

## Step 4 — Set up the credential in n8n Cloud

1. In n8n, left sidebar → **Credentials** → **New**
2. Type: search "Gmail OAuth2" → select it
3. Fill in:
   - **Client ID**: from Step 3
   - **Client Secret**: from Step 3
4. Click **Connect my account** (or **Sign in with Google**)
5. Sign in to the Gmail account you want to monitor (in your case `yashtyagi3333@gmail.com`)
6. Approve the `gmail.readonly` permission
7. Save the credential with the name **"Invoice Mailbox"** (the workflow references this name)

---

## Step 5 — Import the workflow

1. In n8n, top-right menu (three dots) → **Import from File** → **Import File from Local**
2. Select `C:\Users\yashu\Downloads\invoice-ai-v1.0.0\n8n\invoice-email-workflow.json`
3. The workflow appears on the canvas
4. Open the **Gmail Trigger** node → select your **"Invoice Mailbox"** credential
5. (Optional) Open the **Filter: Subject + Attachment** node to adjust the subject regex

---

## Step 6 — Reaching your backend from n8n Cloud

**This is the tricky part.** n8n Cloud runs on n8n's servers, not your laptop. It cannot reach `http://127.0.0.1:8000` directly.

You need to make your local backend reachable from the public internet. Pick one:

### Option 1: ngrok (easiest for testing)

1. Sign up at <https://ngrok.com> (free tier is fine)
2. Install: <https://dashboard.ngrok.com/get-started/setup>
3. Run:
   ```bash
   ngrok http 8000
   ```
4. ngrok prints a forwarding URL like `https://abc123.ngrok-free.app`
5. In n8n, **Settings** → **Variables**:
   - `BACKEND_URL` = `https://abc123.ngrok-free.app`
   - `BACKEND_API_KEY` = *(only if you set one in `backend\.env`)*

The free ngrok URL changes every time you restart ngrok. For long-running setups, either keep ngrok running, or use a paid ngrok plan with a reserved domain.

### Option 2: Deploy the backend publicly

See `docs/DEPLOYMENT.md` for Railway / Render / Fly.io instructions. Once deployed, the backend has a stable public URL. Set `BACKEND_URL` to that URL in n8n.

### Option 3: Self-host n8n instead

If you install n8n locally with `npm install n8n -g && n8n start`, it runs on your laptop and can reach `localhost:8000` directly. Then:

- `BACKEND_URL` = `http://127.0.0.1:8000`
- No tunnel needed

The downside is you must keep both processes (backend and n8n) running on your machine.

---

## Step 7 — Activate and test

1. In the workflow, toggle the top-right switch from **Inactive** to **Active**
2. Send a test email **to `yashtyagi3333@gmail.com`** with:
   - Subject: `Invoice INV-2026-TEST`
   - Attachment: any PDF invoice (e.g. `sample-invoice.pdf`)
3. In n8n, open the **Executions** tab — you should see a successful run within ~1 minute
4. Check your Supabase `invoices` table — the new row should appear
5. Hit `http://127.0.0.1:8000/analytics/overview` to confirm `total_invoices` increased

---

## Important Quirks

### Token expiry (Testing mode)

When the OAuth consent screen is in **Testing** mode, Google access tokens expire after **7 days**. After that, n8n will fail to fetch new emails. To fix:

- Re-open the Gmail credential in n8n → click **Reconnect** → grant permission again

For long-term use, publish the app (requires Google's verification review) or migrate to a paid Google Workspace setup with domain-wide delegation.

### Test user limit

Testing-mode projects allow up to **100 test users**. For personal use, this is plenty.

### Polling interval

The default workflow polls every minute. To make it faster, edit the **Gmail Trigger** node → **Poll Times** → set to "every 30 seconds" or similar. Be aware: very frequent polling may hit Google's API rate limits.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Redirect URI mismatch" when connecting Gmail | The callback URL in Google Cloud doesn't match your n8n instance URL. Add the exact n8n callback URL to the OAuth client's authorized redirect URIs |
| n8n gets `401` from the backend | `BACKEND_API_KEY` is set on the backend but missing or wrong in n8n |
| n8n gets `connection refused` or timeout | `BACKEND_URL` is unreachable from n8n Cloud — you need ngrok or a deployed backend |
| Workflow runs but no rows in Supabase | The PDF didn't match the subject filter, or extraction failed; check the **Executions** tab for the backend response |
| Google says "App is being tested" warning | Normal for Testing-mode apps; click "Advanced" → "Go to [app name] (unsafe)" to proceed |

---

## Verifying It's Working

After a test email:

```bash
# Check the row landed in Supabase
curl http://127.0.0.1:8000/analytics/overview
# Should show total_invoices increased by 1
```

In n8n, click on the latest execution → expand each node → confirm:
- **Gmail Trigger** fetched the email
- **Filter** passed (subject matched, attachment present)
- **Split Attachments** produced items
- **Call Backend API** returned `200` with `status: "received"` and an `invoice_id`
- **IF: Success?** routed to the success branch
