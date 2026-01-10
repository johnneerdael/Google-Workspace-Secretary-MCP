"""
Database dependency for web routes.

Provides access to the shared PostgreSQL database used by the engine.
"""

from typing import Annotated, Optional, Generator, Any
from fastapi import Depends
import os
import logging

logger = logging.getLogger(__name__)

_db_instance: Optional[Any] = None


def get_database():
    """Get or create database instance from environment config."""
    global _db_instance

    if _db_instance is not None:
        return _db_instance

    from workspace_secretary.engine.database import PostgresDatabase, SqliteDatabase

    backend = os.environ.get("DB_BACKEND", "postgres")

    if backend == "postgres":
        _db_instance = PostgresDatabase(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database=os.environ.get("POSTGRES_DB", "secretary"),
            user=os.environ.get("POSTGRES_USER", "secretary"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
        )
    else:
        _db_instance = SqliteDatabase(
            email_cache_path=os.environ.get("SQLITE_PATH", "config/email_cache.db"),
        )

    _db_instance.initialize()
    logger.info(f"Web UI database initialized: {backend}")
    return _db_instance


def get_db():
    """FastAPI dependency for database access."""
    return get_database()


DatabaseDep = Annotated[Any, Depends(get_db)]
