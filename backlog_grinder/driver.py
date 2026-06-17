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


def _with_lessons(prompt, lessons):
    """Prepend lesson bullets to prompt when lessons are present."""
    if not lessons:
        return prompt
    bullets = "\n".join(f"- {lesson['pattern']} → {lesson['fix']}" for lesson in lessons)
    return f"{prompt}\n\nLessons from earlier items:\n{bullets}"


def _run_gate_confirmed(deps, gate_cmd, cwd):
    """Flake-confirm (§3.4): re-run a red ONCE before trusting it.

    Returns gate result dict augmented with a 'kind' key in
    {'infra', 'green', 'flaky', 'red'}.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_item(item, *, deps, state, gate_cmd, allow=None, deny=None, max_attempts=3):
    """Run one item through the implement→gate→guard→verify→commit cycle.

    Mutates item in place (attempts, failures, status) and persists to state.
    Returns the (mutated) item.
    """
    raise NotImplementedError


def run_queue(queue, *, deps, state=None, gate_cmd, allow=None, deny=None,
              max_attempts=3, stop_file=None):
    """Iterate pending items in queue, calling run_item on each until terminal or halted.

    Checkpoints state after every item. Halts early on budget exhaustion,
    stop-file presence, or a blocked-coverage-config result.
    Returns the (mutated) queue.
    """
    raise NotImplementedError
