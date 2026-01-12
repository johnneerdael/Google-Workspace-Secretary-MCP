import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os

os.environ["SECRETARY_DATABASE_BACKEND"] = "sqlite"

test_app = FastAPI()

from workspace_secretary.web.routes import notifications, admin, settings

test_app.include_router(notifications.router)
test_app.include_router(admin.router)
test_app.include_router(settings.router)

from workspace_secretary.web.auth import Session

client = TestClient(test_app)


async def mock_require_auth():
    return Session(user_id="test_user", email="test@example.com")


test_app.dependency_overrides[notifications.require_auth] = mock_require_auth
test_app.dependency_overrides[admin.require_auth] = mock_require_auth
test_app.dependency_overrides[settings.require_auth] = mock_require_auth


@pytest.mark.asyncio
async def test_sync_status_endpoint():
    """Test GET /api/sync/status endpoint functionality."""
    with patch("workspace_secretary.web.engine_client.get_status") as mock_status:
        with patch("workspace_secretary.web.engine_client.get_folders") as mock_folders:
            mock_status.return_value = {
                "status": "running",
                "imap_connected": True,
                "enrolled": True,
            }
            mock_folders.return_value = {"INBOX": 10}

            response = client.get("/api/sync/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["running"] is True
            assert data["connected"] is True
            assert data["enrolled"] is True
            assert "last_sync" in data
            assert data["folders"] == {"INBOX": 10}


@pytest.mark.asyncio
async def test_activity_log_endpoint():
    """Test GET /api/activity/log endpoint functionality."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    from datetime import datetime

    now = datetime.now()

    mock_cursor.description = [
        ("id",),
        ("email_uid",),
        ("email_folder",),
        ("action",),
        ("status",),
        ("error",),
        ("created_at",),
        ("completed_at",),
    ]
    mock_cursor.fetchall.return_value = [
        (1, 123, "INBOX", "archive", "success", None, now, now)
    ]

    with patch("workspace_secretary.web.database.get_conn") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        response = client.get("/api/activity/log")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert len(data["log"]) == 1
        assert data["log"][0]["action"] == "archive"
        assert data["log"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_update_identity_settings():
    """Test POST /api/settings/identity endpoint functionality."""
    with patch("workspace_secretary.config.save_config") as mock_save:
        with patch("workspace_secretary.config.load_config") as mock_load:
            mock_conf = MagicMock()
            mock_load.return_value = mock_conf

            payload = {
                "email": "test@test.com",
                "full_name": "Test User",
                "aliases": [],
            }
            response = client.post("/api/settings/identity", json=payload)

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_update_ui_settings():
    """Test PUT /api/settings/ui endpoint functionality."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("workspace_secretary.web.database.get_pool") as mock_pool_func:
        mock_pool_obj = MagicMock()
        mock_pool_func.return_value = mock_pool_obj
        mock_pool_obj.connection.return_value.__enter__.return_value = mock_conn

        payload = {"theme": "dark", "density": "compact"}
        response = client.put("/api/settings/ui", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        assert mock_cursor.execute.call_count == 1
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "INSERT INTO user_preferences" in sql
