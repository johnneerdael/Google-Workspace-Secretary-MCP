"""
Web UI for Gmail Secretary - AI-powered email client.

Provides a human interface to the email system with:
- Inbox view with pagination
- Thread/conversation view
- Semantic search
- AI assistant integration (configurable LLM)
"""

from fastapi import FastAPI, Request, Depends, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from typing import Optional
import logging

from workspace_secretary.web.database import get_db, DatabaseDep

logger = logging.getLogger(__name__)

web_app = FastAPI(
    title="Secretary Web",
    description="AI-powered email client",
    docs_url="/api/docs",
    redoc_url=None,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

web_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@web_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Redirect to inbox."""
    return templates.TemplateResponse(
        "inbox.html",
        {"request": request, "emails": [], "page": 1, "has_more": False},
    )


@web_app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "secretary-web"}
