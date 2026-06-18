"""Pytest port of git-adapter.test.mjs — faithful behavioral port, synchronous."""

import subprocess
from pathlib import Path

from backlog_grinder.git_adapter import make_git

# ---------------------------------------------------------------------------
# Helpers (mirror the JS helpers in git-adapter.test.mjs)
# ---------------------------------------------------------------------------

def _git(cwd, *args):
    """Run git with the given args in cwd; return stdout as str (strips nothing)."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _make_repo(tmp_path: Path) -> Path:
    """
    Create a minimal git repo with one tracked file and an initial commit.

    Mirrors the async `repo()` helper in the JS test:
      mkdtemp → git init → config user → write a.txt → add -A → commit 'init'
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_diff_stages_untracked_and_tracked(tmp_path):
    """
    diff() stages everything (incl. untracked) then diffs the index against HEAD,
    so guards see exactly what a commit would include (§7).
    Mirrors: 'diff stages untracked + tracked and shows them against HEAD'
    """
    repo = _make_repo(tmp_path)
    g = make_git()

    (repo / "a.txt").write_text("2\n")    # modify tracked file
    (repo / "b.txt").write_text("new\n")  # add untracked file

    d = g["diff"](repo)

    assert "a.txt" in d
    assert "b.txt" in d


def test_commit_advances_head(tmp_path):
    """
    commit() stages everything and creates a new commit; head() returns the new SHA.
    Mirrors: 'commit advances HEAD; head returns the new sha'
    """
    repo = _make_repo(tmp_path)
    g = make_git()

    before = g["head"](repo)
    (repo / "a.txt").write_text("2\n")
    g["commit"](repo, "change a")
    after = g["head"](repo)

    assert before != after
    assert "change a" in _git(repo, "log", "--oneline")


def test_restore_resets_tracked_and_removes_untracked(tmp_path):
    """
    restore() = reset --hard HEAD + clean -fd, so a rejected attempt can never
    leak files into the next item (§7 invariant).
    Mirrors: 'restore resets tracked AND removes untracked (§7)'
    """
    repo = _make_repo(tmp_path)
    g = make_git()

    (repo / "a.txt").write_text("CORRUPT\n")
    (repo / "junk.txt").write_text("leak\n")

    g["restore"](repo)

    # Tracked file must be back to its committed content
    assert _git(repo, "show", "HEAD:a.txt") == "1\n"
    # Untracked file must have been removed by clean -fd
    assert not (repo / "junk.txt").exists()
