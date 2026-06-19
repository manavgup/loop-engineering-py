# SPDX-License-Identifier: MIT
"""Top-level loop that runs items through implement → gate → guard → verify → commit.

Location: backlog_grinder/driver.py
Authors: Manav Gupta

Orchestrates the full per-item retry cycle and the outer queue drain.  Pure
business logic: all I/O (git, gate, implementer, verifier, provenance) is
injected via the ``deps`` dict so the core is independently testable.

Public API
----------
run_item(item, *, deps, state, gate_cmd, allow, deny, max_attempts) -> item
run_queue(queue, *, deps, state, gate_cmd, allow, deny, max_attempts, stop_file) -> queue

Module constants
----------------
BASE      : str   — base prompt text injected at the start of every implementer call.
TERMINAL  : list  — statuses that terminate the inner retry loop for an item.
"""

from .coverage import check_coverage
from .feedback import build_retry_prompt, is_repeated_failure
from .guards import check_guards
from .state import mark_done, pending_items, save_item

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

BASE = (
    "Fix ONLY this finding with the smallest diff. Do not refactor unrelated code, "
    "delete or weaken tests, or touch denylist paths. If your change alters behavior, "
    "ensure a test executes the changed lines — add or extend a test if none does; "
    "a behavior change with no covering test will be rejected. Stop when done."
)

TERMINAL = ["done", "abandoned", "parked-infra", "parked-flaky", "blocked-coverage-config"]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _run_gate_confirmed(deps, gate_cmd, cwd):
    """Flake-confirm (§3.4): re-run a red gate ONCE before trusting it."""
    result = deps["run_gate"](gate_cmd, cwd)
    if not result["passed"]:
        result = deps["run_gate"](gate_cmd, cwd)
    return result


def _fail(
    item,
    state,
    deps,
    cwd,
    max_attempts,
    *,
    gate_output,
    guard_violations,
    coverage_ok,
    coverage_uncovered,
):
    """Record a rejection, restore the tree, and set status (abandon or stay pending)."""
    record = {
        "attempt": item["attempts"],
        "gate_output": gate_output,
        "guard_violations": guard_violations,
        "coverage_ok": coverage_ok,
        "coverage_uncovered": coverage_uncovered,
    }
    repeated = is_repeated_failure(item["failures"], record)
    item["failures"].append(record)
    deps["git"]["restore"](cwd)
    if repeated or item["attempts"] >= max_attempts:
        item["status"] = "abandoned"
    else:
        item["status"] = "pending"
    save_item(state, item)
    return item


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_item(item, *, deps, state, gate_cmd, allow=None, deny=None, max_attempts=3):
    """Run one backlog item through the implement → gate → guard → verify → commit cycle.

    Calls the injected implementer, runs the gate (with flake-confirmation), checks
    guard rules and coverage, then calls the verifier.  On approval the change is
    committed and the item is marked done; on failure the tree is restored and the
    item is either left pending (for retry) or abandoned.

    Args:
        item: Backlog item dict (mutated in place: ``attempts``, ``failures``,
            ``status``, ``commit_sha``).
        deps: Dict of injected callables and sub-dicts:
            ``implementer`` — callable(item, prompt) that edits the working tree;
            ``verifier`` — callable(item, diff, warnings) -> verdict dict;
            ``run_gate`` — callable(cmd, cwd) -> gate result dict;
            ``git`` — dict with ``diff``, ``commit``, ``head``, ``restore`` callables;
            ``provenance`` — optional callable(record) to append audit entry;
            ``budget`` — optional dict with ``ok()`` callable;
            ``persist_state`` — optional callable(state) to checkpoint state;
            ``cwd`` — optional str working-directory path.
        state: Mutable state dict managed by the persist module.
        gate_cmd: Shell command (str or list) to run the test suite.
        allow: Optional list of path prefixes the diff is allowed to touch.
            When non-empty, any file outside the list is a hard violation.
        deny: Optional list of path prefixes that must not be touched (advisory
            to the verifier; hard enforcement is done by the allowlist).
        max_attempts: Maximum number of attempts before an item is abandoned.

    Returns:
        The mutated ``item`` dict with updated ``status``, ``attempts``, and
        ``failures``.
    """
    cwd = deps.get("cwd")
    # Freshly-parsed backlog items have no attempts/failures yet — initialize (§8).
    item["attempts"] = item.get("attempts", 0) + 1
    item["failures"] = item.get("failures") or []

    base_prompt = f"{BASE}\n\n{item['title']}\nPath: {item['path']}\nFix: {item.get('fix', '')}"
    if item["failures"]:
        prompt = build_retry_prompt(item, base_prompt, item["failures"])
    else:
        prompt = base_prompt
    deps["implementer"](item, prompt)

    gate = _run_gate_confirmed(deps, gate_cmd, cwd)
    diff = deps["git"]["diff"](cwd)

    if not gate["passed"]:
        return _fail(
            item,
            state,
            deps,
            cwd,
            max_attempts,
            gate_output=gate["output"],
            guard_violations=[],
            coverage_ok=False,
            coverage_uncovered=[],
        )

    if "coverage" not in gate:
        deps["git"]["restore"](cwd)
        item["status"] = "blocked-coverage-config"
        save_item(state, item)
        return item

    guards = check_guards(diff, {"allow": allow or [], "deny": deny or []})
    cov = check_coverage(diff, gate["coverage"])
    if not guards["ok"] or not cov["ok"]:
        uncovered = [f"{u['file']}:{u['line']}" for u in cov["uncovered"]]
        return _fail(
            item,
            state,
            deps,
            cwd,
            max_attempts,
            gate_output=gate["output"],
            guard_violations=guards["violations"],
            coverage_ok=cov["ok"],
            coverage_uncovered=uncovered,
        )

    verdict = deps["verifier"](item, diff, guards["warnings"])
    if verdict["verdict"] == "APPROVE":
        deps["git"]["commit"](cwd, f"{item['id']}: {item['title']}")
        sha = deps["git"]["head"](cwd)
        # Provenance BEFORE the done marker (§6/§8): a done marker must imply audit-on-disk.
        if deps.get("provenance"):
            deps["provenance"](
                {
                    "item_id": item["id"],
                    "title": item["title"],
                    "commit_sha": sha,
                    "prompt_sent": prompt,
                    "attempts": item["failures"],
                    "gate_output": gate["output"],
                    "coverage_ok": cov["ok"],
                    "guard_results": {
                        "violations": guards["violations"],
                        "warnings": guards["warnings"],
                    },
                    "verifier_verdict": verdict["verdict"],
                    "verifier_rationale": verdict["reasons"],
                    "final_diff": diff,
                    "lessons_applied": [],
                }
            )
        mark_done(state, item, sha)
    return item


def run_queue(
    queue, *, deps, state=None, gate_cmd, allow=None, deny=None, max_attempts=3, stop_file=None
):
    """Drain the pending items in a queue by calling ``run_item`` on each in turn.

    Iterates items returned by ``pending_items`` (skipping stale, done, and
    abandoned entries).  Halts early when the injected budget is exhausted.
    Checkpoints state to disk after every item if ``deps['persist_state']`` is
    provided.

    Args:
        queue: List of backlog item dicts (mutated in place by ``run_item``).
        deps: Dict of injected callables — same shape as ``run_item``'s ``deps``.
            ``budget`` — optional dict with ``ok()`` callable; absence means unlimited.
            ``persist_state`` — optional callable(state) called after each item.
        state: Mutable state dict managed by the persist module.
        gate_cmd: Shell command (str or list) passed through to ``run_item``.
        allow: Optional list of path prefixes forwarded to ``run_item``.
        deny: Optional list of path prefixes forwarded to ``run_item``.
        max_attempts: Maximum attempts per item before abandonment.
        stop_file: Reserved parameter (not yet active in the pure driver).

    Returns:
        The (mutated) ``queue`` list after processing all pending items or
        exhausting the budget.
    """
    budget = deps.get("budget")
    persist = deps.get("persist_state")
    for item in pending_items(queue, state):
        if budget and not budget["ok"]():
            break
        run_item(
            item,
            deps=deps,
            state=state,
            gate_cmd=gate_cmd,
            allow=allow,
            deny=deny,
            max_attempts=max_attempts,
        )
        if persist:
            persist(state)
    return queue
