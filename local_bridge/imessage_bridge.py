import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Rise-X Local Messages Bridge", version="1.0.0")

BRIDGE_API_KEY = os.getenv("RISE_X_LOCAL_BRIDGE_API_KEY", "replace-with-local-secret")
MESSAGES_DB = Path.home() / "Library" / "Messages" / "chat.db"


def require_auth(authorization: Optional[str]) -> None:
    if authorization != f"Bearer {BRIDGE_API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def apple_time_to_iso(value: Optional[int]) -> Optional[str]:
    if value is None:
        return None
    seconds = value / 1_000_000_000 + 978_307_200
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def copy_messages_db() -> Path:
    if not MESSAGES_DB.exists():
        raise HTTPException(status_code=404, detail="Messages database not found.")
    target = Path(tempfile.gettempdir()) / "rise_x_messages_chat.db"
    shutil.copy2(MESSAGES_DB, target)
    return target


@app.get("/health")
def health_check():
    return {"status": "ok", "source": "imessage"}


@app.get("/messages/recent")
def recent_messages(
    limit: int = 50,
    unread_only: bool = False,
    authorization: Optional[str] = Header(default=None),
):
    require_auth(authorization)
    db_path = copy_messages_db()
    query = """
        SELECT
            message.ROWID AS message_id,
            handle.id AS sender,
            message.text AS body,
            message.attributedBody AS attributed_body,
            message.date AS sent_at,
            message.is_from_me AS is_from_me,
            message.is_read AS is_read,
            message.service AS service
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.is_empty = 0
    """
    params = []
    if unread_only:
        query += " AND message.is_read = 0 AND message.is_from_me = 0"
    query += " ORDER BY message.date DESC LIMIT ?"
    params.append(max(1, min(limit, 200)))

    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Could not read Messages database: {exc}")

    return {
        "messages": [
            {
                "message_id": f"imessage_{row['message_id']}",
                "source": "imessage" if row["service"] == "iMessage" else "sms",
                "sender": row["sender"] or "unknown",
                "body": row["body"] or (
                    "[Message content is not available as plain text in the local Messages database.]"
                ),
                "has_plain_text_body": row["body"] is not None,
                "has_attributed_body": row["attributed_body"] is not None,
                "sent_at": apple_time_to_iso(row["sent_at"]),
                "is_from_me": bool(row["is_from_me"]),
                "is_read": bool(row["is_read"]),
            }
            for row in rows
        ]
    }
