"""
Pluggable, model-agnostic implementer and verifier factories.

The implementer runs a configured shell command that is expected to edit the
working tree to fix the item.  The item + prompt are exposed via env so ANY
tool (a script, sed, or an LLM CLI like ``claude -p "$BG_PROMPT"``) drops in
without the harness hardcoding a model.

The verifier is optional: with no command it defaults to APPROVE because the
hybrid checker's hard checks (gate ∧ coverage ∧ guards) already gate the
commit.  A configured command sees the diff via ``$BG_DIFF_FILE`` and guard
warnings via ``$BG_WARNINGS``; exit 0 → APPROVE, non-zero → REJECT (its
output becomes the rejection reason).
"""
import os
import shutil
import subprocess
import tempfile


def make_shell_implementer(command):
    """Return a callable(item, prompt) that runs *command* in a shell with item+prompt in env."""
    def run(item, prompt):
        env = dict(os.environ)
        env["BG_ITEM_ID"] = str(item.get("id", ""))
        env["BG_ITEM_TITLE"] = str(item.get("title", ""))
        env["BG_ITEM_PATH"] = str(item.get("path", ""))
        env["BG_ITEM_FIX"] = str(item.get("fix", ""))
        env["BG_PROMPT"] = str(prompt)
        proc = subprocess.run(command, shell=True, env=env)
        return {"ok": proc.returncode == 0}
    return run


def make_shell_verifier(command=None):
    """Return a callable(item, diff, warnings) -> {verdict, reasons} that delegates to *command*."""
    def verify(item, diff, warnings):
        if command is None:
            reason = "No verifier command; hard checks (gate, coverage, guards) gate the commit."
            return {"verdict": "APPROVE", "reasons": [reason]}
        tmpdir = tempfile.mkdtemp(prefix="bg-verify-")
        diff_file = os.path.join(tmpdir, "diff.patch")
        env = dict(os.environ)
        env["BG_DIFF_FILE"] = diff_file
        env["BG_WARNINGS"] = "\n".join(warnings or [])
        with open(diff_file, "w") as fh:
            fh.write(diff)
        proc = subprocess.run(command, shell=True, env=env, capture_output=True, text=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        if proc.returncode == 0:
            return {"verdict": "APPROVE", "reasons": []}
        output = (proc.stdout + proc.stderr).strip()
        return {"verdict": "REJECT", "reasons": [output]}
    return verify
