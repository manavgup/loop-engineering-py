# SPDX-License-Identifier: MIT
"""Run a shell command and evaluate pass/fail with flake detection.

Location: backlog_grinder/gate.py
Authors: Manav Gupta

Provides two entry points for running an arbitrary shell command as a gate:

``run_gate`` — single execution, returns pass/fail plus combined output.
``run_gate_checked`` — adds flake-detection per §3.4: a red first run is
    re-run once; two agreeing reds are a trusted failure; red-then-green is
    flagged as flaky.
"""

import os
import subprocess


def _gate_env():
    """Return a copy of the current env with pytest runner vars stripped out.

    Mirrors the JS gateEnv() helper that strips NODE_TEST_CONTEXT so that a
    gate which itself shells out to the test runner behaves as a standalone
    run even when the harness is invoked from within pytest.
    """
    env = dict(os.environ)
    env.pop("PYTEST_CURRENT_TEST", None)
    return env


def run_gate(command, cwd, *, timeout_ms=600_000):
    """Run a shell command in a subprocess and return a result dict.

    Args:
        command: Shell command string passed to ``subprocess.run`` with
            ``shell=True``.
        cwd: Working directory in which to execute the command.
        timeout_ms: Timeout in milliseconds before the subprocess is killed.
            Defaults to 600 000 ms (10 minutes).

    Returns:
        A dict with keys:
            ``passed`` (bool): True iff the command exited with code 0.
            ``output`` (str): Combined stdout and stderr, stripped of
                leading/trailing whitespace.
            ``infra_error`` (bool): True when the command could not run at all
                (exit code 127, meaning the executable was not found).
    """
    proc = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        env=_gate_env(),
        capture_output=True,
        text=True,
        timeout=timeout_ms / 1000,
    )
    return {
        "passed": proc.returncode == 0,
        "output": (proc.stdout + proc.stderr).strip(),
        "infra_error": proc.returncode == 127,
    }


def run_gate_checked(command, cwd, **opts):
    """Run a shell command with flake-detection re-run logic (§3.4).

    A green first run is trusted immediately.  A red first run is re-run once:
    two agreeing reds are a trusted failure; red-then-green is flagged as
    flaky.  Infrastructure errors are passed through without a re-run and are
    never marked flaky.

    Args:
        command: Shell command string passed to ``run_gate``.
        cwd: Working directory in which to execute the command.
        **opts: Additional keyword arguments forwarded to ``run_gate``
            (e.g. ``timeout_ms``).

    Returns:
        The same dict as ``run_gate`` plus:
            ``flaky`` (bool): True iff the first and second runs disagreed
                (red on the first run, green on the second).
    """
    first = run_gate(command, cwd, **opts)
    if first["passed"] or first["infra_error"]:
        first["flaky"] = False
        return first
    second = run_gate(command, cwd, **opts)
    second["flaky"] = second["passed"]
    return second
