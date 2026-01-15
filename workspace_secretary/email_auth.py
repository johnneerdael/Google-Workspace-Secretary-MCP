"""Email authentication and anti-phishing helpers.

This module is intentionally independent of any Gmail REST API client.
It provides parsing of Authentication-Results style headers (SPF/DKIM/DMARC)
into structured signals used by both the engine phishing analyzer and the
web dashboard.
"""

from __future__ import annotations

import re
from typing import Any


AUTH_HEADER_KEYS: tuple[str, ...] = (
    "Authentication-Results",
    "ARC-Authentication-Results",
    "Received-SPF",
)


def parse_authentication_results(headers: dict[str, Any] | Any) -> dict[str, Any]:
    """Parse Authentication-Results headers for SPF/DKIM/DMARC status.

    Args:
        headers: message headers mapping. Values may be strings or lists.

    Returns:
        Dict with keys:
          - auth_results_raw: combined raw auth headers (or None)
          - spf/dkim/dmarc: pass|fail|unknown
    """

    raw_values: list[str] = []

    if not isinstance(headers, dict):
        headers = {}

    for k in AUTH_HEADER_KEYS:
        v = headers.get(k)
        if not v:
            continue
        if isinstance(v, list):
            raw_values.extend([str(x) for x in v if x])
        else:
            raw_values.append(str(v))

    combined = "\n".join(raw_values)
    combined_l = combined.lower()

    def _has_result(prefix: str, value: str) -> bool:
        return bool(
            re.search(rf"\b{re.escape(prefix)}\s*=\s*{re.escape(value)}\b", combined_l)
        )

    spf_pass = _has_result("spf", "pass") or _has_result("spf", "bestguesspass")
    spf_fail = _has_result("spf", "fail") or _has_result("spf", "softfail")
    dkim_pass = _has_result("dkim", "pass")
    dkim_fail = _has_result("dkim", "fail")
    dmarc_pass = _has_result("dmarc", "pass")
    dmarc_fail = _has_result("dmarc", "fail")

    return {
        "auth_results_raw": combined or None,
        "spf": "pass" if spf_pass else "fail" if spf_fail else "unknown",
        "dkim": "pass" if dkim_pass else "fail" if dkim_fail else "unknown",
        "dmarc": "pass" if dmarc_pass else "fail" if dmarc_fail else "unknown",
    }
