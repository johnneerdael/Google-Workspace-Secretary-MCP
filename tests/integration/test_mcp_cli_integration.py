"""Integration tests for MCP CLI with IMAP server integration.

This test verifies the basics of server configuration and proper CLI interaction with the IMAP MCP server.
Following the project's integration testing framework, all tests
are tagged with @pytest.mark.integration and can be run or skipped with
the --skip-integration flag.
"""

import json
import os
import pytest
import subprocess
import time
import logging
import tempfile
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Define paths and variables
PROJECT_ROOT = Path.cwd()
SERVER_MODULE = "imap_mcp.server"


class TestImapMcpServerConfig:
    """Test the IMAP MCP server configuration and basic CLI functionality."""

    def test_server_module_runnable(self):
        """Test that the IMAP MCP server module can be invoked with --help."""
        # Use sys.executable to ensure we use the same python interpreter
        result = subprocess.run(
            [sys.executable, "-m", SERVER_MODULE, "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        # Verify it exits successfully and contains expected help output
        assert result.returncode == 0, (
            f"Server module --help failed with code {result.returncode}\nStderr: {result.stderr}"
        )
        # ArgumentParser help usually goes to stdout
        assert "usage:" in result.stdout or "usage:" in result.stderr, (
            "Help output not found"
        )
