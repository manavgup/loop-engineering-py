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


def make_shell_implementer(command):
    """Return a callable(item, prompt) that runs *command* in a shell with item+prompt in env."""
    raise NotImplementedError


def make_shell_verifier(command):
    """Return a callable(item, diff, warnings) -> {verdict, reasons} that delegates to *command*."""
    raise NotImplementedError
