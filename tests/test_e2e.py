"""Synthetic E2E: guards block cheats on a real temp git repo.

End-to-end tests for the harness on a real temp git repo.

Tests run_item (the inner driver loop) directly with injected deps, so they
exercise the guards/gate/commit pipeline without needing a real implementer or
a full run_grind orchestration.

Python-world adaptations
------------------------
* All async callables in the JS deps dict become plain synchronous callables
  (no async/await anywhere in the port).

* The JS ``runGate`` dep returned ``{ passed, output, coverage }``; the
  Python equivalent returns ``{"passed": ..., "output": ..., "coverage": ...}``.
  The driver accesses keys by name so the dict shape is equivalent.

* ``head`` key on the git dep (required by the v2 driver) is included for
  parity with the JS fixture; the Python driver calls git["head"](cwd).

* ``git_rm`` (the cheat in test 2) uses subprocess so it operates on the real
  temp repo driven via subprocess.

* Coverage for test 1 is expressed as a plain Python dict mapping filename
  to a set of hit line numbers — identical shape to the JS ``Map`` equivalent
  (the coverage adapter returns the same shape).

* For the "no-test change rejected by coverage-of-change" assertion (test 1):
  the JS original checked that passing a coverage map with the changed line
  present leads to a commit.  The Python port asserts the same intent via
  the run_item return status and the git log.

* Guard violation text patterns mirror the JS ``assert.match`` regexes:
  - deleted test → r"deleted.*test" (case-insensitive)
  - out-of-allowlist file → r"allowlist" (case-insensitive)
"""

import re
import subprocess

from backlog_grinder.driver import run_item

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def git(cwd: str, *args: str) -> str:
    """Run a git command synchronously and return decoded stdout."""
    return subprocess.check_output(
        ["git", *args], cwd=cwd, encoding="utf-8", stderr=subprocess.STDOUT
    )


# ---------------------------------------------------------------------------
# Test 1 — stub implementer fixes a file, real gate passes, driver commits
# ---------------------------------------------------------------------------


def test_stub_implementer_fixes_file_driver_commits(tmp_path):
    """Stub implementer fixes a file, real gate passes, driver commits.

    Faithful port of:
      test('E2E: stub implementer fixes a file, real gate passes, driver commits')
    """
    d = str(tmp_path)
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t.t")
    git(d, "config", "user.name", "t")

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    # Broken source: gate is a check script that requires VALUE == 2.
    (src_dir / "x.py").write_text("VALUE = 1\n")

    # check.py: exits 0 iff VALUE == 2.
    (tmp_path / "check.py").write_text(
        "from src.x import VALUE; import sys; sys.exit(0 if VALUE == 2 else 1)\n"
    )
    # Make src importable from the tmp_path root.
    (src_dir / "__init__.py").write_text("")
    # Python writes __pycache__/*.pyc when the gate runs; a real repo ignores them
    # so they never pollute the staged diff the scope guards inspect.
    (tmp_path / ".gitignore").write_text("__pycache__/\n*.pyc\n")

    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "init")

    item = {
        "id": "e1",
        "title": "set VALUE to 2",
        "path": "src/x.py:1",
        "fix": "VALUE = 2",
        "status": "pending",
        "attempts": 0,
        "failures": [],
    }

    def implementer(item, prompt):
        (src_dir / "x.py").write_text("VALUE = 2\n")
        return {"ok": True}

    def verifier(item, diff, warnings):
        return {"verdict": "APPROVE", "reasons": []}

    def run_gate(cmd, cwd):
        # Green gate must carry a coverage map; the changed line (src/x.py:1) is covered.
        try:
            subprocess.check_call(
                ["python3", "check.py"],
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"passed": True, "output": "ok", "coverage": {"src/x.py": {1}}}
        except subprocess.CalledProcessError as exc:
            return {"passed": False, "output": str(exc)}

    deps = {
        "implementer": implementer,
        "verifier": verifier,
        "run_gate": run_gate,
        "git": {
            # Canonical diff: stage EVERYTHING (incl. untracked) then diff the index,
            # so guards see exactly what the commit will include.
            # ``git diff HEAD`` alone misses untracked adds.
            "diff": lambda cwd: (git(cwd, "add", "-A"), git(cwd, "diff", "--cached", "HEAD"))[1],
            "commit": lambda cwd, msg: (git(cwd, "add", "-A"), git(cwd, "commit", "-q", "-m", msg)),
            "head": lambda cwd: git(cwd, "rev-parse", "HEAD").strip(),
            # §7 git safety invariant: reset to last-good-commit AND clean untracked.
            "restore": lambda cwd: (
                git(cwd, "reset", "-q", "--hard", "HEAD"),
                git(cwd, "clean", "-fdq"),
            ),
        },
    }

    os.chdir(d)
    r = run_item(
        item,
        deps=deps,
        state={"items": {}},
        gate_cmd="python3 check.py",
        allow=["src/x.py"],
        deny=[],
        max_attempts=2,
    )

    assert r["status"] == "done"
    assert "VALUE = 2" in (src_dir / "x.py").read_text()
    assert "set VALUE to 2" in git(d, "log", "--oneline")


# Need os for chdir calls above and below.
import os  # noqa: E402  (placed here to keep the import at module scope)

# ---------------------------------------------------------------------------
# Test 2 — stub implementer that cheats (deletes the test) is reverted by guards
# ---------------------------------------------------------------------------


def test_cheat_deletes_test_is_reverted_by_guards(tmp_path):
    """Stub implementer that cheats (deletes the test) is reverted by guards.

    Faithful port of:
      test('E2E: stub implementer that cheats (deletes the test) is reverted by guards')

    The verifier approves; the guards must catch the deletion regardless.
    Guard violation message must match r"deleted.*test" (case-insensitive).
    """
    d = str(tmp_path)
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t.t")
    git(d, "config", "user.name", "t")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_x.py").write_text("def test_x():\n    assert False\n")
    (tmp_path / ".gitignore").write_text("__pycache__/\n*.pyc\n")

    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "init")

    item = {
        "id": "e2",
        "title": "make tests pass",
        "path": "tests/test_x.py:1",
        "status": "pending",
        "attempts": 0,
        "failures": [],
    }

    def implementer(item, prompt):
        # Cheat: delete the test file so the gate goes green vacuously.
        subprocess.check_call(["git", "rm", "-q", "tests/test_x.py"], cwd=d)
        return {"ok": True}

    def verifier(item, diff, warnings):
        # Verifier would approve; guards must catch the cheat.
        return {"verdict": "APPROVE", "reasons": []}

    def run_gate(cmd, cwd):
        return {"passed": True, "output": "no tests, vacuously green", "coverage": {}}

    deps = {
        "implementer": implementer,
        "verifier": verifier,
        "run_gate": run_gate,
        "git": {
            # Canonical diff: identical to test 1.
            "diff": lambda cwd: (git(cwd, "add", "-A"), git(cwd, "diff", "--cached", "HEAD"))[1],
            "commit": lambda cwd, msg: (git(cwd, "add", "-A"), git(cwd, "commit", "-q", "-m", msg)),
            "head": lambda cwd: git(cwd, "rev-parse", "HEAD").strip(),
            # §7 git safety invariant: identical revert semantics everywhere.
            "restore": lambda cwd: (
                git(cwd, "reset", "-q", "--hard", "HEAD"),
                git(cwd, "clean", "-fdq"),
            ),
        },
    }

    os.chdir(d)
    r = run_item(
        item,
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["tests/"],
        deny=[],
        max_attempts=1,
    )

    # Guards must block the cheat even though gate + verifier said OK.
    assert r["status"] != "done"
    violations_text = " ".join(r["failures"][0]["guard_violations"])
    assert re.search(r"deleted.*test", violations_text, re.IGNORECASE), (
        f"Expected 'deleted.*test' in guard violations, got: {violations_text!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — implementer adds out-of-allowlist NEW file (untracked exploit) is blocked
# ---------------------------------------------------------------------------


def test_new_file_outside_allowlist_is_blocked(tmp_path):
    """Implementer adds an out-of-allowlist NEW file (the untracked exploit) is blocked.

    Faithful port of:
      test('E2E: implementer adds an out-of-allowlist NEW file (the untracked exploit) is blocked')

    The canonical diff stages untracked files so the scope guard can see them.
    Guard violation message must match r"allowlist" (case-insensitive).
    """
    d = str(tmp_path)
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t.t")
    git(d, "config", "user.name", "t")

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "x.py").write_text("VALUE = 1\n")
    (tmp_path / ".gitignore").write_text("__pycache__/\n*.pyc\n")

    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "init")

    item = {
        "id": "e3",
        "title": "fix VALUE",
        "path": "src/x.py:1",
        "status": "pending",
        "attempts": 0,
        "failures": [],
    }

    def implementer(item, prompt):
        # Cheat: create a new untracked file OUTSIDE the allowlist instead of editing in-scope.
        (tmp_path / "auth_bypass.py").write_text("GRANT_ALL = True\n")
        return {"ok": True}

    def verifier(item, diff, warnings):
        return {"verdict": "APPROVE", "reasons": []}

    def run_gate(cmd, cwd):
        return {"passed": True, "output": "ok", "infra_error": False, "coverage": {}}

    deps = {
        "implementer": implementer,
        "verifier": verifier,
        "run_gate": run_gate,
        "git": {
            # Canonical diff stages the untracked file so the guard can see it.
            "diff": lambda cwd: (git(cwd, "add", "-A"), git(cwd, "diff", "--cached", "HEAD"))[1],
            "commit": lambda cwd, msg: (git(cwd, "add", "-A"), git(cwd, "commit", "-q", "-m", msg)),
            "head": lambda cwd: git(cwd, "rev-parse", "HEAD").strip(),
            "restore": lambda cwd: (
                git(cwd, "reset", "-q", "--hard", "HEAD"),
                git(cwd, "clean", "-fdq"),
            ),
        },
    }

    os.chdir(d)
    r = run_item(
        item,
        deps=deps,
        state={"items": {}},
        gate_cmd="true",
        allow=["src/x.py"],
        deny=[],
        max_attempts=1,
    )

    # Not committed.
    assert r["status"] != "done"
    # Caught by scope guard.
    violations_text = " ".join(r["failures"][0]["guard_violations"])
    assert re.search(r"allowlist", violations_text, re.IGNORECASE), (
        f"Expected 'allowlist' in guard violations, got: {violations_text!r}"
    )
    # Still just the 'init' commit.
    log_lines = [ln for ln in git(d, "log", "--oneline").split("\n") if ln.strip()]
    assert len(log_lines) == 1
