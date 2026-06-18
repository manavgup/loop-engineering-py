"""Tests for backlog_grinder.persist."""

import json

from backlog_grinder.persist import (
    load_state,
    make_provenance_writer,
    make_state_persister,
)


def test_load_state_returns_empty_shape_when_file_is_missing(tmp_path):
    """load_state on a non-existent path returns the empty canonical shape."""
    missing = tmp_path / "nope.json"
    assert load_state(missing) == {"items": {}}


def test_load_state_returns_parsed_json_when_file_exists(tmp_path):
    """load_state parses an existing JSON file and returns it as a dict."""
    state_file = tmp_path / "state.json"
    data = {
        "items": {"a1": {"status": "done", "attempts": 1, "failures": [], "commit_sha": "s"}},
        "last_good_sha": "s",
    }
    state_file.write_text(json.dumps(data), encoding="utf-8")

    loaded = load_state(state_file)
    assert loaded["items"]["a1"]["status"] == "done"
    assert loaded["last_good_sha"] == "s"


def test_state_persister_round_trips_through_disk(tmp_path):
    """make_state_persister writes state.json; load_state reads it back faithfully."""
    p = tmp_path / "state.json"
    save = make_state_persister(p)

    state = {
        "items": {"a1": {"status": "done", "attempts": 1, "failures": [], "commit_sha": "s"}},
        "last_good_sha": "s",
    }
    save(state)

    loaded = load_state(p)
    assert loaded["items"]["a1"]["status"] == "done"
    assert loaded["last_good_sha"] == "s"


def test_state_persister_creates_parent_dirs(tmp_path):
    """make_state_persister creates intermediate directories if they don't exist."""
    p = tmp_path / "deep" / "nested" / "state.json"
    save = make_state_persister(p)
    save({"items": {}})
    assert p.exists()


def test_provenance_writer_appends_one_jsonl_record_per_commit(tmp_path):
    """make_provenance_writer appends one JSON line per call (JSONL format)."""
    p = tmp_path / "provenance.jsonl"
    write = make_provenance_writer(p)

    # Provenance is append-only JSONL so the audit trail is on disk and never lost.
    write({"item_id": "a1", "commit_sha": "s1"})
    write({"item_id": "a2", "commit_sha": "s2"})

    lines = p.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["commit_sha"] == "s1"
    assert json.loads(lines[1])["item_id"] == "a2"


def test_provenance_writer_creates_parent_dirs(tmp_path):
    """make_provenance_writer creates intermediate directories if they don't exist."""
    p = tmp_path / "deep" / "nested" / "provenance.jsonl"
    write = make_provenance_writer(p)
    write({"item_id": "x", "commit_sha": "abc"})
    assert p.exists()
