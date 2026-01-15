import json
import asyncio
import json
from unittest.mock import MagicMock

import workspace_secretary.tools as tools


def _triage_priority_emails(**kwargs) -> str:
    if "continuation_state" in kwargs and kwargs["continuation_state"] is not None:
        continuation_state = kwargs["continuation_state"]
        if not isinstance(continuation_state, str):
            continuation_state = json.dumps(continuation_state)
        kwargs["continuation_state"] = f"raw:{continuation_state}"

    _, result = asyncio.run(tools.mcp.call_tool("triage_priority_emails", kwargs))
    return result["result"]


class _FakeIdentity:
    def __init__(self, email: str, name_tokens: list[str]):
        self._email = email.lower()
        self._name_tokens = [t.lower() for t in name_tokens]

    def matches_email(self, addr: str) -> bool:
        return self._email in (addr or "").lower()

    def matches_name(self, body: str) -> bool:
        body_l = (body or "").lower()
        return any(t in body_l for t in self._name_tokens)


class _FakeConfig:
    def __init__(self, identity: _FakeIdentity, vip_senders: list[str]):
        self.identity = identity
        self.vip_senders = vip_senders


def test_triage_priority_emails_selects_direct_to_small_recipient_list(
    monkeypatch,
):
    db = MagicMock()
    db.search_emails.return_value = [
        {
            "uid": 10,
            "from_addr": "sender@example.com",
            "to_addr": "me@example.com",
            "cc_addr": "",
            "subject": "Question",
            "date": "2026-01-01",
            "body_text": "Hi",
        }
    ]

    config = _FakeConfig(
        identity=_FakeIdentity("me@example.com", ["Jane"]), vip_senders=[]
    )

    monkeypatch.setattr(tools, "_get_database", lambda ctx: db)
    monkeypatch.setattr(tools, "_get_config", lambda ctx: config)

    out = _triage_priority_emails(ctx=None)
    payload = json.loads(out)

    assert payload["status"] == "complete"
    assert payload["has_more"] is False
    assert [e["uid"] for e in payload["priority_emails"]] == [10]


def test_triage_priority_emails_requires_user_in_to(monkeypatch):
    db = MagicMock()
    db.search_emails.return_value = [
        {
            "uid": 11,
            "from_addr": "sender@example.com",
            "to_addr": "someoneelse@example.com",
            "cc_addr": "me@example.com",
            "subject": "FYI",
            "date": "2026-01-01",
            "body_text": "Hi Jane",
        }
    ]

    config = _FakeConfig(
        identity=_FakeIdentity("me@example.com", ["Jane"]), vip_senders=[]
    )

    monkeypatch.setattr(tools, "_get_database", lambda ctx: db)
    monkeypatch.setattr(tools, "_get_config", lambda ctx: config)

    out = _triage_priority_emails(ctx=None)
    payload = json.loads(out)

    assert payload["status"] == "complete"
    assert payload["priority_emails"] == []


def test_triage_priority_emails_medium_recipient_list_requires_name_mention(
    monkeypatch,
):
    db = MagicMock()
    db.search_emails.return_value = [
        {
            "uid": 12,
            "from_addr": "sender@example.com",
            "to_addr": "me@example.com,"
            + ",".join([f"u{i}@example.com" for i in range(1, 10)]),
            "cc_addr": "",
            "subject": "Update",
            "date": "2026-01-01",
            "body_text": "No name here",
        },
        {
            "uid": 13,
            "from_addr": "sender@example.com",
            "to_addr": "me@example.com,"
            + ",".join([f"u{i}@example.com" for i in range(1, 10)]),
            "cc_addr": "",
            "subject": "Update",
            "date": "2026-01-01",
            "body_text": "Hi Jane - quick question",
        },
    ]

    config = _FakeConfig(
        identity=_FakeIdentity("me@example.com", ["Jane"]), vip_senders=[]
    )

    monkeypatch.setattr(tools, "_get_database", lambda ctx: db)
    monkeypatch.setattr(tools, "_get_config", lambda ctx: config)

    out = _triage_priority_emails(ctx=None)
    payload = json.loads(out)

    assert payload["status"] == "complete"
    assert [e["uid"] for e in payload["priority_emails"]] == [13]


def test_triage_priority_emails_vip_overrides_other_filters(monkeypatch):
    db = MagicMock()
    db.search_emails.return_value = [
        {
            "uid": 14,
            "from_addr": "ceo@company.com",
            "to_addr": "me@example.com",
            "cc_addr": "",
            "subject": "Ping",
            "date": "2026-01-01",
            "body_text": "FYI",
        }
    ]

    config = _FakeConfig(
        identity=_FakeIdentity("me@example.com", ["Jane"]),
        vip_senders=["ceo@company.com"],
    )

    monkeypatch.setattr(tools, "_get_database", lambda ctx: db)
    monkeypatch.setattr(tools, "_get_config", lambda ctx: config)

    out = _triage_priority_emails(ctx=None)
    payload = json.loads(out)

    assert payload["status"] == "complete"
    assert [e["uid"] for e in payload["priority_emails"]] == [14]


def test_triage_priority_emails_continuation_state(monkeypatch):
    db = MagicMock()
    db.search_emails.return_value = [
        {
            "uid": uid,
            "from_addr": "sender@example.com",
            "to_addr": "me@example.com",
            "cc_addr": "",
            "subject": f"S{uid}",
            "date": "2026-01-01",
            "body_text": "Hi",
        }
        for uid in range(100, 140)
    ]

    config = _FakeConfig(
        identity=_FakeIdentity("me@example.com", ["Jane"]), vip_senders=[]
    )

    monkeypatch.setattr(tools, "_get_database", lambda ctx: db)
    monkeypatch.setattr(tools, "_get_config", lambda ctx: config)

    first = _triage_priority_emails(ctx=None, time_limit_seconds=0)
    p1 = json.loads(first)
    assert p1["status"] == "partial"
    assert p1["has_more"] is True
    assert "continuation_state" in p1
    assert isinstance(p1["continuation_state"], str)

    second = _triage_priority_emails(
        ctx=None,
        continuation_state=p1["continuation_state"],
        time_limit_seconds=5,
    )
    p2 = json.loads(second)

    assert p2["status"] in ("partial", "complete")
    assert len(p2["priority_emails"]) >= 0
