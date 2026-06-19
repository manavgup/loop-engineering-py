"""Standalone-tool E2E: run_grind drains a real backlog against a REAL temp git repo
using a shell implementer (NO model) and a REAL gate that emits coverage.
Proves the whole tool runs end to end:
  parse -> stale-check -> grind -> gate+coverage+guards -> commit ->
  STATE + provenance on disk, with honest end states.

Python-world adaptations
------------------------
* Gate command: instead of ``node --test ... --test-reporter=lcov``, we drive a
  pytest+coverage gate that writes a Cobertura XML artifact:
      python3 -m pytest test_x.py --cov=src --cov-report=xml:coverage.xml --cov-fail-under=0
  Coverage format: "cobertura", file: "coverage.xml".
  This is the idiomatic equivalent in the Python world; the same assertions
  (coverage artifact present → item committed; artifact absent → halted) are
  preserved verbatim.

* The "green gate with no coverage artifact" test uses gate_cmd "true" with
  format "cobertura" / file "coverage.xml" (never produced).  Assertion intent
  is identical to the JS original: driver must halt (blocked-coverage-config),
  not commit blind.

* ``git()`` helper is synchronous (subprocess.check_output), matching the
  synchronous style of the Python port (no async/await).

* All async operations from the JS original become plain synchronous calls.
"""

import json
import subprocess
from pathlib import Path

from backlog_grinder.cli import run_grind

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GATE = "python3 -m pytest test_x.py --cov=src --cov-report=xml:coverage.xml --cov-fail-under=0 -q"


def git(cwd: str, *args: str) -> str:
    """Run a git command synchronously and return decoded stdout."""
    return subprocess.check_output(
        ["git", *args], cwd=cwd, encoding="utf-8", stderr=subprocess.STDOUT
    )


def fixture_repo(tmp_path: Path) -> str:
    """Build a minimal git repo with a broken source file and a backlog.

    The repo structure mirrors the JS fixture:
    - src/x.py   — broken: compute() returns 1 but the test expects 2.
    - test_x.py  — pytest test that calls compute() and asserts == 2.
    - .gitignore — ignores coverage.xml and .backlog-grinder/.
    - BACKLOG.md — one critical item: make compute return 2.

    The changed line lives inside a function body that the test executes, so
    coverage-of-change gets a real hit in the XML report.
    """
    d = str(tmp_path)
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t.t")
    git(d, "config", "user.name", "t")

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Broken source: returns 1, test expects 2.
    (src_dir / "__init__.py").write_text("")
    (src_dir / "x.py").write_text("def compute():\n    return 1\n")

    # The pytest test that covers the changed line.
    (tmp_path / "test_x.py").write_text(
        "from src.x import compute\n\ndef test_compute_is_2():\n    assert compute() == 2\n"
    )

    # Gate artifact and grinder state must not pollute the diff.
    # Ignore the gate artifact, grinder state, AND Python bytecode — __pycache__/*.pyc
    # would otherwise be staged into the diff and tripped as out-of-scope by the guards.
    (tmp_path / ".gitignore").write_text(
        "coverage.xml\n.coverage\n.backlog-grinder/\n__pycache__/\n*.pyc\n"
    )

    (tmp_path / "BACKLOG.md").write_text(
        "### \U0001f534 CRITICAL (1)\n\n"
        "#### bug-fix\n\n"
        "- [ ] **make compute return 2**  ·  `src/x.py:2`  ·  _S/high_\n"
        "    - _Evidence:_ compute returns 1 but the test expects 2.\n"
        "    - _Fix:_ change the return to 2.\n"
    )

    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "init")
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_grind_fixes_real_repo_and_records_provenance(tmp_path):
    """run_grind fixes a real repo behind gate+coverage+guards and records provenance.

    Faithful port of:
      test('E2E: runGrind fixes a real repo behind gate+coverage+guards...')
    """
    d = fixture_repo(tmp_path)

    summary = run_grind(
        {
            "backlog_path": "BACKLOG.md",
            "repo_cwd": d,
            "gate_cmd": GATE,
            "coverage": {"format": "cobertura", "file": "coverage.xml"},
            # Model-agnostic implementer: a one-liner that performs the fix.
            "implementer_cmd": ("printf 'def compute():\\n    return 2\\n' > src/x.py"),
            "allow": ["src/x.py"],
            "deny": [],
            "max_attempts": 2,
            "project_name": "E2E",
        }
    )

    # End state + counts.
    assert summary["end_state"] == "complete"
    assert summary["counts"]["done"] == 1
    assert summary["counts"]["pending"] == 0

    # The real edit landed and is committed.
    assert (tmp_path / "src" / "x.py").read_text() == "def compute():\n    return 2\n"
    assert "make compute return 2" in git(d, "log", "--oneline")

    # Gate artifact and grinder state were gitignored — the commit is clean.
    show_stat = git(d, "show", "--stat", "HEAD")
    assert "coverage.xml" not in show_stat
    assert "backlog-grinder" not in show_stat

    # STATE persisted, item done.
    state = json.loads((tmp_path / ".backlog-grinder" / "state.json").read_text())
    ids = list(state["items"].keys())
    assert len(ids) == 1
    assert state["items"][ids[0]]["status"] == "done"
    assert state["items"][ids[0]]["commit_sha"]

    # Provenance: one record, coverage passed, ties to the commit.
    prov_lines = (
        (tmp_path / ".backlog-grinder" / "provenance.jsonl").read_text().strip().split("\n")
    )
    assert len(prov_lines) == 1
    rec = json.loads(prov_lines[0])
    assert rec["item_id"] == ids[0]
    assert rec["coverage_ok"] is True
    assert rec["commit_sha"]


def test_green_gate_with_no_coverage_artifact_halts(tmp_path):
    """A green gate that emits no coverage artifact must halt (blocked-coverage-config).

    Faithful port of:
      test('E2E: a green gate with no coverage artifact halts the run (config error, §5)')

    Python adaptation: gate_cmd is 'true' (vacuously green, writes nothing).
    Coverage format is 'cobertura', file is 'coverage.xml' (never produced).
    Same assertion intent as the JS original.
    """
    d = fixture_repo(tmp_path)

    summary = run_grind(
        {
            "backlog_path": "BACKLOG.md",
            "repo_cwd": d,
            "gate_cmd": "true",  # vacuously green, no coverage written
            "coverage": {"format": "cobertura", "file": "coverage.xml"},  # file never produced
            "implementer_cmd": ("printf 'def compute():\\n    return 2\\n' > src/x.py"),
            "allow": ["src/x.py"],
            "max_attempts": 1,
        }
    )

    assert summary["end_state"] == "halted"
    assert summary["counts"]["blocked"] == 1
    assert summary["counts"]["done"] == 0

    # Nothing committed beyond init; the implementer's edit was reverted (§7).
    log_lines = git(d, "log", "--oneline").strip().splitlines()
    assert len(log_lines) == 1
    assert (tmp_path / "src" / "x.py").read_text() == "def compute():\n    return 1\n"
