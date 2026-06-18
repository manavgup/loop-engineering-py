"""
Tests for backlog_grinder.triage.
All tests are synchronous plain-def; no async/await.
"""
from backlog_grinder.triage import summarize, to_state_markdown

ITEMS = [
    {
        "id": "a1", "title": "X", "path": "backend/a.py:1",
        "effort": "S", "severity": "critical", "category": "bug-fix",
        "checked": False, "stale": False,
    },
    {
        "id": "b2", "title": "Y", "path": "backend/auth/b.py:2",
        "effort": "M", "severity": "critical", "category": "security",
        "checked": False, "stale": True,
    },
    {
        "id": "c3", "title": "Z", "path": "backend/c.py:3",
        "effort": "L", "severity": "high", "category": "bug-fix",
        "checked": False, "stale": False,
    },
    {
        "id": "e5", "title": "W", "path": "backend/auth/login.py:9",
        "effort": "S", "severity": "high", "category": "security",
        "checked": False, "stale": False,
    },
]


def test_summarize_groups_by_severity_and_category_and_counts_stale():
    s = summarize(ITEMS)
    assert s["total"] == 4
    assert s["stale"] == 1
    assert s["queueable"] == 3
    assert s["by_severity"]["critical"] == 2
    assert s["by_category"]["bug-fix"] == 2


def test_to_state_markdown_queues_non_stale_parks_stale_flags_denylist():
    md = to_state_markdown(ITEMS, {"project_name": "T", "deny": ["auth"]})

    # Header uses injected project name
    assert "# Loop State — T" in md

    # Non-stale item a1 appears in the queue
    assert "a1 — X" in md

    # Stale item b2 must NOT appear as a checkbox queue entry
    assert "- [ ] b2 — Y" not in md

    # Stale section heading is present
    assert "Stale / needs human re-validation" in md

    # b2 still appears in the stale section (not silently dropped)
    assert "b2 — Y" in md

    # Non-stale auth item e5 is queued AND denylist-flagged
    assert "e5 — W [DENYLIST: human gate]" in md
