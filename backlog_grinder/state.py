"""State persistence helpers for the backlog-grinder loop.

Persist EVERY item (pending/abandoned/parked too), not just done — so a halt
or crash doesn't lose attempts/failures (§8 "feedback intact").
"""


def save_item(state: dict, item: dict) -> dict:
    """Persist item's status, attempts, failures, and commit_sha into state."""
    state["items"][item["id"]] = {
        "status": item.get("status"),
        "attempts": item.get("attempts"),
        "failures": item.get("failures"),
        "commit_sha": item.get("commit_sha"),
    }
    return state


def mark_done(state: dict, item: dict, commit_sha: str) -> dict:
    """Set item status to 'done', record commit_sha on item and state, then save."""
    item["status"] = "done"
    item["commit_sha"] = commit_sha
    return save_item(state, item)


def rehydrate(queue: list, state: dict) -> list:
    """Copy persisted attempts/failures back onto freshly-parsed queue items before the loop.

    A resumed pending item must keep its retry history (the "do not repeat" feedback).
    Only restores state for non-done items so finished work is not re-queued.
    """
    for item in queue:
        saved = state["items"].get(item["id"])
        if saved and saved.get("status") != "done":
            item["attempts"] = saved.get("attempts")
            item["failures"] = saved.get("failures")
            item["status"] = saved.get("status")
    return queue


def pending_items(queue: list, state: dict) -> list:
    """Return queue items that are not stale, done, or abandoned."""
    result = []
    for item in queue:
        if item.get("stale"):
            continue
        saved = state["items"].get(item["id"])
        if saved and saved.get("status") in ("done", "abandoned"):
            continue
        result.append(item)
    return result


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
    advanced = in_flight_item and head_sha != last_recorded_sha
    if advanced and in_flight_item["id"] not in state["items"]:
        return mark_done(state, in_flight_item, head_sha)
