"""Provenance (§6): every approved commit emits a machine-generated audit record
so "why did the system make this edit and what did it check" is answerable from
disk without re-running anything.

make_record builds the §6 record from the item + the run artifacts.
append_record stores it append-only (one record per commit).
The clock is injected so the timestamp is deterministic in tests.
"""


def make_record(item, opts=None, *, clock=None):
    """Build a §6 provenance audit record from an item and run artifacts.

    Returns a dict with all §6 fields in snake_case.
    """
    opts = opts or {}
    record = {}
    record["item_id"] = item.get("id")
    record["title"] = item.get("title")
    record["source_path"] = item.get("path")
    record["commit_sha"] = opts.get("commit_sha")
    record["timestamp"] = clock() if clock else None
    record["prompt_sent"] = opts.get("prompt")
    record["attempts"] = opts.get("attempts")
    record["gate_output"] = opts.get("gate_output")
    record["tests_collected"] = opts.get("tests_collected")
    record["coverage_of_change"] = opts.get("coverage")
    record["guard_results"] = opts.get("guard_results")
    record["verifier_verdict"] = opts.get("verifier_verdict")
    record["verifier_rationale"] = opts.get("verifier_rationale")
    record["final_diff"] = opts.get("final_diff")
    record["lessons_applied"] = opts.get("lessons_applied")
    return record


def append_record(store, record):
    """Return a new list with *record* appended to *store* (append-only, no mutation)."""
    return [*store, record]
