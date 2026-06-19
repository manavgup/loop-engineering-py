"""Tests for the L1 triage-only path (cli.triage + `--triage-only`)."""

from pathlib import Path

from backlog_grinder.cli import main, triage

BACKLOG = """### 🔴 CRITICAL (2)

#### bug-fix

- [ ] **fix the present thing**  ·  `present.py:1`  ·  _S/high_
    - _Fix:_ do it.
- [ ] **fix the gone thing**  ·  `missing.py:1`  ·  _S/high_
    - _Fix:_ do it.
"""


def _repo(tmp_path):
    (tmp_path / "present.py").write_text("x = 1\n")
    (tmp_path / "BACKLOG.md").write_text(BACKLOG)
    return tmp_path


def test_triage_computes_stale_rate_and_writes_state_md(tmp_path):
    summary = triage({"backlog_path": "BACKLOG.md", "repo_cwd": str(_repo(tmp_path))})
    assert summary["total"] == 2
    assert summary["stale"] == 1  # missing.py no longer exists
    assert summary["queueable"] == 1
    assert summary["stale_rate"] == 0.5
    assert Path(summary["state_markdown_path"]).exists()
    # Triage runs NO fixing loop: no state.json, no provenance, nothing committed.
    bg = tmp_path / ".backlog-grinder"
    assert not (bg / "state.json").exists()
    assert not (bg / "provenance.jsonl").exists()


def test_triage_only_cli_needs_no_gate_or_implementer_config(tmp_path):
    repo = _repo(tmp_path)
    # No gate_cmd / implementer_cmd / coverage supplied — triage must not require them.
    rc = main(["--triage-only", "--repo", str(repo), "--backlog", "BACKLOG.md"])
    assert rc == 0
    assert (repo / ".backlog-grinder" / "STATE.md").exists()
    assert not (repo / ".backlog-grinder" / "state.json").exists()
