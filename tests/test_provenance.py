"""Pytest port of provenance.test.mjs — synchronous, no async/await.

§6 audit records: every approved commit emits a machine-generated record so
"why did the system make this edit and what did it check" is answerable from
disk without re-running anything.
"""
from backlog_grinder.provenance import append_record, make_record

ITEM = {"id": "a1", "title": "Fix X", "path": "backend/x.py:46"}


def test_make_record_contains_every_section6_field_for_approved_item():
    # Clock is injected so the timestamp is deterministic in tests.
    rec = make_record(
        ITEM,
        {
            "prompt": "do the fix",
            "attempts": [{"attempt": 1}],
            "gate_output": "ok",
            "tests_collected": 12,
            "coverage": {"ok": True},
            "guard_results": {"coverage": True, "scope": True, "tamper_warnings": ["w"]},
            "verifier_verdict": "APPROVE",
            "verifier_rationale": ["looks good"],
            "final_diff": "diff...",
            "commit_sha": "abc123",
            "lessons_applied": ["l1"],
        },
        clock=lambda: "2026-06-16T00:00:00Z",
    )
    assert rec["item_id"] == "a1"
    assert rec["title"] == "Fix X"
    assert rec["source_path"] == "backend/x.py:46"
    assert rec["commit_sha"] == "abc123"
    assert rec["timestamp"] == "2026-06-16T00:00:00Z"
    assert rec["prompt_sent"] == "do the fix"
    assert rec["attempts"] == [{"attempt": 1}]
    assert rec["gate_output"] == "ok"
    assert rec["tests_collected"] == 12
    assert rec["coverage_of_change"] == {"ok": True}
    assert rec["guard_results"] == {"coverage": True, "scope": True, "tamper_warnings": ["w"]}
    assert rec["verifier_verdict"] == "APPROVE"
    assert rec["verifier_rationale"] == ["looks good"]
    assert rec["final_diff"] == "diff..."
    assert rec["lessons_applied"] == ["l1"]


def test_append_record_stores_one_record_per_commit_append_only():
    # append_record is a pure functional accumulator: each call returns a new
    # list so the store is effectively append-only (no mutation, no truncation).
    store = []
    store = append_record(store, make_record(ITEM, {"commit_sha": "s1"}, clock=lambda: "t"))
    store = append_record(store, make_record(ITEM, {"commit_sha": "s2"}, clock=lambda: "t"))
    assert len(store) == 2
    assert store[0]["commit_sha"] == "s1"
    assert store[1]["commit_sha"] == "s2"
