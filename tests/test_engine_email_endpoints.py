import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from workspace_secretary.engine.api import app, state


@pytest.fixture(autouse=True)
def reset_state():
    state.enrolled = True
    state.config = MagicMock()
    state.config.imap.username = "me@example.com"
    state.config.imap.oauth2 = MagicMock()
    state.database = MagicMock()
    state.database.get_user_preferences.return_value = {
        "calendar": {"selected_calendar_ids": ["primary"]}
    }
    state.database.list_calendar_outbox.return_value = []
    state.database.get_calendar_sync_state.return_value = {
        "last_incremental_sync_at": None
    }
    state.imap_client = MagicMock()
    state.calendar_client = MagicMock()
    state.calendar_client.service = MagicMock()
    yield
    state.imap_client = None
    state.calendar_client = None


def _client():
    return TestClient(app)


def _basic_send_payload():
    return {"to": ["a@example.com"], "subject": "s", "body": "b"}


def test_send_email_rejects_missing_config():
    state.config = None
    response = _client().post("/api/email/send", json=_basic_send_payload())
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Configuration not loaded"


def test_send_email_requires_oauth():
    state.config.imap.oauth2 = None
    response = _client().post("/api/email/send", json=_basic_send_payload())
    assert response.status_code == status.HTTP_412_PRECONDITION_FAILED
    assert "OAuth2 configuration" in response.json()["detail"]


def test_send_email_calls_smtp():
    with patch("workspace_secretary.engine.api.SMTPClient") as mock_smtp:
        mock_client = MagicMock()
        mock_smtp.return_value = mock_client
        response = _client().post("/api/email/send", json=_basic_send_payload())
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"
    mock_client.send_message.assert_called_once()


def test_create_draft_reply_not_found():
    state.database.get_email_by_uid.return_value = None
    response = _client().post(
        "/api/email/draft-reply",
        json={"uid": 1, "folder": "INBOX", "body": "hi"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Original email not found" in response.json()["detail"]


def test_create_draft_reply_success():
    state.database.get_email_by_uid.return_value = {
        "from_addr": "sender@example.com",
        "subject": "Hello",
        "message_id": "<mid>",
    }
    state.imap_client.save_draft_mime.return_value = 555

    response = _client().post(
        "/api/email/draft-reply",
        json={"uid": 1, "folder": "INBOX", "body": "Thanks"},
    )

    body = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert body["status"] == "ok"
    assert body["draft_uid"] == 555
    state.imap_client.save_draft_mime.assert_called_once()


def test_setup_labels_dry_run():
    state.imap_client.list_folders.return_value = []
    response = _client().post(
        "/api/email/setup-labels",
        json={"dry_run": True},
    )
    payload = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert payload["status"] == "ok"
    assert payload["dry_run"] is True
    assert payload["created"]


def test_setup_labels_requires_enrollment():
    state.enrolled = False
    response = _client().post(
        "/api/email/setup-labels",
        json={"dry_run": True},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "No account" in response.json()["detail"]


def test_setup_labels_creates_missing():
    state.imap_client.list_folders.return_value = ["Secretary"]
    state.imap_client.create_folder.return_value = True

    response = _client().post(
        "/api/email/setup-labels",
        json={"dry_run": False},
    )

    payload = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert payload["status"] == "ok"
    assert "failed" in payload
    state.imap_client.create_folder.assert_called()
