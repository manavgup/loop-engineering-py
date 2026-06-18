"""
Faithful pytest port of implementer.test.mjs.
All tests are synchronous plain-def; no async/await.
"""
import os
import tempfile

from backlog_grinder.implementer import make_shell_implementer, make_shell_verifier


def test_shell_implementer_runs_command_and_writes_env():
    """make_shell_implementer runs the shell command with item+prompt via env vars."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "out.txt")
        # Write $BG_ITEM_TITLE to a file — proves the env var was passed correctly.
        impl = make_shell_implementer(f'printf "fixed:$BG_ITEM_TITLE" > {out_file}')
        result = impl(
            {"id": "i1", "title": "X", "path": "a", "fix": "do",
             "status": "open", "attempts": 0, "failures": []},
            "PROMPT",
        )
        assert result["ok"] is True
        with open(out_file) as fh:
            assert fh.read() == "fixed:X"


def test_shell_implementer_passes_all_env_vars():
    """make_shell_implementer exposes BG_ITEM_ID, BG_ITEM_PATH, BG_ITEM_FIX, BG_PROMPT."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "env.txt")
        cmd = (
            f'printf "%s|%s|%s|%s" '
            f'"$BG_ITEM_ID" "$BG_ITEM_PATH" "$BG_ITEM_FIX" "$BG_PROMPT" > {out_file}'
        )
        impl = make_shell_implementer(cmd)
        impl(
            {"id": "myid", "title": "T", "path": "src/foo.py", "fix": "rm it",
             "status": "open", "attempts": 0, "failures": []},
            "DO IT",
        )
        with open(out_file) as fh:
            content = fh.read()
        assert content == "myid|src/foo.py|rm it|DO IT"


def test_default_verifier_no_command_approves():
    """make_shell_verifier(None) defaults to APPROVE without running anything."""
    v = make_shell_verifier(None)
    result = v({"id": "i1"}, "diff text", [])
    assert result["verdict"] == "APPROVE"
    # Reason string must be present and non-empty (explains that hard checks are the gate).
    assert len(result["reasons"]) > 0


def test_shell_verifier_exit_0_approves():
    """make_shell_verifier: command that exits 0 returns verdict APPROVE."""
    # Write a non-empty diff to $BG_DIFF_FILE then grep for content — exits 0.
    v = make_shell_verifier('grep -q . "$BG_DIFF_FILE"')
    result = v({"id": "i"}, "some diff", [])
    assert result["verdict"] == "APPROVE"
    assert result["reasons"] == []


def test_shell_verifier_nonzero_rejects_with_output():
    """make_shell_verifier: command that exits non-zero returns verdict REJECT with its output."""
    v = make_shell_verifier("echo nope; exit 1")
    result = v({"id": "i"}, "d", [])
    assert result["verdict"] == "REJECT"
    combined = " ".join(result["reasons"])
    assert "nope" in combined


def test_shell_verifier_writes_diff_to_temp_file():
    """make_shell_verifier writes the staged diff to $BG_DIFF_FILE before running the command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        captured = os.path.join(tmpdir, "captured.patch")
        # Copy $BG_DIFF_FILE to a path we control so we can assert its contents.
        v = make_shell_verifier(f'cp "$BG_DIFF_FILE" {captured}')
        v({"id": "x"}, "patch content here", [])
        with open(captured) as fh:
            assert fh.read() == "patch content here"


def test_shell_verifier_cleans_up_temp_file():
    """make_shell_verifier removes its temp directory after the command finishes."""

    def capture_diff_path_cmd(tmpdir_holder):
        # Emit the diff file path to stdout, which we collect via a side-channel file.
        out = os.path.join(tmpdir_holder, "diff_path.txt")
        return f'echo "$BG_DIFF_FILE" > {out}', out

    with tempfile.TemporaryDirectory() as holder:
        cmd, out = capture_diff_path_cmd(holder)
        v = make_shell_verifier(cmd)
        v({"id": "x"}, "data", [])
        with open(out) as fh:
            diff_file = fh.read().strip()
        # The temp directory that contained diff_file must have been removed.
        assert not os.path.exists(os.path.dirname(diff_file))


def test_shell_verifier_passes_warnings_as_env():
    """make_shell_verifier exposes warnings as BG_WARNINGS (newline-joined) in env."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "warn.txt")
        v = make_shell_verifier(f'printf "%s" "$BG_WARNINGS" > {out_file}')
        v({"id": "x"}, "d", ["warn-a", "warn-b"])
        with open(out_file) as fh:
            content = fh.read()
        assert "warn-a" in content
        assert "warn-b" in content
