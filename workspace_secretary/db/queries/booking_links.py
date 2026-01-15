"""Booking link query helpers."""

from __future__ import annotations

import json
from typing import Any, Optional

from psycopg.rows import dict_row

from workspace_secretary.db.types import DatabaseInterface


def _serialize_metadata(metadata: Optional[dict[str, Any]]) -> Optional[str]:
    if metadata is None:
        return None
    return json.dumps(metadata)


def _deserialize_metadata(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return value


def upsert_booking_link(
    db: DatabaseInterface,
    link_id: str,
    user_id: str,
    calendar_id: str,
    host_name: Optional[str] = None,
    meeting_title: Optional[str] = None,
    meeting_description: Optional[str] = None,
    timezone: Optional[str] = None,
    duration_minutes: int = 30,
    availability_days: int = 14,
    availability_start_hour: int = 11,
    availability_end_hour: int = 22,
    is_active: bool = True,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Insert or update a booking link definition."""

    payload = (
        link_id,
        user_id,
        calendar_id,
        host_name,
        meeting_title,
        meeting_description,
        timezone,
        duration_minutes,
        availability_days,
        availability_start_hour,
        availability_end_hour,
        is_active,
        _serialize_metadata(metadata),
    )

    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO booking_links (
                    link_id,
                    user_id,
                    calendar_id,
                    host_name,
                    meeting_title,
                    meeting_description,
                    timezone,
                    duration_minutes,
                    availability_days,
                    availability_start_hour,
                    availability_end_hour,
                    is_active,
                    metadata,
                    updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT(link_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    calendar_id = EXCLUDED.calendar_id,
                    host_name = EXCLUDED.host_name,
                    meeting_title = EXCLUDED.meeting_title,
                    meeting_description = EXCLUDED.meeting_description,
                    timezone = EXCLUDED.timezone,
                    duration_minutes = EXCLUDED.duration_minutes,
                    availability_days = EXCLUDED.availability_days,
                    availability_start_hour = EXCLUDED.availability_start_hour,
                    availability_end_hour = EXCLUDED.availability_end_hour,
                    is_active = EXCLUDED.is_active,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                payload,
            )
            conn.commit()


def set_booking_link_status(
    db: DatabaseInterface, link_id: str, is_active: bool
) -> bool:
    """Activate or deactivate a booking link."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE booking_links
                SET is_active = %s, updated_at = NOW()
                WHERE link_id = %s
                """,
                (is_active, link_id),
            )
            conn.commit()
            return cur.rowcount > 0


def get_booking_link(db: DatabaseInterface, link_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single booking link by ID."""
    with db.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM booking_links WHERE link_id = %s",
                (link_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            row["metadata"] = _deserialize_metadata(row.get("metadata"))
            return row


def list_booking_links_for_user(
    db: DatabaseInterface, user_id: str, include_inactive: bool = False
) -> list[dict[str, Any]]:
    """Return booking links owned by the given user."""
    with db.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if include_inactive:
                cur.execute(
                    "SELECT * FROM booking_links WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM booking_links
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
            rows = cur.fetchall() or []
            for row in rows:
                row["metadata"] = _deserialize_metadata(row.get("metadata"))
            return rows
