#!/usr/bin/env bash
# Drive the (Node) backlog-grinder over this Python repo, module by module, in
# dependency-tier order. Each module is one grind run whose gate targets ONLY
# that module's pytest file(s) — sidestepping the harness's per-run (not
# per-item) gate scope, so a still-stubbed downstream module can't redden an
# upstream module's gate.
#
# The TEST is the spec (already ported, frozen). The implementer fills the stub.
# coverage-of-change proves the new code is actually executed by its test;
# scope guards keep the diff to the one module; the PEP-8 verifier enforces style.
#
# Usage:
#   port/grind-port.sh                 # all tiers
#   port/grind-port.sh parse guards    # just these modules
#   IMPL='sh examples/deterministic.sh' port/grind-port.sh   # swap implementer
#
# Env overrides:
#   GRINDER_BIN  path to the Node grinder bin/grind.mjs
#   IMPL         implementer command (default: headless Claude)
#   MAX_ATTEMPTS per-item attempt cap (default 3)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
GRINDER_BIN="${GRINDER_BIN:-/Users/mg/mg-work/manav/work/ai-experiments/loop-engineering/starters/backlog-grinder-claude/bin/grind.mjs}"
IMPL="${IMPL:-sh examples/claude-implementer.sh}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-3}"
TMP="$REPO/.grind-tmp"
mkdir -p "$TMP"

TIER0="parse triage guards gate coverage feedback state provenance git_adapter coverage_adapter implementer persist"
TIER1="driver"
TIER2="cli"

# module -> source .mjs basename (only the two hyphenated ones differ)
src_name() {
  case "$1" in
    git_adapter) echo "git-adapter" ;;
    coverage_adapter) echo "coverage-adapter" ;;
    *) echo "$1" ;;
  esac
}

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
  local src tests backlog config
  src="$(src_name "$mod")"
  tests="$(test_files "$mod")"
  backlog="$TMP/$mod.backlog.md"
  config="$TMP/$mod.config.json"

  cat > "$backlog" <<EOF
### 🟠 HIGH — port modules

#### port

- [ ] **implement $mod.py to pass its tests**  ·  \`backlog_grinder/$mod.py:1\`  ·  _M/high_
    - _Evidence:_ backlog_grinder/$mod.py is a stub raising NotImplementedError; $tests is the contract.
    - _Fix:_ port scripts/$src.mjs to PEP-8 Python so $tests passes; edit only backlog_grinder/$mod.py, never the tests.
EOF

  # Tests are the FROZEN, complete spec — a minimal faithful implementation is
  # already 100%-covered by them (verified). So scope is the module file ONLY
  # and tests are denied: the implementer's job is a minimal port, and
  # coverage-of-change rejects any extra/unexecuted line it invents.
  cat > "$config" <<EOF
{
  "backlogPath": ".grind-tmp/$mod.backlog.md",
  "gateCmd": "python3 -m pytest $tests --cov=backlog_grinder --cov-report=xml:coverage.xml --cov-fail-under=0 -q",
  "coverage": { "format": "cobertura", "file": "coverage.xml" },
  "implementerCmd": "$IMPL",
  "verifierCmd": "sh examples/verifier-pep8.sh",
  "allow": ["backlog_grinder/$mod.py"],
  "deny": ["tests/"],
  "maxAttempts": $MAX_ATTEMPTS,
  "projectName": "loop-engineering-py port: $mod"
}
EOF

  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "  grinding: $mod   (gate: $tests)"
  echo "════════════════════════════════════════════════════════════"
  node "$GRINDER_BIN" --config "$config" --repo "$REPO"
}

modules="${*:-$TIER0 $TIER1 $TIER2}"
for mod in $modules; do
  grind_module "$mod"
done

echo ""
echo "Done. Full suite:"
( cd "$REPO" && python3 -m pytest -q --tb=no || true )
