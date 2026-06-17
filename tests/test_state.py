"""Tests for backlog_grinder.state — faithful port of state.test.mjs."""

from backlog_grinder.state import mark_done, pending_items, reconcile, rehydrate, save_item


def test_mark_done_records_sha_and_status():
    """mark_done records sha and status (write AFTER commit)."""
    s = {"items": {}}
    mark_done(s, {"id": "a1"}, "deadbeef")
    assert s["items"]["a1"]["status"] == "done"
    assert s["items"]["a1"]["commit_sha"] == "deadbeef"


def test_pending_items_skips_done_abandoned_stale_keeps_pending():
    """pending_items skips done/abandoned/stale, keeps pending."""
    s = {"items": {"a1": {"status": "done"}, "b2": {"status": "abandoned"}}}
    q = [{"id": "a1"}, {"id": "b2"}, {"id": "c3"}, {"id": "d4", "stale": True}]
    result = pending_items(q, s)
    assert [i["id"] for i in result] == ["c3"]


def test_save_item_and_rehydrate_restores_attempts_and_failures():
    """save_item persists attempts+failures; rehydrate restores them onto freshly-parsed items."""
    s = {"items": {}}
    save_item(
        s,
        {
            "id": "p1",
            "status": "pending",
            "attempts": 2,
            "failures": [{"attempt": 1}, {"attempt": 2}],
        },
    )
    # Simulates freshly-parsed queue items: no retry history yet.
    queue = [{"id": "p1"}]
    rehydrate(queue, s)
    assert queue[0]["attempts"] == 2
    assert len(queue[0]["failures"]) == 2
    assert queue[0]["status"] == "pending"


def test_reconcile_marks_in_flight_item_done_when_head_advanced():
    """reconcile marks an in-flight item done if HEAD advanced past last recorded sha."""
    s = {"items": {}, "last_good_sha": "old"}
    reconcile(s, {"id": "x9"}, "newsha", "old")  # crash between commit and marker
    assert s["items"]["x9"]["status"] == "done"
    assert s["items"]["x9"]["commit_sha"] == "newsha"
