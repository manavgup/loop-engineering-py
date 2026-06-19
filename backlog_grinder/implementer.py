# SPDX-License-Identifier: MIT
"""Pluggable, model-agnostic implementer and verifier factories.

Location: backlog_grinder/implementer.py
Authors: Manav Gupta

The implementer runs a configured shell command that is expected to edit the
working tree to fix the item.  The item and prompt are exposed via env so ANY
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


def make_shell_implementer(command: str):
    """Return a callable that runs *command* in a shell with item fields and prompt in env.

    The returned callable accepts an item dict and a prompt string.  It sets the
    following environment variables before executing *command*:

    - ``BG_ITEM_ID`` — item ``id`` field (stringified).
    - ``BG_ITEM_TITLE`` — item ``title`` field.
    - ``BG_ITEM_PATH`` — item ``path`` field.
    - ``BG_ITEM_FIX`` — item ``fix`` field.
    - ``BG_PROMPT`` — the prompt string.

    Args:
        command: Shell command string passed to ``subprocess.run(..., shell=True)``.
            Any tool that reads the ``BG_*`` variables and edits the working tree
            can be used here (e.g. ``claude -p "$BG_PROMPT"``).

    Returns:
        A callable ``(item: dict, prompt: str) -> dict`` that runs *command* and
        returns ``{"ok": True}`` on exit code 0 or ``{"ok": False}`` otherwise.
    """

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


def make_shell_verifier(command: str | None = None):
    """Return a callable that verifies a diff by delegating to *command*.

    When *command* is ``None`` the verifier always approves, relying on the
    hybrid checker's hard checks (gate, coverage, guards) to gate commits.
    When *command* is provided it receives the diff via a temp file referenced
    by ``$BG_DIFF_FILE`` and guard warnings via ``$BG_WARNINGS``; exit 0 →
    APPROVE, any non-zero exit → REJECT.

    Args:
        command: Optional shell command string.  ``None`` means "no verifier;
            always APPROVE".

    Returns:
        A callable ``(item: dict, diff: str, warnings: list[str]) -> dict``
        that returns ``{"verdict": "APPROVE"|"REJECT", "reasons": list[str]}``.
    """

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
