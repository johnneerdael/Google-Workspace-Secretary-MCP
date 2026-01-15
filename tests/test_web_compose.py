import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from workspace_secretary.web.routes import compose
from workspace_secretary.web.auth import Session


@pytest.fixture()
def compose_client():
    app = FastAPI()
    app.include_router(compose.router)

    async def mock_require_auth():
        return Session(user_id="tester", email="tester@example.com")

    app.dependency_overrides[compose.require_auth] = mock_require_auth
    return TestClient(app)


def _payload(**overrides):
    base = {"to": "user@example.com", "subject": "Hello", "body": "Body"}
    base.update(overrides)
    return base


def test_send_blocks_attachments(compose_client):
    response = compose_client.post(
        "/api/email/send",
        data=_payload(),
        files={"attachments": ("test.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 501
    data = response.json()
    assert data["success"] is False
    assert "Attachment support" in data["error"]


def test_send_blocks_scheduling(compose_client):
    response = compose_client.post(
        "/api/email/send",
        data=_payload(schedule_time="2026-01-14T12:00:00"),
    )

    assert response.status_code == 501
    data = response.json()
    assert data["success"] is False
    assert "Scheduled send" in data["error"]


@patch("workspace_secretary.web.routes.compose.engine.send_email")
def test_send_bubbles_engine_http_error(mock_send_email, compose_client):
    mock_send_email.side_effect = HTTPException(status_code=503, detail="engine down")

    response = compose_client.post("/api/email/send", data=_payload())

    assert response.status_code == 503
    data = response.json()
    assert data["success"] is False
    assert data["error"] == "engine down"


@patch("workspace_secretary.web.routes.compose.engine.send_email")
def test_send_returns_validation_error(mock_send_email, compose_client):
    mock_send_email.side_effect = ValueError("bad input")

    response = compose_client.post("/api/email/send", data=_payload())

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"] == "bad input"


@patch("workspace_secretary.web.routes.compose.engine.send_email")
def test_send_handles_unexpected_error(mock_send_email, compose_client):
    mock_send_email.side_effect = RuntimeError("boom")

    response = compose_client.post("/api/email/send", data=_payload())

    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    assert data["error"] == "Unexpected send failure"


@patch(
    "workspace_secretary.web.routes.compose.engine.send_email", new_callable=AsyncMock
)
def test_send_success(mock_send_email, compose_client):
    response = compose_client.post("/api/email/send", data=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Email sent successfully"
    mock_send_email.assert_awaited_once_with(
        to="user@example.com",
        subject="Hello",
        body="Body",
        cc=None,
        bcc=None,
        reply_to_message_id=None,
    )


def _draft_payload(**overrides):
    base = {"uid": 1, "folder": "INBOX", "body": "Reply", "reply_all": False}
    base.update(overrides)
    return base


@patch("workspace_secretary.web.routes.compose.engine.create_draft_reply")
def test_save_draft_bubbles_engine_http_error(mock_create_draft, compose_client):
    mock_create_draft.side_effect = HTTPException(status_code=502, detail="engine busy")

    response = compose_client.post("/api/email/draft", data=_draft_payload())

    assert response.status_code == 502
    data = response.json()
    assert data["success"] is False
    assert data["error"] == "engine busy"


@patch("workspace_secretary.web.routes.compose.engine.create_draft_reply")
def test_save_draft_returns_validation_error(mock_create_draft, compose_client):
    mock_create_draft.side_effect = ValueError("missing body")

    response = compose_client.post("/api/email/draft", data=_draft_payload())

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"] == "missing body"


@patch("workspace_secretary.web.routes.compose.engine.create_draft_reply")
def test_save_draft_handles_unexpected_error(mock_create_draft, compose_client):
    mock_create_draft.side_effect = RuntimeError("boom")

    response = compose_client.post("/api/email/draft", data=_draft_payload())

    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    assert data["error"] == "Unexpected draft failure"


@patch(
    "workspace_secretary.web.routes.compose.engine.create_draft_reply",
    new_callable=AsyncMock,
)
def test_save_draft_success(mock_create_draft, compose_client):
    response = compose_client.post("/api/email/draft", data=_draft_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Draft saved"
    mock_create_draft.assert_awaited_once_with(
        uid=1,
        folder="INBOX",
        body="Reply",
        reply_all=False,
    )
