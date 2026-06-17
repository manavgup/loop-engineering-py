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

You are implementing ONE Python module so its EXISTING pytest test passes.

- Edit ONLY this file: ${BG_ITEM_PATH%%:*}
- The test file under tests/ is the FROZEN SPEC. Do NOT modify, delete, or weaken any test.
- The module currently raises NotImplementedError; replace the stub bodies with a real,
  faithful implementation. Keep the public function names and signatures exactly as the
  test imports them.
- Follow PEP 8 (the change is rejected if \`ruff check\` flags the file).
- A behavior change with no covering test is rejected, but the test already exists here —
  just make it pass without touching it.
- Verify locally before finishing: python3 -m pytest <the matching tests/ file> -q

Item: $BG_ITEM_TITLE
Backlog fix note: ${BG_ITEM_FIX:-（none）}
"

exec claude -p "$PROMPT" --permission-mode acceptEdits
