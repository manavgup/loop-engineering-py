# Port backlog — loop-engineering-py

Each item is "implement one stub module so its (already-ported, frozen) pytest
file passes." The grinder drains these in dependency-tier order via
`port/grind-port.sh`; the test is the spec, coverage-of-change proves the new
code is exercised, scope guards keep the diff to one file, and the PEP-8
verifier enforces style. This file is the human-readable reference — the runner
generates a single-item backlog per module at grind time.

### 🟠 HIGH — Tier 0 (leaf modules, no internal deps)

#### port

- [ ] **implement parse.py to pass its tests**  ·  `backlog_grinder/parse.py:1`  ·  _M/high_
    - _Fix:_ port scripts/parse.mjs; tests/test_parse.py is the contract.
- [ ] **implement triage.py to pass its tests**  ·  `backlog_grinder/triage.py:1`  ·  _M/high_
    - _Fix:_ port scripts/triage.mjs; tests/test_triage.py is the contract.
- [ ] **implement guards.py to pass its tests**  ·  `backlog_grinder/guards.py:1`  ·  _M/high_
    - _Fix:_ port scripts/guards.mjs; tests/test_guards.py is the contract.
- [ ] **implement gate.py to pass its tests**  ·  `backlog_grinder/gate.py:1`  ·  _M/high_
    - _Fix:_ port scripts/gate.mjs; tests/test_gate.py is the contract.
- [ ] **implement coverage.py to pass its tests**  ·  `backlog_grinder/coverage.py:1`  ·  _M/high_
    - _Fix:_ port scripts/coverage.mjs; tests/test_coverage.py is the contract.
- [ ] **implement feedback.py to pass its tests**  ·  `backlog_grinder/feedback.py:1`  ·  _M/high_
    - _Fix:_ port scripts/feedback.mjs; tests/test_feedback.py is the contract.
- [ ] **implement state.py to pass its tests**  ·  `backlog_grinder/state.py:1`  ·  _M/high_
    - _Fix:_ port scripts/state.mjs; tests/test_state.py is the contract.
- [ ] **implement provenance.py to pass its tests**  ·  `backlog_grinder/provenance.py:1`  ·  _M/high_
    - _Fix:_ port scripts/provenance.mjs; tests/test_provenance.py is the contract.
- [ ] **implement git_adapter.py to pass its tests**  ·  `backlog_grinder/git_adapter.py:1`  ·  _M/high_
    - _Fix:_ port scripts/git-adapter.mjs; tests/test_git_adapter.py is the contract.
- [ ] **implement coverage_adapter.py to pass its tests**  ·  `backlog_grinder/coverage_adapter.py:1`  ·  _M/high_
    - _Fix:_ port scripts/coverage-adapter.mjs; tests/test_coverage_adapter.py is the contract.
- [ ] **implement implementer.py to pass its tests**  ·  `backlog_grinder/implementer.py:1`  ·  _M/high_
    - _Fix:_ port scripts/implementer.mjs; tests/test_implementer.py is the contract.
- [ ] **implement persist.py to pass its tests**  ·  `backlog_grinder/persist.py:1`  ·  _M/high_
    - _Fix:_ port scripts/persist.mjs; tests/test_persist.py is the contract.

### 🟡 MEDIUM — Tier 1 (driver: depends on guards, coverage, feedback, state)

#### port

- [ ] **implement driver.py to pass its tests**  ·  `backlog_grinder/driver.py:1`  ·  _L/medium_
    - _Fix:_ port scripts/driver.mjs; tests/test_driver.py + tests/test_e2e_v2.py are the contract.

### 🟡 MEDIUM — Tier 2 (cli: depends on everything)

#### port

- [ ] **implement cli.py to pass its tests**  ·  `backlog_grinder/cli.py:1`  ·  _L/medium_
    - _Fix:_ port scripts/cli.mjs + bin/grind.mjs; tests/test_cli_e2e.py + tests/test_e2e.py are the contract.
