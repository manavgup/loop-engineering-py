# Module backlog — backlog-grinder

Each item is "implement one stub module so its (frozen) pytest file passes."
`scripts/grind.sh` drains these in dependency-tier order: the test is the spec,
coverage-of-change proves the new code is exercised, scope guards keep the diff
to one file, and the PEP-8 verifier enforces style. This file is the human-
readable reference — the runner generates a single-item backlog per module at
grind time.

### 🟠 HIGH — Tier 0 (leaf modules, no internal deps)

#### implement

- [ ] **implement parse.py to pass its tests**  ·  `backlog_grinder/parse.py:1`  ·  _M/high_
    - _Fix:_ implement parse.py so tests/test_parse.py passes.
- [ ] **implement triage.py to pass its tests**  ·  `backlog_grinder/triage.py:1`  ·  _M/high_
    - _Fix:_ implement triage.py so tests/test_triage.py passes.
- [ ] **implement guards.py to pass its tests**  ·  `backlog_grinder/guards.py:1`  ·  _M/high_
    - _Fix:_ implement guards.py so tests/test_guards.py passes.
- [ ] **implement gate.py to pass its tests**  ·  `backlog_grinder/gate.py:1`  ·  _M/high_
    - _Fix:_ implement gate.py so tests/test_gate.py passes.
- [ ] **implement coverage.py to pass its tests**  ·  `backlog_grinder/coverage.py:1`  ·  _M/high_
    - _Fix:_ implement coverage.py so tests/test_coverage.py passes.
- [ ] **implement feedback.py to pass its tests**  ·  `backlog_grinder/feedback.py:1`  ·  _M/high_
    - _Fix:_ implement feedback.py so tests/test_feedback.py passes.
- [ ] **implement state.py to pass its tests**  ·  `backlog_grinder/state.py:1`  ·  _M/high_
    - _Fix:_ implement state.py so tests/test_state.py passes.
- [ ] **implement provenance.py to pass its tests**  ·  `backlog_grinder/provenance.py:1`  ·  _M/high_
    - _Fix:_ implement provenance.py so tests/test_provenance.py passes.
- [ ] **implement git_adapter.py to pass its tests**  ·  `backlog_grinder/git_adapter.py:1`  ·  _M/high_
    - _Fix:_ implement git_adapter.py so tests/test_git_adapter.py passes.
- [ ] **implement coverage_adapter.py to pass its tests**  ·  `backlog_grinder/coverage_adapter.py:1`  ·  _M/high_
    - _Fix:_ implement coverage_adapter.py so tests/test_coverage_adapter.py passes.
- [ ] **implement implementer.py to pass its tests**  ·  `backlog_grinder/implementer.py:1`  ·  _M/high_
    - _Fix:_ implement implementer.py so tests/test_implementer.py passes.
- [ ] **implement persist.py to pass its tests**  ·  `backlog_grinder/persist.py:1`  ·  _M/high_
    - _Fix:_ implement persist.py so tests/test_persist.py passes.

### 🟡 MEDIUM — Tier 1 (driver: depends on guards, coverage, feedback, state)

#### implement

- [ ] **implement driver.py to pass its tests**  ·  `backlog_grinder/driver.py:1`  ·  _L/medium_
    - _Fix:_ implement driver.py so tests/test_driver.py + tests/test_e2e_v2.py pass.

### 🟡 MEDIUM — Tier 2 (cli: depends on everything)

#### implement

- [ ] **implement cli.py to pass its tests**  ·  `backlog_grinder/cli.py:1`  ·  _L/medium_
    - _Fix:_ implement cli.py so tests/test_cli_e2e.py + tests/test_e2e.py pass.
