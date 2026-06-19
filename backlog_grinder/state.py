# SPDX-License-Identifier: MIT
"""State persistence helpers for the backlog-grinder loop.

Location: backlog_grinder/state.py
Authors: Manav Gupta

Persist EVERY item (pending/abandoned/parked too), not just done — so a halt
or crash doesn't lose attempts/failures (§8 "feedback intact").
"""


def save_item(state: dict, item: dict) -> dict:
    """Persist item's status, attempts, failures, and commit_sha into state.

    Args:
        state: The mutable state dict whose ``items`` sub-dict is updated in place.
        item: Backlog item dict providing ``id``, ``status``, ``attempts``,
            ``failures``, and optionally ``commit_sha``.

    Returns:
        The same state dict with the item's persisted fields written under
        ``state["items"][item["id"]]``.
    """
    state["items"][item["id"]] = {
        "status": item.get("status"),
        "attempts": item.get("attempts"),
        "failures": item.get("failures"),
        "commit_sha": item.get("commit_sha"),
    }
    return state


def mark_done(state: dict, item: dict, commit_sha: str) -> dict:
    """Set item status to 'done', record commit_sha on item and state, then save.

    Args:
        state: The mutable state dict to update.
        item: Backlog item dict to mutate; its ``status`` and ``commit_sha`` are set.
        commit_sha: The git commit SHA string to record for the completed item.

    Returns:
        The updated state dict after persisting the item as done.
    """
    item["status"] = "done"
    item["commit_sha"] = commit_sha
    return save_item(state, item)


def rehydrate(queue: list, state: dict) -> list:
    """Copy persisted attempts/failures back onto freshly-parsed queue items before the loop.

    A resumed pending item must keep its retry history (the "do not repeat" feedback).
    Only restores state for non-done items so finished work is not re-queued.

    Args:
        queue: List of freshly-parsed backlog item dicts (mutated in place).
        state: Persisted state dict containing a ``items`` sub-dict keyed by item id.

    Returns:
        The same queue list with ``attempts``, ``failures``, and ``status`` restored
        from state for any item that was previously saved and is not yet done.
    """
    for item in queue:
        saved = state["items"].get(item["id"])
        if saved and saved.get("status") != "done":
            item["attempts"] = saved.get("attempts")
            item["failures"] = saved.get("failures")
            item["status"] = saved.get("status")
    return queue


def pending_items(queue: list, state: dict) -> list:
    """Return queue items that are not stale, done, or abandoned.

    Args:
        queue: List of backlog item dicts to filter.
        state: Persisted state dict containing a ``items`` sub-dict keyed by item id.

    Returns:
        A new list of item dicts whose ``stale`` flag is falsy and whose persisted
        status (if any) is neither ``"done"`` nor ``"abandoned"``.
    """
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

    Args:
        state: The mutable state dict to update if recovery is needed.
        in_flight_item: The item that was being processed when the crash occurred,
            or None if no item was in flight.
        head_sha: The current git HEAD SHA, or None if unavailable.
        last_recorded_sha: The SHA recorded at the last successful state write,
            or None if no prior write exists.

    Returns:
        The updated state dict (with the in-flight item marked done) if recovery
        was performed, or the original state dict unchanged.
    """
    advanced = in_flight_item and head_sha != last_recorded_sha
    if advanced and in_flight_item["id"] not in state["items"]:
        return mark_done(state, in_flight_item, head_sha)
