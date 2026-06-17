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

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_grind(config: dict) -> dict:
    """Orchestrate a full grind run against a real repo with real adapters.

    Parameters
    ----------
    config : dict
        Keys (snake_case):
            backlog_path      (str, required)
            repo_cwd          (str, default cwd)
            gate_cmd          (str, required)
            coverage          (dict {format, file}, required)
            implementer_cmd   (str, required)
            verifier_cmd      (str | None)
            allow             (list[str], default [])
            deny              (list[str], default [])
            max_attempts      (int, default 3)
            project_name      (str, default 'Backlog Grinder')
            stop_file         (str | None)
            budget_seconds    (int | None)
            state_path        (str | None)
            provenance_path   (str | None)
            state_markdown_path (str | None)

    Returns
    -------
    dict
        Keys: end_state (str in {'complete','drained','halted'}),
              counts (dict), state_path, provenance_path, state_markdown_path.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Parse argv, load JSON config, run run_grind, print summary, return exit code.

    Returns 0 on complete|drained, 2 on halted or bad usage.
    """
    raise NotImplementedError
