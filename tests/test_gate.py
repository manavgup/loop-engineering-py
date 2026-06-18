"""Tests for backlog_grinder.gate — synchronous."""
import os
import tempfile

from backlog_grinder.gate import run_gate, run_gate_checked


def test_run_gate_pass_on_exit_0():
    r = run_gate("printf 'ok'; exit 0", os.getcwd())
    assert r["passed"] is True
    assert "ok" in r["output"]


def test_run_gate_fail_on_nonzero_exit_real_red_not_infra():
    # stderr output; real red, not an infra error
    r = run_gate("printf 'boom' 1>&2; exit 1", os.getcwd())
    assert r["passed"] is False
    assert r["infra_error"] is False
    assert "boom" in r["output"]


def test_run_gate_flags_infra_error_command_not_found():
    r = run_gate("definitely_not_a_real_command_xyz", os.getcwd())
    assert r["passed"] is False
    assert r["infra_error"] is True


def test_run_gate_checked_green_first_run_trusted_not_flaky():
    r = run_gate_checked("printf 'ok'; exit 0", os.getcwd())
    assert r["passed"] is True
    assert r["flaky"] is False


def test_run_gate_checked_two_agreeing_reds_trusted_red_not_flaky():
    r = run_gate_checked("exit 1", os.getcwd())
    assert r["passed"] is False
    assert r["flaky"] is False


def test_run_gate_checked_red_then_green_disagreement_is_flaky():
    with tempfile.TemporaryDirectory(prefix="bg-flake-") as tmpdir:
        marker = os.path.join(tmpdir, "seen")
        # first invocation: marker absent → create it + exit 1
        # second invocation: marker present → exit 0
        cmd = f"if [ -e '{marker}' ]; then exit 0; else : > '{marker}'; exit 1; fi"
        r = run_gate_checked(cmd, os.getcwd())
    assert r["flaky"] is True


def test_run_gate_checked_infra_error_passed_through_never_flaky():
    r = run_gate_checked("definitely_not_a_real_command_xyz", os.getcwd())
    assert r["infra_error"] is True
    assert r["flaky"] is False
