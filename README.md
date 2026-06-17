# loop-engineering-py

A Python (PEP-8) port of the **backlog-grinder** loop-engineering harness, with
feature parity to the Node original in `loop-engineering/starters/backlog-grinder-claude`.

It is also a **self-referential demo**: this repo was built *by* the Node
harness grinding against it. The Node `loop-engineering` tool is the stable
grinder; this repo is its target. The test suite was ported first (the spec),
then each module was implemented by the grinder behind the same hybrid checker
the harness gives any repo — gate ∧ coverage-of-change ∧ scope guards ∧ a
PEP-8 verifier — so no module landed unless a test executed its lines.

## Layout

```
backlog_grinder/      the package (pure modules + real adapters)
  parse  triage  guards  gate  coverage  feedback  state  provenance   # tier 0
  git_adapter  coverage_adapter  implementer  persist                  # tier 0 adapters
  driver                                                               # tier 1
  cli                                                                  # tier 2 (orchestrator + main)
tests/                one pytest file per module + e2e proofs (the frozen spec)
examples/             claude-implementer.sh, verifier-pep8.sh
port/grind-port.sh    drives the Node grinder over this repo, tier by tier
BACKLOG.md            human-readable port backlog
```

## Design notes (vs. the Node original)

- **Synchronous.** The Node code is async (Promises); the Python port is plain
  synchronous code — injected dependencies are ordinary callables.
- **Dicts, not objects.** Items, records, gate results, verdicts and lessons are
  plain dicts with snake_case keys (`gate_output`, `coverage_ok`, …).
- **Coverage backbone is cobertura.** The gate emits `coverage.xml` via
  `pytest --cov=backlog_grinder --cov-report=xml`; the coverage adapter parses
  cobertura (and lcov) and remaps filenames to repo-relative paths.

## Develop / test

```bash
python3 -m pip install -e '.[dev]'   # pytest, pytest-cov, ruff
python3 -m pytest -q                 # run the suite
python3 -m pytest --cov=backlog_grinder --cov-report=term-missing
ruff check backlog_grinder tests     # PEP-8
```

## How it was (re)built — running the grinder

```bash
# headless-Claude implementer (default); needs the `claude` CLI:
port/grind-port.sh

# a subset, in order:
port/grind-port.sh parse guards coverage

# swap in any implementer (model-agnostic):
IMPL='sh examples/my-implementer.sh' port/grind-port.sh
```

Each module is one grind run whose gate targets only that module's pytest
file(s) — this respects the harness's per-run (not per-item) gate scope so a
still-stubbed downstream module can't redden an upstream module's gate. Outputs
land in `<repo>/.backlog-grinder/` (triage `STATE.md`, resumable `state.json`,
append-only `provenance.jsonl`).
