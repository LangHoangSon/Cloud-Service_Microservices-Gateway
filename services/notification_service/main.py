import uuid
import json
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Notification Service", version="1.0.0")

NOTIFICATIONS_FILE = Path("notifications.json")

VALID_TYPES = {
    "order_confirmed",
    "order_shipped",
    "order_delivered",
    "order_cancelled",
}


# ── File store ────────────────────────────────────────────────────────────────
def _load() -> list:
    if not NOTIFICATIONS_FILE.exists():
        NOTIFICATIONS_FILE.write_text("[]")
    return json.loads(NOTIFICATIONS_FILE.read_text())

def _save(notifications: list):
    NOTIFICATIONS_FILE.write_text(json.dumps(notifications, indent=2, ensure_ascii=False))


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class NotificationRequest(BaseModel):
    user_id:  str
    email:    str
    type:     str
    order_id: str
    message:  str

class NotificationResponse(BaseModel):
    notification_id: str
    sent:            bool
    timestamp:       str


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    notifications = _load()
    return {
        "service": "notification",
        "status":  "ok",
        "total_sent": len(notifications),
    }


@app.post("/notifications/send", response_model=NotificationResponse)
def send_notification(body: NotificationRequest):
    if body.type not in VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid notification type. Use: {VALID_TYPES}",
        )

    nid       = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "notification_id": nid,
        "user_id":         body.user_id,
        "email":           body.email,
        "type":            body.type,
        "order_id":        body.order_id,
        "message":         body.message,
        "sent":            True,
        "timestamp":       timestamp,
    }

    # Persist to log
    notifications = _load()
    notifications.append(record)
    _save(notifications)

    # Simulate email (print to console — replace with SMTP/SendGrid in prod)
    print(f"[EMAIL] → {body.email} | {body.type} | order={body.order_id[:8]} | {body.message}")

    return NotificationResponse(notification_id=nid, sent=True, timestamp=timestamp)


@app.get("/notifications")
def list_notifications(user_id: str | None = None, limit: int = 50):
    """List notification history — useful for debugging and dashboard."""
    notifications = _load()
    if user_id:
        notifications = [n for n in notifications if n["user_id"] == user_id]
    notifications.sort(key=lambda n: n["timestamp"], reverse=True)
    return {"total": len(notifications), "notifications": notifications[:limit]}