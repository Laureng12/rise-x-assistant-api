# Rise-X Founder Assistant Starter

This starter gives you the assets for a Custom GPT with API Actions that can read inbound messages, draft replies, save drafts, send only after approval, and create follow-up tasks.

## Files

- `gpt_instructions.md` — paste into the Custom GPT Instructions field.
- `openapi.yaml` — paste into the GPT Actions schema editor after changing the server URL.
- `app/main.py` — FastAPI backend scaffold.
- `requirements.txt` — Python dependencies.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Deploy

Deploy the FastAPI app on Render, Railway, Fly.io, AWS, GCP, or another HTTPS host.

Then update `openapi.yaml`:

```yaml
servers:
  - url: https://your-live-api-domain.com
```

## GPT Action auth

Use API key auth with a Bearer token.

Header:

```text
Authorization: Bearer YOUR_SECRET
```

## MVP actions

1. `getUnreadMessages`
2. `getMessageThread`
3. `draftResponse`
4. `saveDraft`
5. `sendApprovedResponse`
6. `createTask`

## Recommended first connected source

Start with Gmail or Outlook only. Add Slack/CRM later.
