import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from workspace_secretary.web.database import get_search_suggestions
from workspace_secretary.web.auth import CSRFMiddleware
from workspace_secretary.engine.database import PostgresDatabase
from fastapi import Request


class TestDBFixes:
    def test_get_search_suggestions_query(self):
        """Verify the SQL query used in get_search_suggestions avoids InvalidColumnReference."""
        with patch("workspace_secretary.web.database.get_conn") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur

            # Setup mock return to avoid iteration error
            mock_cur.fetchall.return_value = []

            get_search_suggestions("test", limit=5)

            # Verify the second call (subjects query)
            # The first call is for senders
            assert mock_cur.execute.call_count == 2

            # Check the subjects query
            args, _ = mock_cur.execute.call_args_list[1]
            sql = args[0]

            # Verify usage of GROUP BY and aggregate in ORDER BY
            assert "GROUP BY subject" in sql
            assert "ORDER BY MAX(date)" in sql
            assert "SELECT subject" in sql

    def test_postgres_db_init_contacts(self):
        """Verify PostgresDatabase.initialize includes contacts tables."""
        with patch("psycopg_pool.ConnectionPool") as MockPool:
            db = PostgresDatabase()
            mock_conn = MagicMock()
            mock_cur = MagicMock()

            db._pool = MockPool.return_value
            db._pool.connection.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur

            db.initialize()

            # Collect all executed SQL statements
            executed_sql = []
            for call in mock_cur.execute.call_args_list:
                executed_sql.append(call[0][0])

            # Verify contact tables creation
            sql_text = " ".join(executed_sql).lower()
            assert "create table if not exists contacts" in sql_text
            assert "create table if not exists contact_interactions" in sql_text
            assert "create table if not exists contact_notes" in sql_text
            assert "create table if not exists contact_tags" in sql_text


@pytest.mark.asyncio
class TestCSRFFixes:
    async def test_csrf_middleware_skips_safe_methods(self):
        """Verify CSRFMiddleware skips validation for safe methods."""
        app = MagicMock()
        middleware = CSRFMiddleware(app)

        # Test GET request (Safe)
        request = MagicMock(spec=Request)
        request.method = "GET"

        call_next = AsyncMock(return_value="response")

        response = await middleware.dispatch(request, call_next)

        assert response == "response"
        call_next.assert_called_once_with(request)

    async def test_csrf_middleware_checks_unsafe_methods(self):
        """Verify CSRFMiddleware checks unsafe methods."""
        app = MagicMock()
        middleware = CSRFMiddleware(app)

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.cookies = {}
        request.headers = {}

        call_next = AsyncMock()

        # Should raise 403 because no session/token provided (default behavior of middleware)
        # Note: In the actual implementation, it calls get_session.
        # If get_session returns None, it proceeds (assuming auth middleware handles it or it's a public endpoint?
        # Wait, let's check the code:
        # if method in {"POST"...}:
        #    session = get_session(request)
        #    if session: ... check token ...
        #
        # So if NO session, it proceeds?
        # Let's verify the code in workspace_secretary/web/auth.py lines 338-339:
        # session = get_session(request)
        # if session:
        #    ... check ...

        # So if we mock get_session to return a session, it should fail if headers are missing.

        with patch("workspace_secretary.web.auth.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.csrf_token = "expected_token"
            mock_get_session.return_value = mock_session

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as excinfo:
                await middleware.dispatch(request, call_next)

            assert excinfo.value.status_code == 403
            assert excinfo.value.detail == "CSRF token missing or invalid"
