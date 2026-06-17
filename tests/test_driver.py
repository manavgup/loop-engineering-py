"""Faithful pytest port of driver.test.mjs.

Tests cover run_item only. deps are plain dicts of callables (no async).
"""

from backlog_grinder.driver import run_item

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

_DIFF = (
    "diff --git a/backend/x.py b/backend/x.py\n"
    "--- a/backend/x.py\n"
    "+++ b/backend/x.py\n"
    "@@ -1 +1 @@\n"
    "-a\n"
    "+b\n"
)


def stubs(overrides=None):
    """Return (calls, deps) with sensible green-path defaults.

    overrides is a dict with an optional key 'deps' whose value is merged into
    the default deps dict, exactly mirroring the JS stubs() helper.
    """
    overrides = overrides or {}
    calls = {"commits": [], "restores": []}

    deps = {
        "implementer": lambda item, prompt: {"ok": True, "summary": "edited"},
        "verifier": lambda item, diff, warnings: {"verdict": "APPROVE", "reasons": []},
        "run_gate": lambda cmd, cwd: {
            "passed": True,
            "output": "ok",
            "coverage": {"backend/x.py": {1}},
        },
        "git": {
            "diff": lambda cwd: _DIFF,
            "commit": lambda cwd, msg: calls["commits"].append(msg),
            "restore": lambda cwd: calls["restores"].append(True),
            "head": lambda cwd: "sha1",
        },
        **(overrides.get("deps") or {}),
    }

    return calls, deps


ITEM = {
    "id": "x1",
    "title": "Fix X",
    "path": "backend/x.py:1",
    "fix": "do Y",
    "status": "pending",
    "attempts": 0,
    "failures": [],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_green_gate_clean_guards_approve_commits_status_done():
    """green gate + clean guards + APPROVE -> commit, status done."""
    calls, deps = stubs()
    r = run_item(
        {**ITEM},
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["backend/x.py"],
        deny=[],
        max_attempts=3,
    )
    assert r["status"] == "done"
    assert len(calls["commits"]) == 1
    assert len(calls["restores"]) == 0


def test_red_gate_reverts_records_failure_stays_pending():
    """red gate -> revert, record failure, stays pending under maxAttempts."""
    calls, deps = stubs()
    deps["run_gate"] = lambda cmd, cwd: {"passed": False, "output": "AssertionError"}
    r = run_item(
        {**ITEM},
        deps=deps,
        state={"items": {}},
        gate_cmd="false",
        allow=["backend/x.py"],
        deny=[],
        max_attempts=3,
    )
    assert r["status"] == "pending"
    assert len(r["failures"]) == 1
    assert len(calls["restores"]) == 1
    assert len(calls["commits"]) == 0


def test_guard_violation_out_of_allowlist_not_committed():
    """guard violation (out of allowlist) -> revert, not committed."""
    calls, deps = stubs()
    r = run_item(
        {**ITEM},
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["backend/NOTHING.py"],
        deny=[],
        max_attempts=3,
    )
    assert r["status"] != "done"
    assert len(calls["commits"]) == 0
    assert len(calls["restores"]) == 1


def test_exhausting_max_attempts_abandoned():
    """exhausting maxAttempts -> abandoned."""
    calls, deps = stubs()
    deps["run_gate"] = lambda cmd, cwd: {"passed": False, "output": "AssertionError"}
    item = {**ITEM, "attempts": 2}
    r = run_item(
        item,
        deps=deps,
        state={"items": {}},
        gate_cmd="false",
        allow=["backend/x.py"],
        deny=[],
        max_attempts=3,
    )
    assert r["status"] == "abandoned"
