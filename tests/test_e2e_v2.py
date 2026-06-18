"""End-to-end proofs (PROOF 1–6) of the driver invariants.

PROOF 1: coverage reject
PROOF 2: repeat-escalation
PROOF 3: budget halt + checkpoint
PROOF 4: resume (skip done, reconcile crash-commit)
PROOF 5: §7 restore on blocked-coverage-config
PROOF 6: coverage-feedback retry

All deps are plain dicts of callables (no async).
"""

from backlog_grinder.driver import run_item, run_queue
from backlog_grinder.state import mark_done

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DIFF = (
    "diff --git a/src/x.py b/src/x.py\n"
    "--- a/src/x.py\n"
    "+++ b/src/x.py\n"
    "@@ -10,1 +11,1 @@\n"
    "-a\n"
    "+b\n"
)


def base_deps(over=None):
    """Return a green-path deps dict, optionally overridden by `over`."""
    over = over or {}
    deps = {
        "implementer": lambda item, prompt: {"ok": True},
        "verifier": lambda item, diff, warnings: {"verdict": "APPROVE", "reasons": []},
        "run_gate": lambda cmd, cwd: {
            "passed": True,
            "output": "ok",
            "infra_error": False,
            "coverage": {"src/x.py": {11}},
        },
        "git": {
            "diff": lambda cwd: _DIFF,
            "commit": lambda cwd, msg: None,
            "restore": lambda cwd: None,
            "head": lambda cwd: "sha1",
        },
    }
    deps.update(over)
    return deps


def item(o=None):
    """Factory for a minimal pending item dict."""
    o = o or {}
    base = {
        "id": "i1",
        "title": "fix",
        "path": "src/x.py:11",
        "status": "pending",
        "attempts": 0,
        "failures": [],
    }
    base.update(o)
    return base


# ---------------------------------------------------------------------------
# PROOF 1: a no-test fix is rejected by coverage
# ---------------------------------------------------------------------------


def test_proof_1_coverage_rejects_untested_fix():
    """PROOF 1: a no-test fix is rejected by coverage (changed line not executed)."""
    deps = base_deps({
        "run_gate": lambda cmd, cwd: {
            "passed": True,
            "output": "ok",
            "infra_error": False,
            "coverage": {"src/x.py": {99}},  # line 11 NOT in executed set
        },
    })
    r = run_item(
        item(),
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["src/x.py"],
        max_attempts=1,
    )
    assert r["status"] != "done"
    assert r["failures"][0]["coverage_ok"] is False


# ---------------------------------------------------------------------------
# PROOF 2: a signature-identical repeat escalates, not burns max attempts
# ---------------------------------------------------------------------------


def test_proof_2_repeat_failure_escalates_early():
    """PROOF 2: a signature-identical repeat escalates before reaching maxAttempts."""
    deps = base_deps({
        "run_gate": lambda cmd, cwd: {
            "passed": False,
            "output": "AssertionError: nope",
            "infra_error": False,
        },
    })
    it = item()
    # maxAttempts=5 but 2nd identical failure must abandon early
    r = run_item(
        it,
        deps=deps,
        state={"items": {}},
        gate_cmd="false",
        allow=["src/x.py"],
        max_attempts=5,
    )
    assert r["status"] == "pending"

    r = run_item(
        it,
        deps=deps,
        state={"items": {}},
        gate_cmd="false",
        allow=["src/x.py"],
        max_attempts=5,
    )
    assert r["status"] == "abandoned"
    assert r["attempts"] == 2  # escalated early, did not reach 5


# ---------------------------------------------------------------------------
# PROOF 3: budget halts mid-queue after one item and checkpoints
# ---------------------------------------------------------------------------


def test_proof_3_budget_halts_mid_queue():
    """PROOF 3: budget halts mid-queue after one item and checkpoints."""
    committed = [0]
    persisted = [False]

    def commit_fn(cwd, msg):
        committed[0] += 1

    def persist_fn(state):
        persisted[0] = True

    deps = base_deps({
        "budget": {"ok": lambda: committed[0] < 1},
        "git": {
            "diff": lambda cwd: _DIFF,
            "commit": commit_fn,
            "restore": lambda cwd: None,
            "head": lambda cwd: "sha1",
        },
        "persist_state": persist_fn,
    })

    queue = [item({"id": "q1"}), item({"id": "q2"})]
    run_queue(
        queue,
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["src/x.py"],
        max_attempts=1,
    )

    assert queue[0]["status"] == "done"     # first item completed (one commit)
    assert queue[1]["status"] == "pending"  # budget halted before the second
    assert queue[1]["attempts"] == 0        # q2 was never touched
    assert persisted[0] is True             # checkpoint written


# ---------------------------------------------------------------------------
# PROOF 4: resume skips an already-done item; reconcile handles a crash-commit
# ---------------------------------------------------------------------------


def test_proof_4_resume_skips_done_item():
    """PROOF 4: resume skips an already-done item; only pending items are processed."""
    state = {"items": {}}
    mark_done(state, {"id": "q1"}, "sha-q1")  # q1 committed + marked in a prior run

    ran = []

    def implementer(it, prompt):
        ran.append(it["id"])
        return {"ok": True}

    deps = base_deps({"implementer": implementer})

    queue = [item({"id": "q1"}), item({"id": "q2"})]
    run_queue(
        queue,
        deps=deps,
        state=state,
        gate_cmd="true",
        allow=["src/x.py"],
        max_attempts=1,
    )

    assert ran == ["q2"]  # q1 skipped on resume, only q2 processed


# ---------------------------------------------------------------------------
# PROOF 5: a green gate with NO coverage map halts the run AND restores the tree (§7)
# ---------------------------------------------------------------------------


def test_proof_5_no_coverage_map_halts_and_restores():
    """PROOF 5: green gate with no coverage map → blocked-coverage-config + §7 restore."""
    restored = [0]

    def restore_fn(cwd):
        restored[0] += 1

    deps = base_deps({
        "run_gate": lambda cmd, cwd: {
            "passed": True,
            "output": "ok",
            "infra_error": False,
            # no 'coverage' key → CONFIG error
        },
        "git": {
            "diff": lambda cwd: _DIFF,
            "commit": lambda cwd, msg: None,
            "restore": restore_fn,
            "head": lambda cwd: "sha1",
        },
    })

    r = run_item(
        item(),
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["src/x.py"],
        max_attempts=1,
    )

    assert r["status"] == "blocked-coverage-config"
    assert restored[0] == 1  # §7: non-commit path reverted the working tree


# ---------------------------------------------------------------------------
# PROOF 6: a coverage rejection is fed back into the retry prompt, covering retry commits
# ---------------------------------------------------------------------------


def test_proof_6_coverage_feedback_fed_to_retry_and_commits():
    """PROOF 6: coverage rejection is fed back into retry prompt; covering retry commits."""
    attempt = [0]
    saw_coverage_feedback = [False]

    def implementer(it, prompt):
        attempt[0] += 1
        if "Coverage gap" in prompt or "coverage gap" in prompt.lower():
            saw_coverage_feedback[0] = True
        return {"ok": True}

    def run_gate(cmd, cwd):
        # attempt 1: line 11 NOT executed; attempt 2+: line 11 executed
        executed = {11} if attempt[0] >= 2 else {99}
        return {
            "passed": True,
            "output": "ok",
            "infra_error": False,
            "coverage": {"src/x.py": executed},
        }

    deps = base_deps({
        "implementer": implementer,
        "run_gate": run_gate,
    })

    it = item()
    r = run_item(
        it,
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["src/x.py"],
        max_attempts=3,
    )
    assert r["status"] == "pending"             # attempt 1 rejected by coverage
    assert r["failures"][0]["coverage_ok"] is False

    r = run_item(
        it,
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["src/x.py"],
        max_attempts=3,
    )
    assert saw_coverage_feedback[0] is True     # retry prompt named the uncovered lines
    assert r["status"] == "done"                # the covering retry commits
