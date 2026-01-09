"""Command-line tool for setting up OAuth2 authentication for Gmail."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from workspace_secretary.config import OAuth2Config, OAuthMode
from workspace_secretary.browser_auth import load_client_credentials, run_local_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_gmail_oauth2(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    credentials_file: Optional[str] = None,
    config_path: Optional[str] = None,
    config_output: Optional[str] = None,
    manual_mode: bool = True,
    token_output: Optional[str] = None,
) -> Dict[str, Any]:
    """Set up OAuth2 authentication for Gmail.

    Args:
        client_id: Google API client ID
        client_secret: Google API client secret
        config_path: Path to existing config file to update (optional)
        config_output: Path to save the updated config file (optional)

    Returns:
        Updated configuration dictionary
    """
    if credentials_file and not (client_id and client_secret):
        try:
            logger.info(f"Loading credentials from {credentials_file}")
            client_id, client_secret = load_client_credentials(credentials_file)
            logger.info("Successfully loaded credentials from file")
        except Exception as e:
            logger.error(f"Failed to load credentials from file: {e}")
            sys.exit(1)

    if not client_id or not client_secret:
        logger.error("Client ID and Client Secret are required")
        print("\nYou must provide either:")
        print("  1. Client ID and Client Secret directly, or")
        print(
            "  2. Path to the credentials JSON file downloaded from Google Cloud Console"
        )
        sys.exit(1)

    print("\nStarting OAuth2 authentication flow...")
    if manual_mode:
        print(
            "Using manual mode - you will need to paste the redirect URL after authorization.\n"
        )
    else:
        print("Using automatic mode - a browser window will open for authorization.\n")

    try:
        access_token, refresh_token, token_expiry = run_local_server(
            client_id=client_id,
            client_secret=client_secret,
            oauth_mode=OAuthMode.IMAP,
            manual_mode=manual_mode,
        )
        if not refresh_token:
            logger.error("Failed to obtain refresh token")
            sys.exit(1)
        logger.info("Successfully obtained tokens")
    except Exception as e:
        logger.error(f"Failed to obtain tokens: {e}")
        sys.exit(1)

    oauth2_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "access_token": access_token,
        "token_expiry": token_expiry,
    }

    config_data = {}
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded existing configuration from {config_path}")

    if "imap" not in config_data:
        config_data["imap"] = {}

    config_data["imap"]["oauth2"] = oauth2_data

    if config_output:
        output_file = Path(config_output)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)
            logger.info(f"Saved updated configuration to {config_output}")

    if token_output:
        token_file = Path(token_output)
        token_file.parent.mkdir(parents=True, exist_ok=True)

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": token_expiry,
        }
        with open(token_file, "w") as f:
            json.dump(token_data, f, indent=2)
            logger.info(f"Saved tokens to {token_output}")

    print("\n" + "=" * 60)
    print("OAuth2 Setup Complete!")
    print("=" * 60)
    print("\nYour credentials have been saved. You can now start the server.")
    print("\nEnvironment variables (alternative to config file):")
    print(f"  GMAIL_CLIENT_ID={client_id}")
    print(f"  GMAIL_CLIENT_SECRET={client_secret}")
    print(f"  GMAIL_REFRESH_TOKEN={oauth2_data['refresh_token']}")

    return config_data


def main() -> None:
    """Run the OAuth2 setup tool."""
    parser = argparse.ArgumentParser(
        description="Set up OAuth2 authentication for Gmail"
    )
    parser.add_argument(
        "--client-id",
        help="Google API client ID (optional if credentials file is provided)",
        default=os.environ.get("GMAIL_CLIENT_ID"),
    )
    parser.add_argument(
        "--client-secret",
        help="Google API client secret (optional if credentials file is provided)",
        default=os.environ.get("GMAIL_CLIENT_SECRET"),
    )
    parser.add_argument(
        "--credentials-file",
        help="Path to the OAuth2 client credentials JSON file downloaded from Google Cloud Console",
    )
    parser.add_argument(
        "--config",
        help="Path to existing config file to update",
        default=None,
    )
    parser.add_argument(
        "--output",
        help="Path to save the updated config file",
        default="config.yaml",
    )
    parser.add_argument(
        "--token-output",
        help="Path to save token.json file separately",
        default=None,
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        default=True,
        help="Use manual OAuth flow (paste redirect URL). This is the default.",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Use automatic browser-based OAuth flow (runs local server)",
    )

    args = parser.parse_args()

    manual_mode = not args.browser

    setup_gmail_oauth2(
        client_id=args.client_id,
        client_secret=args.client_secret,
        credentials_file=args.credentials_file,
        config_path=args.config,
        config_output=args.output,
        manual_mode=manual_mode,
        token_output=args.token_output,
    )


if __name__ == "__main__":
    main()
