from datetime import datetime, date
from typing import Optional, Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Rise-X Founder Assistant API", version="1.0.0")

API_KEY = "replace-with-real-secret"


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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/messages/unread")
def get_unread_messages(
    source: str = "all",
    limit: int = 10,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    # TODO: Replace with Gmail/Outlook/Slack/CRM connector logic.
    return {
        "messages": [
            {
                "message_id": "msg_123",
                "source": source if source != "all" else "gmail",
                "from_name": "Jane Smith",
                "from_email": "jane@example.com",
                "subject": "Following up on Rise-X",
                "body": "Hey Lauren, checking in after our call...",
                "received_at": datetime.utcnow().isoformat() + "Z",
            }
        ][:limit]
    }


@app.get("/messages/{message_id}/thread")
def get_message_thread(
    message_id: str,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    # TODO: Replace with real thread lookup from original source.
    return {
        "thread": [
            {
                "message_id": message_id,
                "source": "gmail",
                "from_name": "Jane Smith",
                "from_email": "jane@example.com",
                "subject": "Following up on Rise-X",
                "body": "Hey Lauren, checking in after our call...",
                "received_at": datetime.utcnow().isoformat() + "Z",
            }
        ]
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
