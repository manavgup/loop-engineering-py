"""Driver: top-level loop that runs items through implement → gate → guard → verify → commit.

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
# Module-level constants (ported verbatim from driver.mjs)
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
    """Flake-confirm (§3.4): re-run a red ONCE before trusting it."""
    result = deps["run_gate"](gate_cmd, cwd)
    if not result["passed"]:
        result = deps["run_gate"](gate_cmd, cwd)
    return result


def _fail(item, state, deps, cwd, max_attempts, *, gate_output, guard_violations,
          coverage_ok, coverage_uncovered):
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
    """Run one item through the implement→gate→guard→verify→commit cycle.

    Mutates item in place (attempts, failures, status) and persists to state.
    Returns the (mutated) item.
    """
    cwd = deps.get("cwd")
    item["attempts"] += 1

    base_prompt = f"{BASE}\n\n{item['title']}\nPath: {item['path']}\nFix: {item.get('fix', '')}"
    if item["failures"]:
        prompt = build_retry_prompt(item, base_prompt, item["failures"])
    else:
        prompt = base_prompt
    deps["implementer"](item, prompt)

    gate = _run_gate_confirmed(deps, gate_cmd, cwd)
    diff = deps["git"]["diff"](cwd)

    if not gate["passed"]:
        return _fail(item, state, deps, cwd, max_attempts, gate_output=gate["output"],
                     guard_violations=[], coverage_ok=False, coverage_uncovered=[])

    if "coverage" not in gate:
        deps["git"]["restore"](cwd)
        item["status"] = "blocked-coverage-config"
        save_item(state, item)
        return item

    guards = check_guards(diff, {"allow": allow or []})
    cov = check_coverage(diff, gate["coverage"])
    if not guards["ok"] or not cov["ok"]:
        uncovered = [f"{u['file']}:{u['line']}" for u in cov["uncovered"]]
        return _fail(item, state, deps, cwd, max_attempts, gate_output=gate["output"],
                     guard_violations=guards["violations"], coverage_ok=cov["ok"],
                     coverage_uncovered=uncovered)

    verdict = deps["verifier"](item, diff, guards["warnings"])
    if verdict["verdict"] == "APPROVE":
        deps["git"]["commit"](cwd, f"{item['id']}: {item['title']}")
        mark_done(state, item, deps["git"]["head"](cwd))
    return item


def run_queue(queue, *, deps, state=None, gate_cmd, allow=None, deny=None,
              max_attempts=3, stop_file=None):
    """Iterate pending items in queue, calling run_item on each until terminal or halted.

    Checkpoints state after every item. Halts early when the budget is exhausted.
    Returns the (mutated) queue.
    """
    budget = deps.get("budget")
    persist = deps.get("persist_state")
    for item in pending_items(queue, state):
        if budget and not budget["ok"]():
            break
        run_item(item, deps=deps, state=state, gate_cmd=gate_cmd, allow=allow,
                 deny=deny, max_attempts=max_attempts)
        if persist:
            persist(state)
    return queue
