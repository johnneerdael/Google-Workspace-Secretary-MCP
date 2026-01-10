"""
Thread view routes - conversation display.
"""

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
from datetime import datetime
import html
import re

from workspace_secretary.web.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def format_datetime(date_val) -> str:
    """Format datetime for thread view."""
    if not date_val:
        return ""

    if isinstance(date_val, str):
        try:
            date_val = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return date_val

    if isinstance(date_val, datetime):
        return date_val.strftime("%b %d, %Y at %I:%M %p")

    return str(date_val)


def extract_name(addr: str) -> str:
    """Extract display name from email address."""
    if not addr:
        return ""
    if "<" in addr:
        return addr.split("<")[0].strip().strip('"')
    return addr.split("@")[0]


def sanitize_html(html_content: str) -> str:
    """Basic HTML sanitization - remove scripts and dangerous elements."""
    if not html_content:
        return ""
    html_content = re.sub(
        r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE
    )
    html_content = re.sub(
        r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL | re.IGNORECASE
    )
    html_content = re.sub(
        r"\son\w+\s*=", " data-removed=", html_content, flags=re.IGNORECASE
    )
    return html_content


def text_to_html(text: str) -> str:
    """Convert plain text to simple HTML."""
    if not text:
        return ""
    text = html.escape(text)
    text = text.replace("\n\n", "</p><p>")
    text = text.replace("\n", "<br>")
    return f"<p>{text}</p>"


@router.get("/thread/{folder}/{uid}", response_class=HTMLResponse)
async def thread_view(
    request: Request,
    folder: str,
    uid: int,
):
    """Display email thread/conversation."""
    db = get_db()

    email = db.get_email_by_uid(uid, folder)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    thread_emails = db.get_thread_emails(uid, folder)

    if not thread_emails:
        thread_emails = [email]

    messages = []
    for e in thread_emails:
        body_html = e.get("body_html", "")
        body_text = e.get("body_text", "")

        if body_html:
            content = sanitize_html(body_html)
        else:
            content = text_to_html(body_text)

        messages.append(
            {
                "uid": e["uid"],
                "folder": e["folder"],
                "from_name": extract_name(e.get("from_addr", "")),
                "from_addr": e.get("from_addr", ""),
                "to_addr": e.get("to_addr", ""),
                "cc_addr": e.get("cc_addr", ""),
                "subject": e.get("subject", "(no subject)"),
                "date": format_datetime(e.get("date")),
                "content": content,
                "is_unread": e.get("is_unread", False),
                "has_attachments": e.get("has_attachments", False),
                "attachment_filenames": e.get("attachment_filenames", []),
            }
        )

    subject = email.get("subject", "(no subject)")

    return templates.TemplateResponse(
        "thread.html",
        {
            "request": request,
            "subject": subject,
            "messages": messages,
            "folder": folder,
            "uid": uid,
        },
    )
