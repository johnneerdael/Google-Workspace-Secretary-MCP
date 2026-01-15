"""
Phishing and security analysis module.

This module centralizes logic for detecting suspicious emails, analyzing
authentication headers (SPF/DKIM/DMARC), and calculating security scores.
"""

import re
import idna
import json
import logging
from email.utils import parseaddr
from typing import Any, Dict, Optional, TypedDict

from workspace_secretary.email_auth import parse_authentication_results

logger = logging.getLogger(__name__)


class SecurityResult(TypedDict):
    """Result of security analysis."""

    score: int
    warning_type: Optional[str]
    signals: Dict[str, Any]
    auth_results: Dict[str, Any]


class PhishingAnalyzer:
    """Analyzer for email security signals."""

    @staticmethod
    def _parse_authentication_results(headers: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Authentication-Results headers for SPF/DKIM/DMARC status.

        Backwards-compatible wrapper around workspace_secretary.email_auth.
        """

        return parse_authentication_results(headers)

    @staticmethod
    def _extract_domain(addr: str) -> str:
        """Extract domain from email address."""
        _, email_addr = parseaddr(addr or "")
        if "@" not in email_addr:
            return ""
        return email_addr.split("@", 1)[1].strip().lower()

    @staticmethod
    def _is_punycode_domain(domain: str) -> bool:
        """Check if domain uses punycode (potential spoofing)."""
        if not domain:
            return False
        try:
            decoded = idna.decode(domain)
            return decoded != domain
        except Exception:
            # Fallback check for xn-- prefix if decode fails
            return "xn--" in domain

    def analyze_email(self, email_data: Dict[str, Any]) -> SecurityResult:
        """
        Analyze an email for security risks.

        Args:
            email_data: Dictionary containing email fields:
                - from_addr or from: Sender address
                - headers: Dict of headers (Reply-To, etc.)
                - reply_to: Optional reply-to address

        Returns:
            SecurityResult dict with score, warning, signals, and auth info.
        """
        # Normalize input keys
        from_addr = str(email_data.get("from_addr") or email_data.get("from") or "")

        headers = email_data.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}

        reply_to_raw = ""
        # Try direct field first, then headers
        reply_to_val = (
            email_data.get("reply_to")
            or email_data.get("reply-to")
            or email_data.get("reply_to_addr")
        )
        if reply_to_val:
            reply_to_raw = str(reply_to_val)
        elif headers.get("Reply-To"):
            reply_to_raw = str(headers.get("Reply-To"))

        # 1. Parse Auth Results
        auth_results = self._parse_authentication_results(headers)

        # 2. Sender Analysis
        from_domain = self._extract_domain(from_addr)
        reply_to_domain = self._extract_domain(reply_to_raw)

        # Signal: Reply-to domain differs from From domain
        reply_to_differs = bool(
            reply_to_domain and from_domain and reply_to_domain != from_domain
        )

        # Signal: Display name spoofing (e.g. "CEO Name <attacker@gmail.com>")
        display_name, parsed_addr = parseaddr(from_addr)
        display_name_l = (display_name or "").lower()
        parsed_local = (
            parsed_addr.split("@", 1)[0].lower() if "@" in parsed_addr else ""
        )

        display_name_mismatch = False
        if display_name_l and parsed_local:
            # Simple heuristic: if local part is "clean" but not found in display name
            token = re.sub(r"[^a-z0-9]+", "", parsed_local)
            # If token is substantial and not in display name, might be mismatch
            # (Note: This is a weak signal, often false positives, but kept from original logic)
            if (
                token
                and len(token) > 3
                and token not in re.sub(r"[^a-z0-9]+", "", display_name_l)
            ):
                display_name_mismatch = True

        # Signal: Punycode domains
        punycode_domain = self._is_punycode_domain(
            from_domain
        ) or self._is_punycode_domain(reply_to_domain)

        signals = {
            "reply_to_differs": reply_to_differs,
            "display_name_mismatch": display_name_mismatch,
            "punycode_domain": punycode_domain,
            "spf_fail": auth_results["spf"] == "fail",
            "dkim_fail": auth_results["dkim"] == "fail",
            "dmarc_fail": auth_results["dmarc"] == "fail",
        }

        # 3. Calculate Score
        score = 100
        warning_type = None

        # Heavy penalties
        if signals["dmarc_fail"]:
            score -= 50
            warning_type = "auth_failure"
        elif signals["spf_fail"] and signals["dkim_fail"]:
            score -= 40
            warning_type = "auth_failure"

        if signals["punycode_domain"]:
            score -= 30
            if warning_type is None:
                warning_type = "spoofing_risk"

        if signals["reply_to_differs"]:
            score -= 20
            if warning_type is None:
                warning_type = "suspicious_sender"

        # Moderate penalties
        if signals["spf_fail"] and score > 60:
            score -= 10

        if signals["display_name_mismatch"]:
            score -= 10
            if warning_type is None:
                warning_type = "suspicious_sender"

        # Clamp score
        score = max(0, min(100, score))

        # Set generic warning if score is low but no specific type set
        if score < 70 and warning_type is None:
            warning_type = "low_trust"

        # If score is high, clear warning
        if score >= 90:
            warning_type = None

        return {
            "score": score,
            "warning_type": warning_type,
            "signals": signals,
            "auth_results": auth_results,
        }
