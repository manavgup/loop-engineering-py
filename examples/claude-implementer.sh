#!/bin/sh
# Headless-Claude implementer for the Python port.
#
# The backlog-grinder invokes this once per attempt with the finding in the
# environment (BG_ITEM_*) and a base+feedback prompt (BG_PROMPT). It only EDITS
# the working tree; the harness runs the gate, coverage-of-change, scope guards
# and the PEP-8 verifier, then commits or reverts. So this can be best-effort:
# a bad edit is reverted and retried with feedback.
#
# Requires: the `claude` CLI on PATH.
set -eu

PROMPT="$BG_PROMPT

You are implementing ONE Python module so its pytest test passes.

- The module currently raises NotImplementedError; replace the stub bodies with a real,
  faithful port of the corresponding Node source. Keep the public function names and
  signatures exactly as the test imports them.
- Follow PEP 8 (the change is rejected if \`ruff check\` flags the file).
- COVERAGE-OF-CHANGE: every changed source line must be executed by a test, or the change
  is rejected. Prefer a minimal implementation. If a faithful port still has lines the
  existing test does not execute, you MAY extend the matching test file with NEW test
  functions/assertions that exercise those lines.
    * Add only REAL assertions about real behavior — never vacuous \`assert True\` padding.
    * NEVER delete a test, weaken/remove an existing assertion, or change an existing
      expected value. Those are rejected (the spec is append-only).
- Editable files this attempt: ${BG_ITEM_PATH%%:*} and its tests/ file(s) ONLY.
- Verify locally before finishing: python3 -m pytest <the matching tests/ file> --cov=. -q

Item: $BG_ITEM_TITLE
Backlog fix note: ${BG_ITEM_FIX:-（none）}
"

exec claude -p "$PROMPT" --permission-mode acceptEdits
