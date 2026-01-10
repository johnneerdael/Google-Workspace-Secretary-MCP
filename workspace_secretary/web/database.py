"""
Database dependency for web routes.

Provides access to the shared PostgreSQL database used by the engine.
Reads configuration from the same config.yaml as the MCP server.
"""

from typing import Annotated, Optional, Any
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)

_db_instance: Optional[Any] = None


def get_database():
    """Get or create database instance from config.yaml."""
    global _db_instance

    if _db_instance is not None:
        return _db_instance

    from workspace_secretary.config import load_config
    from workspace_secretary.engine.database import create_database

    config = load_config()
    _db_instance = create_database(config)
    _db_instance.initialize()

    logger.info(f"Web UI database initialized: {config.database.backend.value}")
    return _db_instance


def get_db():
    """FastAPI dependency for database access."""
    return get_database()


DatabaseDep = Annotated[Any, Depends(get_db)]
