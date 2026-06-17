"""State persistence helpers for the backlog-grinder loop.

Persist EVERY item (pending/abandoned/parked too), not just done — so a halt
or crash doesn't lose attempts/failures (§8 "feedback intact").
"""


def save_item(state: dict, item: dict) -> dict:
    """Persist item's status, attempts, failures, and commit_sha into state."""
    raise NotImplementedError


def mark_done(state: dict, item: dict, commit_sha: str) -> dict:
    """Set item status to 'done', record commit_sha on item and state, then save."""
    raise NotImplementedError


def rehydrate(queue: list, state: dict) -> list:
    """Copy persisted attempts/failures back onto freshly-parsed queue items before the loop.

    A resumed pending item must keep its retry history (the "do not repeat" feedback).
    Only restores state for non-done items so finished work is not re-queued.
    """
    raise NotImplementedError


def pending_items(queue: list, state: dict) -> list:
    """Return queue items that are not stale, done, or abandoned."""
    raise NotImplementedError


def reconcile(
    state: dict,
    in_flight_item: dict | None,
    head_sha: str | None,
    last_recorded_sha: str | None,
) -> dict:
    """Idempotent crash recovery: if HEAD moved but no 'done' was written, mark it done.

    Crash between commit and marker: HEAD moved but no 'done' written.
    Only acts when in_flight_item exists, head_sha differs from last_recorded_sha,
    and the item has not already been recorded in state.
    """
    raise NotImplementedError
