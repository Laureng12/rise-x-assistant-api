# Rise-X Founder Assistant Starter

This starter gives you the assets for a Custom GPT with API Actions that can read and triage communications, draft replies, recommend cleanup actions, manage follow-ups, plan calendar changes, and prepare travel options.

## Files

- `gpt_instructions.md` — paste into the Custom GPT Instructions field.
- `openapi.yaml` — paste into the GPT Actions schema editor after changing the server URL.
- `app/main.py` — FastAPI backend scaffold.
- `local_bridge/imessage_bridge.py` — optional Mac-only local bridge for read-only iMessage/SMS access.
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
  - url: https://your-render-service.onrender.com
```

## Render environment variables

Set these in Render before connecting the API to your Custom GPT:

```text
RISE_X_ASSISTANT_API_KEY=your-long-random-secret
CONNECTED_SOURCES=
ALLOW_MOCK_DATA=false
LOCAL_BRIDGE_URL=
LOCAL_BRIDGE_API_KEY=
```

If your Render service already uses `ASSISTANT_API_KEY`, the app accepts that as a fallback. Prefer `RISE_X_ASSISTANT_API_KEY` for clarity on new deployments.

Use `CONNECTED_SOURCES` only after real connectors are implemented and authenticated, for example:

```text
CONNECTED_SOURCES=gmail,slack
```

When the local Messages bridge is exposed through a secure tunnel, set:

```text
CONNECTED_SOURCES=gmail,imessage,sms
LOCAL_BRIDGE_URL=https://your-secure-bridge-tunnel-url
LOCAL_BRIDGE_API_KEY=your-local-bridge-key
```

Keep `ALLOW_MOCK_DATA=false` in production so the assistant does not pretend it has unread messages before real sources are connected.

## Recommended rollout

1. Gmail/Google Workspace email triage
   - OAuth connect every inbox the assistant should read.
   - Start with labels/archive/delete recommendations only.
   - Require approval before deleting, archiving, unsubscribing, or sending.

2. Google Calendar or Microsoft Calendar
   - Read events and detect conflicts first.
   - Add event creation/move/cancel only after approval rules are clear.

3. Follow-up tasks
   - Create tasks from emails/texts/calendar notes.
   - Store owner, due date, priority, source, and status.

4. Text messages
   - SMS/iMessage access depends on the source. A Render server cannot generally read personal iPhone iMessages directly.
   - Preferred option for your setup: run the Mac local bridge in `local_bridge/imessage_bridge.py`.
   - Other practical options: pasted/exported messages, Twilio/Google Voice for a managed number, or another provider with an API.

5. Travel planning
   - Start with itinerary planning and decision support.
   - Add booking integrations only after explicit approval workflows are implemented.

## GPT Action auth

Use API key auth with a Bearer token.

Header:

```text
Authorization: Bearer YOUR_SECRET
```

## MVP actions

1. `getSourceStatus`
2. `triageCommunications`
3. `getUnreadMessages`
4. `getMessageThread`
5. `planMessageBulkActions`
6. `executeApprovedMessageActions`
7. `draftResponse`
8. `saveDraft`
9. `sendApprovedResponse`
10. `createTask`
11. `planCalendar`
12. `planTravel`

## Recommended first connected source

Start with Gmail or Outlook only. Add Slack/CRM later.

## Local iMessage/SMS bridge

The local bridge is a Mac-only helper that reads your local Messages database in read-only mode and exposes recent iMessage/SMS messages to your assistant stack.

Requirements:

- Messages synced to this Mac.
- Full Disk Access granted to the terminal app or service runner that launches the bridge.
- A private bridge API key.
- A secure way for the hosted API to reach the bridge, such as Tailscale, Cloudflare Tunnel, or another HTTPS tunnel.

Run locally:

```bash
cd /Users/laurengulley/Downloads/rise_x_assistant_starter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export RISE_X_LOCAL_BRIDGE_API_KEY=your-local-long-random-secret
uvicorn local_bridge.imessage_bridge:app --host 127.0.0.1 --port 8765
```

Test locally:

```bash
curl -H "Authorization: Bearer your-local-long-random-secret" \
  "http://127.0.0.1:8765/messages/recent?limit=20&unread_only=false"
```

Security notes:

- Keep the bridge local or behind a private tunnel.
- Do not expose it publicly without authentication and HTTPS.
- The bridge should remain read-only. Delete/archive/send actions should stay behind explicit approval workflows.

After the bridge is running locally, expose it to Render through a secure HTTPS tunnel. Cloudflare Tunnel is the easiest option when the Render service needs to call back to your Mac:

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

Then copy the HTTPS tunnel URL into Render as `LOCAL_BRIDGE_URL` and set `LOCAL_BRIDGE_API_KEY` to the same key used when starting the local bridge.
