"""Gate module: run a shell command and evaluate pass/fail with flake detection."""


def _gate_env():
    """Return a copy of the current env with pytest runner vars stripped out.

    Mirrors the JS gateEnv() helper that strips NODE_TEST_CONTEXT so that a
    gate which itself shells out to the test runner behaves as a standalone
    run even when the harness is invoked from within pytest.
    """
    raise NotImplementedError


def run_gate(command, cwd, *, timeout_ms=600_000):
    """Run *command* in a subprocess and return a result dict.

    Returns:
        dict with keys:
            passed (bool): True iff the command exited with code 0.
            output (str): Combined stdout+stderr, stripped.
            infra_error (bool): True when the command could not run at all
                (FileNotFoundError, exit 127, timeout, or non-numeric exit code).
    """
    raise NotImplementedError


def run_gate_checked(command, cwd, **opts):
    """Run *command* with flake-detection re-run logic (§3.4).

    A green first run is trusted immediately.  A red first run is re-run once:
    two agreeing reds → trusted red; red-then-green → flaky.  Infra errors are
    passed through without a re-run and are never marked flaky.

    Returns:
        Same dict as run_gate plus:
            flaky (bool): True iff first and second runs disagreed (red→green).
    """
    raise NotImplementedError
