import pytest

from workspace_secretary.email_auth import parse_authentication_results
from workspace_secretary.web.routes.analysis import _sender_suspicion_signals


def test_parse_authentication_results_pass():
    headers = {
        "Authentication-Results": "mx.google.com; spf=pass (google.com: domain of x@example.com designates 1.2.3.4) smtp.mailfrom=x@example.com; dkim=pass header.i=@example.com; dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=example.com",
        "Received-SPF": "pass (google.com: domain of x@example.com designates 1.2.3.4 as permitted sender) client-ip=1.2.3.4;",
    }
    out = parse_authentication_results(headers)
    assert out["spf"] == "pass"
    assert out["dkim"] == "pass"
    assert out["dmarc"] == "pass"
    assert out["auth_results_raw"]


def test_parse_authentication_results_fail():
    headers = {
        "Authentication-Results": "mx.google.com; spf=fail smtp.mailfrom=bad.com; dkim=fail header.i=@bad.com; dmarc=fail header.from=bad.com",
    }
    out = parse_authentication_results(headers)
    assert out["spf"] == "fail"
    assert out["dkim"] == "fail"
    assert out["dmarc"] == "fail"


def test_sender_suspicion_reply_to_differs():
    email = {
        "from_addr": "PayPal <billing@paypal.com>",
        "headers": {"Reply-To": "scam@evil.com"},
    }
    out = _sender_suspicion_signals(email)
    assert out["reply_to_differs"] is True
    assert out["is_suspicious_sender"] is True


def test_sender_suspicion_punycode_domain():
    email = {
        "from_addr": "Support <help@xn--pple-43d.com>",
        "headers": {},
    }
    out = _sender_suspicion_signals(email)
    assert out["punycode_domain"] is True
    assert out["is_suspicious_sender"] is True
