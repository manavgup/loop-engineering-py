"""Tests for backlog_grinder.parse.

Every assertion in the JS test suite is reproduced here as plain def test_*
functions using assert statements — no async, no pytest-asyncio.
"""

import re

from backlog_grinder.parse import is_stale, parse_backlog, parse_path_ref

# ---------------------------------------------------------------------------
# Shared markdown fixture
# ---------------------------------------------------------------------------

FIXTURE = """\
### \U0001f534 CRITICAL (9)

#### bug-fix

- [ ] **Providers pass masked SecretStr to SDK**  ·  `backend/openai.py:46`  ·  _S/high_
    - _Evidence:_ str(SecretStr) returns the mask string.
    - _Fix:_ use api_key.get_secret_value().

#### security

- [ ] **verify_jwt disables signature verification**  ·  `backend/auth/oidc.py:74-82`  ·  _M/high_
    - _Evidence:_ options verify_signature False.
    - _Fix:_ verify signature against jwt_secret_key.
"""


# ---------------------------------------------------------------------------
# test: parseBacklog extracts full item fields from the real format
# ---------------------------------------------------------------------------


def test_parse_backlog_extracts_full_item_fields():
    items = parse_backlog(FIXTURE)
    assert len(items) == 2

    a = items[0]
    assert a["title"] == "Providers pass masked SecretStr to SDK"
    assert a["path"] == "backend/openai.py:46"
    assert a["effort"] == "S"
    assert a["severity"] == "critical"
    assert a["category"] == "bug-fix"
    assert a["evidence"] == "str(SecretStr) returns the mask string."
    assert a["fix"] == "use api_key.get_secret_value()."
    assert a["checked"] is False
    assert re.fullmatch(r"[0-9a-f]{12}", a["id"]), f"id {a['id']!r} must be 12 hex chars"

    assert items[1]["category"] == "security"
    assert items[1]["severity"] == "critical"


# ---------------------------------------------------------------------------
# test: parsePathRef + isStale
# ---------------------------------------------------------------------------


def test_parse_path_ref_with_line_number():
    result = parse_path_ref("backend/openai.py:46")
    assert result == {"file": "backend/openai.py", "line": 46}


def test_is_stale_returns_false_when_file_exists():
    assert is_stale({"path": "backend/openai.py:46"}, lambda f: True) is False


def test_is_stale_returns_true_when_file_missing():
    assert is_stale({"path": "gone.py:1"}, lambda f: False) is True


def test_is_stale_returns_true_when_path_empty():
    assert is_stale({"path": ""}, lambda f: True) is True
