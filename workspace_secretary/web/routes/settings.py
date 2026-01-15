"""Settings routes for user preferences."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from workspace_secretary.web import (
    templates,
    get_template_context,
    get_web_config,
    database as db,
)
from workspace_secretary.web.auth import require_auth, Session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])


class IdentitySettingsRequest(BaseModel):
    email: str
    full_name: str = ""
    aliases: list[str] = []


class AISettingsRequest(BaseModel):
    base_url: str = ""
    api_format: str = ""
    model: str = ""
    token_limit: int | None = None
    api_key: str = ""


class UISettingsRequest(BaseModel):
    theme: str
    density: str


class CalendarSettingsRequest(BaseModel):
    selected_calendar_ids: list[str]


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: Session = Depends(require_auth)):
    web_config = get_web_config()

    ctx = get_template_context(
        request,
        page="settings",
        web_config=web_config,
    )
    return templates.TemplateResponse("settings.html", ctx)


@router.get("/settings/vips", response_class=HTMLResponse)
async def vips_partial(request: Request, session: Session = Depends(require_auth)):
    from workspace_secretary.config import load_config

    config = load_config()
    vips = []
    if config:
        vips = getattr(config, "vip_senders", []) or []

    return templates.TemplateResponse(
        "partials/settings_vips.html",
        {"request": request, "vips": vips},
    )


@router.get("/settings/working-hours", response_class=HTMLResponse)
async def working_hours_partial(
    request: Request, session: Session = Depends(require_auth)
):
    from workspace_secretary.config import load_config

    config = load_config()
    working_hours = {
        "start": "09:00",
        "end": "18:00",
        "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "timezone": "UTC",
    }

    if config and hasattr(config, "working_hours") and config.working_hours:
        wh = config.working_hours
        working_hours["start"] = getattr(wh, "start", "09:00")
        working_hours["end"] = getattr(wh, "end", "18:00")
        working_hours["workdays"] = getattr(wh, "workdays", working_hours["workdays"])
        working_hours["timezone"] = getattr(wh, "timezone", "UTC")

    return templates.TemplateResponse(
        "partials/settings_working_hours.html",
        {"request": request, "working_hours": working_hours},
    )


@router.get("/settings/identity", response_class=HTMLResponse)
async def identity_partial(request: Request, session: Session = Depends(require_auth)):
    from workspace_secretary.config import load_config

    config = load_config()
    identity = {
        "email": "",
        "full_name": "",
        "aliases": [],
    }

    if config and config.identity:
        identity["email"] = config.identity.email or ""
        identity["full_name"] = config.identity.full_name or ""
        identity["aliases"] = config.identity.aliases or []

    return templates.TemplateResponse(
        "partials/settings_identity.html",
        {"request": request, "identity": identity},
    )


@router.get("/settings/ai", response_class=HTMLResponse)
async def ai_partial(request: Request, session: Session = Depends(require_auth)):
    web_config = get_web_config()

    ai_config = {
        "configured": False,
        "base_url": "",
        "model": "",
        "api_format": "",
    }

    if web_config and web_config.agent:
        ai_config["configured"] = bool(web_config.agent.api_key)
        ai_config["base_url"] = web_config.agent.base_url or ""
        ai_config["model"] = web_config.agent.model or ""
        ai_config["api_format"] = (
            web_config.agent.api_format.value if web_config.agent.api_format else ""
        )

    return templates.TemplateResponse(
        "partials/settings_ai.html",
        {"request": request, "ai_config": ai_config},
    )


@router.get("/settings/auth", response_class=HTMLResponse)
async def auth_partial(request: Request, session: Session = Depends(require_auth)):
    web_config = get_web_config()

    auth_info = {
        "method": "none",
        "session_expiry": 24,
    }

    if web_config and web_config.auth:
        auth_info["method"] = (
            web_config.auth.method.value if web_config.auth.method else "none"
        )
        auth_info["session_expiry"] = web_config.auth.session_expiry_hours or 24

    return templates.TemplateResponse(
        "partials/settings_auth.html",
        {"request": request, "auth_info": auth_info, "session": session},
    )


@router.get("/settings/calendar", response_class=HTMLResponse)
async def calendar_partial(request: Request, session: Session = Depends(require_auth)):
    from workspace_secretary.web import engine_client as engine
    from workspace_secretary.web.database import get_pool

    calendars = []
    selected_ids = ["primary"]

    try:
        result = await engine.list_calendars()
        if result.get("status") == "ok":
            calendars = result.get("calendars", [])
    except Exception as e:
        logger.error(f"Failed to load calendars: {e}")

    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT prefs_json FROM user_preferences WHERE user_id = %s",
                    (session.user_id,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    prefs = row[0]
                    if isinstance(prefs, str):
                        prefs = json.loads(prefs)
                    selected_ids = prefs.get("calendar", {}).get(
                        "selected_calendar_ids", ["primary"]
                    )
    except Exception as e:
        logger.error(f"Failed to load calendar preferences: {e}")

    try:
        selection_state = db.get_calendar_selection_state(session.user_id)
        states_by_id = {
            state["calendar_id"]: state for state in selection_state["states"]
        }
        for calendar in calendars:
            cal_id = calendar.get("id") or calendar.get("calendarId")
            if not cal_id:
                continue
            state_info = states_by_id.get(cal_id, {})
            calendar["sync_status"] = state_info.get("status")
            calendar["last_sync"] = state_info.get(
                "last_incremental_sync_at"
            ) or state_info.get("last_full_sync_at")
    except Exception as e:
        logger.error(f"Failed to augment calendar sync state: {e}")

    return templates.TemplateResponse(
        "partials/settings_calendar.html",
        {"request": request, "calendars": calendars, "selected_ids": selected_ids},
    )


@router.post("/api/settings/identity")
async def update_identity_settings(
    payload: IdentitySettingsRequest,
    session: Session = Depends(require_auth),
):
    from workspace_secretary.config import UserIdentityConfig, load_config, save_config

    config = load_config(config_path="config/config.yaml")
    if not config:
        raise HTTPException(status_code=500, detail="Config not loaded")

    config.identity = UserIdentityConfig(
        email=payload.email,
        full_name=payload.full_name,
        aliases=payload.aliases,
    )

    save_config(config, config_path="config/config.yaml")
    return {"updated": True}


@router.put("/api/settings/ui")
async def update_ui_settings(
    payload: UISettingsRequest,
    session: Session = Depends(require_auth),
):
    from workspace_secretary.web.database import get_pool

    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT prefs_json FROM user_preferences WHERE user_id = %s",
                (session.user_id,),
            )
            row = cur.fetchone()
            prefs: dict = {}
            if row and row[0]:
                prefs = row[0]
                if isinstance(prefs, str):
                    prefs = json.loads(prefs)

            prefs["theme"] = payload.theme
            prefs["density"] = payload.density

            cur.execute(
                """
                INSERT INTO user_preferences (user_id, prefs_json, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET prefs_json = EXCLUDED.prefs_json, updated_at = NOW()
                """,
                (session.user_id, json.dumps(prefs)),
            )
        conn.commit()

    return {
        "updated": True,
        "theme": payload.theme,
        "density": payload.density,
    }


@router.put("/api/settings/calendar")
async def update_calendar_settings(
    payload: CalendarSettingsRequest,
    session: Session = Depends(require_auth),
):
    from workspace_secretary.web.database import get_pool

    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT prefs_json FROM user_preferences WHERE user_id = %s",
                (session.user_id,),
            )
            row = cur.fetchone()

            prefs = {}
            if row and row[0]:
                prefs = row[0]
                if isinstance(prefs, str):
                    prefs = json.loads(prefs)

            if "calendar" not in prefs:
                prefs["calendar"] = {}

            prefs["calendar"]["selected_calendar_ids"] = payload.selected_calendar_ids

            cur.execute(
                """
                INSERT INTO user_preferences (user_id, prefs_json, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET prefs_json = EXCLUDED.prefs_json, updated_at = NOW()
                """,
                (session.user_id, json.dumps(prefs)),
            )
        conn.commit()

    return {"updated": True}
