"""The §7 git safety adapter for backlog-grinder."""

import subprocess
from types import SimpleNamespace


def make_git():
    """Return an object with git callables: diff, commit, restore, head."""

    def run(cwd, *args):
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def diff(cwd):
        run(cwd, "add", "-A")
        return run(cwd, "diff", "--cached", "HEAD")

    def commit(cwd, message):
        run(cwd, "add", "-A")
        run(cwd, "commit", "-q", "-m", message)

    def restore(cwd):
        run(cwd, "reset", "--hard", "HEAD")
        run(cwd, "clean", "-fd")

    def head(cwd):
        return run(cwd, "rev-parse", "HEAD").strip()

    return SimpleNamespace(diff=diff, commit=commit, restore=restore, head=head)
