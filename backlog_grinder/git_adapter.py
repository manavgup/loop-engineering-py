# SPDX-License-Identifier: MIT
"""Git safety adapter for the §7 rollback / commit layer.

Location: backlog_grinder/git_adapter.py
Authors: Manav Gupta

Provides a single factory, ``make_git``, that bundles the four git operations
the driver needs into an injectable dict of callables.  Using a dict instead of
a module-level API makes it trivial to swap in fakes during testing.
"""

import subprocess


def make_git() -> dict:
    """Return a dict of git callables: ``diff``, ``commit``, ``restore``, ``head``.

    The driver consumes this as ``deps['git']`` with dict access
    (e.g. ``deps['git']['diff'](cwd)``), matching the injected fakes in the
    test suite.

    Returns:
        A dict with keys ``"diff"``, ``"commit"``, ``"restore"``, and ``"head"``,
        each mapping to a callable that operates on a working-tree directory.
    """

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

    return {"diff": diff, "commit": commit, "restore": restore, "head": head}
