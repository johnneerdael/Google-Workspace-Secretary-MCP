import sys
from unittest.mock import MagicMock

# Mock dependencies that might not be installed in the test env
sys.modules["imapclient"] = MagicMock()
sys.modules["google.oauth2.credentials"] = MagicMock()
sys.modules["google_auth_oauthlib.flow"] = MagicMock()
sys.modules["google.auth.transport.requests"] = MagicMock()

import sys
from unittest.mock import MagicMock

# Mock optional dependencies to prevent ImportError during testing
sys.modules["imapclient"] = MagicMock()
sys.modules["google.oauth2.credentials"] = MagicMock()
sys.modules["google_auth_oauthlib.flow"] = MagicMock()
sys.modules["google.auth.transport.requests"] = MagicMock()

import sys
from unittest.mock import MagicMock

sys.modules["imapclient"] = MagicMock()
sys.modules["google.oauth2.credentials"] = MagicMock()
sys.modules["google_auth_oauthlib.flow"] = MagicMock()
sys.modules["google.auth.transport.requests"] = MagicMock()

import unittest
from workspace_secretary.engine.analysis import PhishingAnalyzer


class TestPhishingAnalyzer(unittest.TestCase):
    def test_extract_domain(self):
        analyzer = PhishingAnalyzer()
        self.assertEqual(analyzer._extract_domain("test@example.com"), "example.com")
        self.assertEqual(
            analyzer._extract_domain("User Name <user@SUB.DOMAIN.CO.UK>"),
            "sub.domain.co.uk",
        )
        self.assertEqual(analyzer._extract_domain("invalid-email"), "")
        self.assertEqual(analyzer._extract_domain(""), "")

    def test_is_punycode_domain(self):
        analyzer = PhishingAnalyzer()
        self.assertFalse(analyzer._is_punycode_domain("example.com"))
        self.assertTrue(analyzer._is_punycode_domain("xn--e1afmkfd.xn--80akhbyknj4f"))
        self.assertTrue(analyzer._is_punycode_domain("xn--secure-p9a.bank.com"))
        self.assertFalse(analyzer._is_punycode_domain(""))

    def test_parse_authentication_results(self):
        analyzer = PhishingAnalyzer()

        headers_pass = {
            "Authentication-Results": "mx.google.com; dkim=pass header.i=@example.com; spf=pass (google.com: domain of test@example.com designates 1.2.3.4 as permitted sender) smtp.mailfrom=test@example.com; dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=example.com"
        }
        results_pass = analyzer._parse_authentication_results(headers_pass)
        self.assertEqual(results_pass["spf"], "pass")
        self.assertEqual(results_pass["dkim"], "pass")
        self.assertEqual(results_pass["dmarc"], "pass")

        headers_fail = {
            "Authentication-Results": "mx.google.com; spf=fail; dkim=fail; dmarc=fail"
        }
        results_fail = analyzer._parse_authentication_results(headers_fail)
        self.assertEqual(results_fail["spf"], "fail")
        self.assertEqual(results_fail["dkim"], "fail")
        self.assertEqual(results_fail["dmarc"], "fail")

        headers_empty = {}
        results_empty = analyzer._parse_authentication_results(headers_empty)
        self.assertEqual(results_empty["spf"], "unknown")
        self.assertEqual(results_empty["dkim"], "unknown")
        self.assertEqual(results_empty["dmarc"], "unknown")

        headers_mixed = {
            "Authentication-Results": "mx.google.com; spf=pass (google.com: domain of ...); dkim=pass (test mode) header.i=@example.com"
        }
        results_mixed = analyzer._parse_authentication_results(headers_mixed)
        self.assertEqual(results_mixed["spf"], "pass")
        self.assertEqual(results_mixed["dkim"], "pass")

    def test_analyze_email_clean(self):
        analyzer = PhishingAnalyzer()
        email_data = {
            "from_addr": "Trusted Sender <sender@example.com>",
            "headers": {"Authentication-Results": "spf=pass; dkim=pass; dmarc=pass"},
        }
        result = analyzer.analyze_email(email_data)
        self.assertGreaterEqual(result["score"], 90)
        self.assertIsNone(result["warning_type"])
        self.assertFalse(result["signals"]["dmarc_fail"])
        self.assertFalse(result["signals"]["reply_to_differs"])

    def test_analyze_email_dmarc_fail(self):
        analyzer = PhishingAnalyzer()
        email_data = {
            "from_addr": "Spoofed <ceo@bigcorp.com>",
            "headers": {"Authentication-Results": "dmarc=fail"},
        }
        result = analyzer.analyze_email(email_data)
        self.assertLessEqual(result["score"], 50)
        self.assertEqual(result["warning_type"], "auth_failure")

    def test_analyze_email_reply_to_mismatch(self):
        analyzer = PhishingAnalyzer()
        email_data = {
            "from_addr": "service@paypal.com",
            "reply_to": "hacker@bad-site.com",
            "headers": {"Authentication-Results": "spf=pass; dkim=pass"},
        }
        result = analyzer.analyze_email(email_data)
        self.assertTrue(result["signals"]["reply_to_differs"])
        self.assertLessEqual(result["score"], 80)
        self.assertEqual(result["warning_type"], "suspicious_sender")

    def test_analyze_email_punycode(self):
        analyzer = PhishingAnalyzer()
        email_data = {"from_addr": "support@xn--pple-43d.com", "headers": {}}
        result = analyzer.analyze_email(email_data)
        self.assertTrue(result["signals"]["punycode_domain"])
        self.assertLessEqual(result["score"], 70)
        self.assertEqual(result["warning_type"], "spoofing_risk")

    def test_analyze_email_multiple_issues(self):
        analyzer = PhishingAnalyzer()
        email_data = {
            "from_addr": "support@xn--pple-43d.com",
            "reply_to": "other@evil.com",
            "headers": {"Authentication-Results": "spf=fail; dkim=fail"},
        }
        result = analyzer.analyze_email(email_data)
        self.assertEqual(result["score"], 10)
        self.assertEqual(result["warning_type"], "auth_failure")


if __name__ == "__main__":
    unittest.main()
