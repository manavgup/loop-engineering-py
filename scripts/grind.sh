#!/usr/bin/env bash
# Drive backlog-grind over a target repo one module at a time, in dependency-tier
# order. Each module is one grind run whose gate targets ONLY that module's pytest
# file(s) — this sidesteps the per-run (not per-item) gate scope, so a still-stubbed
# downstream module can't redden an upstream module's gate.
#
# This is the per-module pattern used to build this package test-first: the test is
# the frozen spec, coverage-of-change proves the new code is executed, scope guards
# keep the diff to the one module, and the PEP-8 verifier enforces style.
#
# Usage:
#   scripts/grind.sh                       # all modules, all tiers (target: this repo)
#   scripts/grind.sh parse guards          # just these modules
#   REPO=/path/to/target scripts/grind.sh  # a different target repo
#   IMPL='sh examples/my-implementer.sh' scripts/grind.sh
#
# Env overrides:
#   REPO         target git repo (default: this repo)
#   IMPL         implementer command (default: headless Claude)
#   MAX_ATTEMPTS per-item attempt cap (default 3)
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${REPO:-$HERE}"
IMPL="${IMPL:-sh examples/claude-implementer.sh}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-3}"
TMP="$REPO/.grind-tmp"
mkdir -p "$TMP"

TIER0="parse triage guards gate coverage feedback state provenance git_adapter coverage_adapter implementer persist"
TIER1="driver"
TIER2="cli"

# module -> pytest file(s) that pin it
test_files() {
  case "$1" in
    driver) echo "tests/test_driver.py tests/test_e2e_v2.py" ;;
    cli)    echo "tests/test_cli_e2e.py tests/test_e2e.py" ;;
    *)      echo "tests/test_$1.py" ;;
  esac
}

grind_module() {
  local mod="$1"
  local tests backlog config
  tests="$(test_files "$mod")"
  backlog="$TMP/$mod.backlog.md"
  config="$TMP/$mod.config.json"

  cat > "$backlog" <<EOF
### 🟠 HIGH — modules

#### implement

- [ ] **implement $mod.py to pass its tests**  ·  \`backlog_grinder/$mod.py:1\`  ·  _M/high_
    - _Evidence:_ backlog_grinder/$mod.py is a stub raising NotImplementedError; $tests is the contract.
    - _Fix:_ implement backlog_grinder/$mod.py so $tests passes; edit only that file, never the tests.
EOF

  # The test is the frozen, complete spec — a minimal implementation is fully
  # covered by it. Scope is the module file ONLY and tests are denied: the
  # implementer writes a minimal module, and coverage-of-change rejects any
  # extra, unexecuted line it invents.
  cat > "$config" <<EOF
{
  "backlog_path": ".grind-tmp/$mod.backlog.md",
  "gate_cmd": "python3 -m pytest $tests --cov=backlog_grinder --cov-report=xml:coverage.xml --cov-fail-under=0 -q",
  "coverage": { "format": "cobertura", "file": "coverage.xml" },
  "implementer_cmd": "$IMPL",
  "verifier_cmd": "sh examples/verifier-pep8.sh",
  "allow": ["backlog_grinder/$mod.py"],
  "deny": ["tests/"],
  "max_attempts": $MAX_ATTEMPTS,
  "project_name": "backlog-grinder: $mod"
}
EOF

  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "  grinding: $mod   (gate: $tests)"
  echo "════════════════════════════════════════════════════════════"
  ( cd "$HERE" && python3 -m backlog_grinder.cli --config "$config" --repo "$REPO" )
}

modules="${*:-$TIER0 $TIER1 $TIER2}"
for mod in $modules; do
  grind_module "$mod"
done

echo ""
echo "Done. Full suite:"
( cd "$REPO" && python3 -m pytest -q --tb=no || true )
