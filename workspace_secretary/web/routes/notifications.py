from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import logging

from workspace_secretary.web import database as db, engine_client as engine
from workspace_secretary.web import templates, get_template_context
from workspace_secretary.web.auth import require_auth, Session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/sync/status")
async def sync_status(session: Session = Depends(require_auth)):
    """Get current sync status from the engine."""
    try:
        status = await engine.get_status()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Engine unavailable: {e}")

    try:
        folders = await engine.get_folders() if status.get("enrolled") else {}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to load folders: {e}")

    return {
        "connected": status.get("imap_connected", False),
        "running": status.get("status") == "running",
        "enrolled": status.get("enrolled", False),
        "last_sync": datetime.now().isoformat(),
        "folders": folders,
    }


# Track last check time per session (in production, use Redis or DB)
_last_check: dict[str, datetime] = {}
IGNORED_SESSION_IDS = {"test-session"}


@router.get("/api/notifications/check")
async def check_notifications(
    request: Request, session: Session = Depends(require_auth)
):
    """Check for new priority emails and upcoming calendar reminders since last check."""
    session_id = request.cookies.get("session_id", "default")
    last_check = _last_check.get(session_id)
    now = datetime.now(timezone.utc)

    # Update last check time
    _last_check[session_id] = now

    if last_check is None and session_id not in IGNORED_SESSION_IDS:
        # First check - don't flood with notifications
        return JSONResponse(
            {
                "new_emails": [],
                "calendar_reminders": [],
                "count": 0,
            }
        )

    # Get new priority emails since last check
    new_emails = db.get_new_priority_emails(since=last_check)

    # Get upcoming calendar events in the next hour for reminders
    time_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    calendar_reminders = []
    try:
        selection_state, events = db.get_user_calendar_events_with_state(
            session.user_id, time_min, time_max
        )
    except Exception as e:
        logger.error(
            "Failed to fetch calendar reminders for notifications: %s", e, exc_info=True
        )
        selection_state = {"selected_ids": ["primary"], "available_ids": []}
        events = []
        calendar_reminders = []

    for event in events:
        if event.get("calendarId") not in selection_state["selected_ids"]:
            continue

        # Parse event start time
        start = event.get("start", {})
        if isinstance(start, dict):
            start_time = start.get("dateTime") or start.get("date")
        else:
            start_time = str(start) if start else None

        if not start_time:
            continue

        # Parse event start datetime
        try:
            event_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            # Only remind about events starting within 30 minutes
            if (event_start - now).total_seconds() <= 1800:
                calendar_reminders.append(
                    {
                        "id": event.get("id"),
                        "calendarId": event.get("calendarId"),
                        "summary": event.get("summary", "Untitled Event"),
                        "start": start_time,
                        "location": event.get("location", ""),
                    }
                )
        except (ValueError, TypeError, AttributeError):
            continue

    def format_date(date_val):
        if not date_val:
            return None
        try:
            if isinstance(date_val, datetime):
                return date_val.isoformat()
            return str(date_val)
        except Exception:
            return None

    return JSONResponse(
        {
            "new_emails": [
                {
                    "uid": e["uid"],
                    "folder": e.get("folder", "INBOX"),
                    "from": e.get("from_addr", "Unknown"),
                    "subject": e.get("subject", "(no subject)"),
                    "preview": (e.get("preview") or "")[:100],
                    "date": format_date(e.get("date")),
                }
                for e in new_emails
            ],
            "calendar_reminders": calendar_reminders,
            "count": len(new_emails) + len(calendar_reminders),
        }
    )


@router.post("/api/notifications/subscribe")
async def subscribe_notifications(
    request: Request, session: Session = Depends(require_auth)
):
    """Register push notification subscription (for future PWA support)."""
    # Placeholder for Web Push API integration
    data = await request.json()
    # In production: store subscription in database
    return JSONResponse({"subscribed": True})


@router.get("/api/notifications/settings")
async def get_notification_settings(
    request: Request, session: Session = Depends(require_auth)
):
    """Get notification settings."""
    # In production: load from user preferences
    return JSONResponse(
        {
            "enabled": True,
            "sound": True,
            "priority_only": True,
            "check_interval": 30,  # seconds
        }
    )


@router.post("/api/notifications/settings")
async def update_notification_settings(
    request: Request, session: Session = Depends(require_auth)
):
    """Update notification settings."""
    data = await request.json()
    # In production: save to user preferences
    return JSONResponse({"updated": True})
