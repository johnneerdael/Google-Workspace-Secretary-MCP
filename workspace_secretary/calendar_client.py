"""Google Calendar client for the AI Secretary."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from workspace_secretary.config import ServerConfig

logger = logging.getLogger(__name__)


class CalendarClient:
    """Client for interacting with Google Calendar API."""

    def __init__(self, config: ServerConfig):
        self.config: ServerConfig = config
        self.service: Any = None
        self._creds: Optional[Credentials] = None

    def _get_credentials(self) -> Optional[Credentials]:
        """Convert our OAuth2Config to Google Credentials."""
        if not self.config.imap.oauth2:
            logger.error("OAuth2 configuration missing for Calendar")
            return None

        oauth = self.config.imap.oauth2
        creds = Credentials(
            token=oauth.access_token,
            refresh_token=oauth.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=oauth.client_id,
            client_secret=oauth.client_secret,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Note: In a real app, we'd want to save the new access_token back to config/file

        return creds

    def connect(self):
        """Initialize the Calendar service."""
        try:
            creds = self._get_credentials()
            if not creds:
                raise ValueError("Could not obtain credentials for Calendar")

            self.service = build("calendar", "v3", credentials=creds)
            logger.info("Successfully connected to Google Calendar API")
        except Exception as e:
            logger.error(f"Failed to connect to Google Calendar: {e}")
            raise

    def _ensure_connected(self) -> Any:
        """Ensure service is connected and return it."""
        if not self.service:
            self.connect()
        if not self.service:
            raise RuntimeError("Failed to connect to Calendar service")
        return self.service

    def list_events(
        self, time_min: str, time_max: str, calendar_id: str = "primary"
    ) -> List[Dict[str, Any]]:
        """List events in a given time range."""
        service = self._ensure_connected()

        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        return events_result.get("items", [])

    def create_event(
        self,
        event_data: Dict[str, Any],
        calendar_id: str = "primary",
        conference_data_version: int = 0,
    ) -> Dict[str, Any]:
        """Create a new calendar event.

        Args:
            event_data: Event details
            calendar_id: Calendar ID
            conference_data_version: Version for conference data (set to 1 to enable Meet)
        """
        service = self._ensure_connected()

        event = (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=event_data,
                conferenceDataVersion=conference_data_version,
            )
            .execute()
        )

        logger.info(f"Created event: {event.get('htmlLink')}")
        return event

    def get_availability(
        self,
        time_min: str,
        time_max: str,
        calendar_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Check availability using the freebusy endpoint."""
        service = self._ensure_connected()

        calendars = calendar_ids or ["primary"]
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": cal_id} for cal_id in calendars],
        }

        return service.freebusy().query(body=body).execute()

    def get_calendar(
        self,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """Get calendar details including conference properties.

        Args:
            calendar_id: Calendar ID

        Returns:
            Calendar details with conferenceProperties
        """
        service = self._ensure_connected()
        return service.calendars().get(calendarId=calendar_id).execute()

    def get_conference_solutions(
        self,
        calendar_id: str = "primary",
    ) -> List[Dict[str, Any]]:
        """Get available conference solutions for a calendar.

        Args:
            calendar_id: Calendar ID

        Returns:
            List of conference solution types available for this calendar
        """
        calendar = self.get_calendar(calendar_id)
        conference_properties = calendar.get("conferenceProperties", {})
        allowed_types = conference_properties.get("allowedConferenceSolutionTypes", [])

        # Map types to more readable names
        type_mapping = {
            "eventHangout": {
                "id": "eventHangout",
                "name": "Google Meet (Classic)",
                "description": "Classic Google Meet video conferencing",
            },
            "eventNamedHangout": {
                "id": "eventNamedHangout",
                "name": "Named Hangout",
                "description": "Named Google Hangout video conference",
            },
            "hangoutsMeet": {
                "id": "hangoutsMeet",
                "name": "Google Meet",
                "description": "Modern Google Meet video conferencing",
            },
            "addOn": {
                "id": "addOn",
                "name": "Third-party Add-on",
                "description": "Third-party video conferencing add-on",
            },
        }

        return [
            type_mapping.get(t, {"id": t, "name": t, "description": t})
            for t in allowed_types
        ]
