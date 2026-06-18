"""CLI / orchestrator for backlog-grinder.

Wires the pure modules to real adapters (git, coverage, shell implementer/
verifier, disk persistence) and drains a finite backlog against a real repo.
Model-agnostic: the implementer is a configured shell command, so any tool
(script, sed, or an LLM CLI) plugs in without the harness hardcoding a model.

Public API
----------
run_grind(config: dict) -> dict
    Orchestrate a full grind run.  Returns
    {end_state, counts, state_path, provenance_path, state_markdown_path}.

main(argv=None) -> int
    CLI entry point (argparse: --config, --repo, --backlog flag overrides).
    Returns 0 on complete|drained, 2 on halted or bad usage.
"""

from __future__ import annotations

import argparse
import json
import os
import time

from .coverage_adapter import load_coverage
from .driver import run_queue
from .gate import run_gate
from .git_adapter import make_git
from .implementer import make_shell_implementer, make_shell_verifier
from .parse import is_stale, parse_backlog
from .persist import load_state, make_provenance_writer, make_state_persister
from .triage import to_state_markdown

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_grind(config: dict) -> dict:
    """Orchestrate a full grind run against a real repo with real adapters."""
    backlog_path = config.get("backlog_path")
    repo_cwd = os.path.abspath(config.get("repo_cwd") or os.getcwd())
    gate_cmd = config.get("gate_cmd")
    coverage = config.get("coverage")
    implementer_cmd = config.get("implementer_cmd")
    verifier_cmd = config.get("verifier_cmd")
    allow = config.get("allow", [])
    deny = config.get("deny", [])
    max_attempts = config.get("max_attempts", 3)
    project_name = config.get("project_name", "Backlog Grinder")
    stop_file = config.get("stop_file")
    budget_seconds = config.get("budget_seconds")
    state_path = config.get("state_path") or os.path.join(
        repo_cwd, ".backlog-grinder", "state.json")
    provenance_path = config.get("provenance_path") or os.path.join(
        repo_cwd, ".backlog-grinder", "provenance.jsonl")
    state_markdown_path = config.get("state_markdown_path") or os.path.join(
        repo_cwd, ".backlog-grinder", "STATE.md")

    if not backlog_path:
        raise ValueError("config.backlog_path is required")
    if not gate_cmd:
        raise ValueError("config.gate_cmd is required")
    if not implementer_cmd:
        raise ValueError("config.implementer_cmd is required")
    if not coverage or not coverage.get("format") or not coverage.get("file"):
        raise ValueError(
            "config.coverage {format,file} is required — the coverage backbone is mandatory")

    # 1. Parse the backlog and re-validate each item against the real tree (park stale).
    with open(os.path.join(repo_cwd, backlog_path), encoding="utf-8") as fh:
        items = parse_backlog(fh.read())
    for it in items:
        it["stale"] = is_stale(it, lambda f: os.path.exists(os.path.join(repo_cwd, f)))

    # 2. Write the triage view (queue + stale + denylist flags) to disk.
    os.makedirs(os.path.dirname(state_markdown_path), exist_ok=True)
    with open(state_markdown_path, "w", encoding="utf-8") as fh:
        fh.write(to_state_markdown(items, {"project_name": project_name, "deny": deny}))

    # 3. Resume: load prior STATE (done items skipped, failures restored by the driver).
    state = load_state(state_path)

    # 4. Real adapters. The gate wrapper attaches a coverage map on a green run; a green gate
    #    that yields no map leaves coverage absent, so the driver halts (blocked-coverage-config)
    #    instead of silently committing untested changes.
    cov_file_abs = os.path.join(repo_cwd, coverage["file"])

    def run_gate_with_coverage(cmd, cwd):
        result = run_gate(cmd, cwd)
        if result["passed"] and not result["infra_error"]:
            try:
                result["coverage"] = load_coverage(
                    format=coverage["format"], file=cov_file_abs, repo_cwd=repo_cwd)
            except Exception:
                pass  # no coverage artifact -> key absent -> driver halts with a config error
        return result

    deadline = time.monotonic() + budget_seconds if budget_seconds else None
    deps = {
        "cwd": repo_cwd,
        "implementer": make_shell_implementer(implementer_cmd),
        "verifier": make_shell_verifier(verifier_cmd),
        "run_gate": run_gate_with_coverage,
        "git": make_git(),
        "provenance": make_provenance_writer(provenance_path),
        "persist_state": make_state_persister(state_path),
        "exists": os.path.exists,
    }
    if deadline is not None:
        deps["budget"] = {"ok": lambda: time.monotonic() < deadline}

    # 5. Run. The shell implementer edits the tree relative to the process cwd, so grind from
    #    inside the target repo (the driver uses deps['cwd'] for git ops).
    cwd0 = os.getcwd()
    os.chdir(repo_cwd)
    try:
        run_queue(items, deps=deps, state=state, gate_cmd=gate_cmd, allow=allow,
                  deny=deny, max_attempts=max_attempts, stop_file=stop_file)
    finally:
        os.chdir(cwd0)
    deps["persist_state"](state)

    # 6. Honest end states. STATE is authoritative for status.
    def status_of(it):
        rec = state["items"].get(it["id"])
        return (rec and rec.get("status")) or it.get("status") or "pending"

    non_stale = [it for it in items if not it.get("stale")]
    counts = {"total": len(items), "stale": len(items) - len(non_stale),
              "done": 0, "abandoned": 0, "parked": 0, "blocked": 0, "pending": 0}
    for it in non_stale:
        s = status_of(it)
        if s == "done":
            counts["done"] += 1
        elif s == "abandoned":
            counts["abandoned"] += 1
        elif s in ("parked-infra", "parked-flaky"):
            counts["parked"] += 1
        elif s == "blocked-coverage-config":
            counts["blocked"] += 1
        else:
            counts["pending"] += 1

    if counts["pending"] > 0 or counts["blocked"] > 0:
        end_state = "halted"
    elif counts["done"] == len(non_stale):
        end_state = "complete"
    else:
        end_state = "drained"

    return {"end_state": end_state, "counts": counts, "state_path": state_path,
            "provenance_path": provenance_path, "state_markdown_path": state_markdown_path}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Parse argv, load JSON config, run run_grind, print summary, return exit code."""
    parser = argparse.ArgumentParser(
        prog="backlog-grind",
        description="Drain a finite backlog against a repo (model-agnostic, no LLM required).")
    parser.add_argument("--config", help="JSON config file")
    parser.add_argument("--repo", help="target git repo (overrides config.repo_cwd)")
    parser.add_argument("--backlog", help="backlog file (overrides config.backlog_path)")
    args = parser.parse_args(argv)

    if not args.config and not args.backlog:
        parser.print_help()
        return 2

    config = {}
    if args.config:
        with open(args.config, encoding="utf-8") as fh:
            config = json.load(fh)
    if args.repo:
        config["repo_cwd"] = args.repo
    if args.backlog:
        config["backlog_path"] = args.backlog

    summary = run_grind(config)
    print(f"\nend state: {summary['end_state']}")
    print(f"counts:    {json.dumps(summary['counts'])}")
    print(f"state:     {summary['state_path']}")
    print(f"provenance:{summary['provenance_path']}")
    print(f"triage:    {summary['state_markdown_path']}")
    return 2 if summary["end_state"] == "halted" else 0


if __name__ == "__main__":
    raise SystemExit(main())
