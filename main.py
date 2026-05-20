import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date
from typing import Optional, Literal, List

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Rise-X Founder Assistant API", version="1.0.0")

API_KEY = os.getenv("RISE_X_ASSISTANT_API_KEY") or os.getenv("ASSISTANT_API_KEY", "replace-with-real-secret")
ALLOW_MOCK_DATA = os.getenv("ALLOW_MOCK_DATA", "false").lower() == "true"
LOCAL_BRIDGE_URL = os.getenv("LOCAL_BRIDGE_URL", "").rstrip("/")
LOCAL_BRIDGE_API_KEY = os.getenv("LOCAL_BRIDGE_API_KEY", "")
CONNECTED_SOURCES = {
    source.strip().lower()
    for source in os.getenv("CONNECTED_SOURCES", "").split(",")
    if source.strip()
}
VALID_SOURCES = {"gmail", "outlook", "slack", "sms", "imessage", "crm", "helpdesk"}


def require_auth(authorization: Optional[str]) -> None:
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


class DraftRequest(BaseModel):
    message_id: str
    response_goal: str
    tone: Optional[Literal[
        "concise", "warm", "executive", "friendly", "firm", "apologetic", "sales", "support"
    ]] = "executive"
    include_context: bool = True


class SaveDraftRequest(BaseModel):
    message_id: str
    subject: Optional[str] = None
    body: str


class SendApprovedRequest(BaseModel):
    draft_id: str
    approval_confirmation: str


class CreateTaskRequest(BaseModel):
    title: str
    owner: str = "Lauren"
    due_date: Optional[date] = None
    priority: Literal["low", "medium", "high"] = "medium"
    notes: Optional[str] = None
    source_message_id: Optional[str] = None


class TriageRequest(BaseModel):
    sources: List[Literal["gmail", "outlook", "slack", "sms", "imessage", "crm", "helpdesk", "pasted"]] = [
        "gmail",
        "outlook",
        "sms",
    ]
    limit: int = 50
    pasted_content: Optional[str] = None
    include_draft_replies: bool = True
    include_cleanup_recommendations: bool = True


class MessageBulkActionPlanRequest(BaseModel):
    message_ids: List[str]
    requested_action: Literal["archive", "delete", "mark_spam", "unsubscribe", "create_followups"]
    rationale: Optional[str] = None


class ExecuteApprovedMessageActionsRequest(BaseModel):
    action_plan_id: str
    approval_confirmation: str


class CalendarPlanRequest(BaseModel):
    date_range: Optional[str] = None
    goal: Optional[str] = None
    constraints: Optional[str] = None
    pasted_calendar: Optional[str] = None


class TravelPlanRequest(BaseModel):
    origin: Optional[str] = None
    destination: str
    dates_or_window: str
    purpose: Optional[str] = None
    budget: Optional[str] = None
    preferences: Optional[str] = None
    constraints: Optional[str] = None


def require_connected_source(source: str) -> list[str]:
    requested = VALID_SOURCES if source == "all" else {source}
    connected = sorted(requested & CONNECTED_SOURCES)
    if connected:
        return connected
    if ALLOW_MOCK_DATA:
        return ["gmail"]
    raise HTTPException(
        status_code=409,
        detail=(
            "No requested communication source is connected. Connect a source "
            "or provide the messages directly before asking the assistant to triage them."
        ),
    )


def fetch_local_bridge_messages(limit: int = 50, unread_only: bool = False) -> list[dict]:
    if not LOCAL_BRIDGE_URL or not LOCAL_BRIDGE_API_KEY:
        raise HTTPException(
            status_code=409,
            detail="Local Messages bridge is not configured. Set LOCAL_BRIDGE_URL and LOCAL_BRIDGE_API_KEY.",
        )

    query = urllib.parse.urlencode(
        {"limit": max(1, min(limit, 200)), "unread_only": str(unread_only).lower()}
    )
    request = urllib.request.Request(
        f"{LOCAL_BRIDGE_URL}/messages/recent?{query}",
        headers={"Authorization": f"Bearer {LOCAL_BRIDGE_API_KEY}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            import json

            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("messages", [])
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=exc.code, detail="Local Messages bridge rejected the request.")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Local Messages bridge is unreachable: {exc.reason}")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/sources/status")
def get_source_status(authorization: Optional[str] = Header(default=None)):
    require_auth(authorization)
    sources = []
    for source in sorted(VALID_SOURCES):
        sources.append({"source": source, "connected": source in CONNECTED_SOURCES})
    return {"sources": sources}


@app.get("/messages/unread")
def get_unread_messages(
    source: str = "all",
    limit: int = 10,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    connected_sources = require_connected_source(source)
    if any(item in connected_sources for item in ["sms", "imessage"]):
        return {"messages": fetch_local_bridge_messages(limit=limit, unread_only=True)}

    # TODO: Replace with Gmail/Outlook/Slack/CRM connector logic.
    return {
        "messages": [
            {
                "message_id": "msg_123",
                "source": connected_sources[0],
                "from_name": "Jane Smith",
                "from_email": "jane@example.com",
                "subject": "Following up on Rise-X",
                "body": "Hey Lauren, checking in after our call...",
                "received_at": datetime.utcnow().isoformat() + "Z",
            }
        ][:limit]
    }


@app.post("/communications/triage")
def triage_communications(
    request: TriageRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    requested_sources = {source for source in request.sources if source != "pasted"}
    has_connected_source = bool(requested_sources & CONNECTED_SOURCES)
    has_pasted_content = bool(request.pasted_content and request.pasted_content.strip())
    if not has_connected_source and not has_pasted_content and not ALLOW_MOCK_DATA:
        raise HTTPException(
            status_code=409,
            detail=(
                "No requested communication source is connected and no pasted content was provided."
            ),
        )

    # TODO: Replace this planning scaffold with Gmail/Outlook/SMS/Slack provider logic.
    source = sorted(requested_sources & CONNECTED_SOURCES)[0] if has_connected_source else "pasted"
    if source in {"sms", "imessage"}:
        messages = fetch_local_bridge_messages(limit=request.limit, unread_only=False)
        return {
            "items": [
                {
                    "message_id": message["message_id"],
                    "source": message["source"],
                    "sender": message["sender"],
                    "subject": "Text message",
                    "bucket": "needs_review" if not message.get("is_from_me") else "archive",
                    "priority": "medium" if not message.get("is_from_me") else "low",
                    "summary": message["body"][:240],
                    "recommended_action": "Review and draft a response if needed.",
                    "draft_response": None,
                    "risk_level": "medium",
                }
                for message in messages
            ],
            "follow_ups": [],
            "cleanup_recommendations": [],
            "needs_user_approval": True,
        }

    return {
        "items": [
            {
                "message_id": "provided_1" if source == "pasted" else "msg_123",
                "source": source,
                "sender": "Unknown sender" if source == "pasted" else "Jane Smith",
                "subject": "Provided communication" if source == "pasted" else "Following up on Rise-X",
                "bucket": "needs_reply",
                "priority": "medium",
                "summary": "Needs review and a concise response.",
                "recommended_action": "Review draft response, then approve sending if accurate.",
                "draft_response": (
                    "Thanks for the follow-up. I’m reviewing this and will come back with "
                    "a clear next step shortly."
                )
                if request.include_draft_replies
                else None,
                "risk_level": "low",
            }
        ],
        "follow_ups": [
            {
                "title": "Follow up on reviewed communication",
                "owner": "Lauren",
                "due_date": None,
                "priority": "medium",
                "source_message_id": "provided_1" if source == "pasted" else "msg_123",
                "notes": "Confirm the response direction before sending.",
            }
        ],
        "cleanup_recommendations": []
        if not request.include_cleanup_recommendations
        else ["Review low-value newsletters and receipts for archive/delete approval."],
        "needs_user_approval": True,
    }


@app.post("/messages/bulk-action-plan")
def plan_message_bulk_actions(
    request: MessageBulkActionPlanRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    return {
        "action_plan_id": "action_plan_123",
        "requested_action": request.requested_action,
        "item_count": len(request.message_ids),
        "rationale": request.rationale or "User-requested message cleanup action.",
        "requires_approval": True,
    }


@app.post("/messages/execute-approved-actions")
def execute_approved_message_actions(
    request: ExecuteApprovedMessageActionsRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    approval = request.approval_confirmation.strip().lower()
    allowed = {
        "approved",
        "approve",
        "yes",
        "yes approved",
        "yes, approved",
        "yes execute",
        "yes, execute",
        "approved, execute",
    }
    if approval not in allowed:
        raise HTTPException(status_code=400, detail="Explicit approval required.")
    # TODO: Execute provider-specific Gmail/Outlook/SMS cleanup actions.
    return {"status": "executed", "executed_count": 0}


@app.get("/messages/{message_id}/thread")
def get_message_thread(
    message_id: str,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    if not CONNECTED_SOURCES and not ALLOW_MOCK_DATA:
        raise HTTPException(
            status_code=409,
            detail="No communication source is connected for thread lookup.",
        )
    # TODO: Replace with real thread lookup from original source.
    return {
        "thread": [
            {
                "message_id": message_id,
                "source": sorted(CONNECTED_SOURCES)[0] if CONNECTED_SOURCES else "gmail",
                "from_name": "Jane Smith",
                "from_email": "jane@example.com",
                "subject": "Following up on Rise-X",
                "body": "Hey Lauren, checking in after our call...",
                "received_at": datetime.utcnow().isoformat() + "Z",
            }
        ]
    }


@app.post("/calendar/plan")
def plan_calendar(
    request: CalendarPlanRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    # TODO: Replace with Google/Microsoft Calendar lookup and planning logic.
    return {
        "summary": "Calendar planning scaffold. Connect a calendar source or provide pasted calendar details for a real plan.",
        "conflicts": [],
        "proposed_changes": [
            "Add buffers around high-priority meetings.",
            "Hold time for follow-ups and preparation.",
        ],
        "follow_ups": [],
        "requires_approval": True,
    }


@app.post("/travel/plan")
def plan_travel(
    request: TravelPlanRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    return {
        "summary": f"Travel planning options for {request.destination} during {request.dates_or_window}.",
        "options": [
            "Confirm exact meeting locations and preferred arrival/departure windows.",
            "Compare flight and lodging options after travel data/provider access is connected.",
        ],
        "constraints": [
            constraint
            for constraint in [request.budget, request.preferences, request.constraints]
            if constraint
        ],
        "estimated_budget": request.budget or "Budget not provided.",
        "risks": ["No booking should be made until the user approves the final itinerary."],
        "next_actions": ["Confirm origin, destination, exact dates, budget, and lodging preferences."],
    }


@app.post("/responses/draft")
def draft_response(
    request: DraftRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    # Option A: Let the Custom GPT draft after reading the thread.
    # Option B: Call OpenAI here server-side and return the generated draft.
    return {
        "message_id": request.message_id,
        "draft_subject": "Re: Following up on Rise-X",
        "draft_body": (
            "Jane — thanks for the follow-up. I enjoyed the conversation as well. "
            "The best next step is to align on the specific workflow you want Rise-X "
            "to support first, then we can map that into a short pilot."
        ),
        "reasoning_summary": "Concise founder-style reply with a clear next step.",
        "needs_approval": True,
        "risk_level": "low",
    }


@app.post("/responses/save-draft")
def save_draft(
    request: SaveDraftRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    # TODO: Save draft back to Gmail/Outlook/Slack/CRM/helpdesk.
    return {"draft_id": "draft_456", "status": "saved"}


@app.post("/responses/send-approved")
def send_approved_response(
    request: SendApprovedRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    approval = request.approval_confirmation.strip().lower()
    allowed = {"approved", "send it", "yes send", "yes, send it", "approved, send it"}
    if approval not in allowed:
        raise HTTPException(status_code=400, detail="Explicit approval required.")
    # TODO: Send through the original provider.
    return {"sent_message_id": "sent_789", "status": "sent"}


@app.post("/tasks")
def create_task(
    request: CreateTaskRequest,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    # TODO: Save to Notion/Todoist/Linear/Asana/DB.
    return {
        "task_id": "task_123",
        "status": "created",
        "title": request.title,
        "owner": request.owner,
        "due_date": str(request.due_date) if request.due_date else None,
        "priority": request.priority,
    }
