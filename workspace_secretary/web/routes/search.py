"""
Search routes - keyword and semantic search.
"""

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
from datetime import datetime
import html
import os
import httpx

from workspace_secretary.web.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def format_date(date_val) -> str:
    """Format date for display."""
    if not date_val:
        return ""
    if isinstance(date_val, str):
        try:
            date_val = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return date_val[:10] if len(date_val) > 10 else date_val
    if isinstance(date_val, datetime):
        return date_val.strftime("%b %d, %Y")
    return str(date_val)


def truncate(text: str, length: int = 100) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    text = html.escape(text.strip())
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."


def extract_name(addr: str) -> str:
    """Extract display name from email address."""
    if not addr:
        return ""
    if "<" in addr:
        return addr.split("<")[0].strip().strip('"')
    return addr.split("@")[0]


async def get_embedding(text: str) -> Optional[list[float]]:
    """Get embedding from LiteLLM endpoint."""
    api_base = os.environ.get("EMBEDDINGS_API_BASE")
    api_key = os.environ.get("EMBEDDINGS_API_KEY", "")
    model = os.environ.get("EMBEDDINGS_MODEL", "text-embedding-3-small")

    if not api_base:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{api_base}/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception:
        return None


@router.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str = Query("", description="Search query"),
    mode: str = Query("keyword", description="Search mode: keyword or semantic"),
    folder: str = Query("INBOX"),
    limit: int = Query(50, ge=1, le=100),
):
    """Search emails by keyword or semantic similarity."""
    db = get_db()
    results = []

    if not q.strip():
        return templates.TemplateResponse(
            "search.html",
            {
                "request": request,
                "query": "",
                "mode": mode,
                "results": [],
                "folder": folder,
            },
        )

    if mode == "semantic" and db.supports_embeddings():
        embedding = await get_embedding(q)
        if embedding:
            results_raw = db.semantic_search(
                query_embedding=embedding,
                folder=folder,
                limit=limit,
                similarity_threshold=0.5,
            )
        else:
            results_raw = db.search_emails(
                folder=folder,
                body_contains=q,
                limit=limit,
            )
    else:
        results_raw = db.search_emails(
            folder=folder,
            body_contains=q,
            limit=limit,
        )

    for e in results_raw:
        results.append(
            {
                "uid": e["uid"],
                "folder": e.get("folder", folder),
                "from_name": extract_name(e.get("from_addr", "")),
                "subject": e.get("subject", "(no subject)"),
                "preview": truncate(e.get("body_text", ""), 150),
                "date": format_date(e.get("date")),
                "similarity": e.get("similarity"),
            }
        )

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "query": q,
            "mode": mode,
            "results": results,
            "folder": folder,
            "supports_semantic": db.supports_embeddings(),
        },
    )
