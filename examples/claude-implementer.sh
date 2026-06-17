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

You are implementing ONE Python module so its pytest test passes. The TEST is the
complete spec — read it first and implement exactly what it requires, nothing more.

- Edit ONLY this file: ${BG_ITEM_PATH%%:*}  (the matching tests/ file is frozen — do NOT touch it)
- The module currently raises NotImplementedError; replace the stub bodies with a real
  implementation. Keep the public function names and signatures exactly as the test imports them.
- Write the MINIMAL implementation that makes the test pass. COVERAGE-OF-CHANGE: every line
  you write must be executed by the test, or the change is REJECTED. So:
    * Do NOT add defensive branches, error handling, helper functions, __main__ blocks, or
      code paths the test never triggers — each unexecuted line fails the gate.
    * If you are tempted to add an edge-case guard the test does not exercise, leave it out.
- Follow PEP 8 (rejected if \`ruff check\` flags the file); keep lines ≤ 100 chars.
- Verify before finishing: python3 -m pytest <the matching tests/ file> --cov=backlog_grinder -q
  and confirm the module shows no missing lines.

Item: $BG_ITEM_TITLE
Backlog fix note: ${BG_ITEM_FIX:-（none）}
"

exec claude -p "$PROMPT" --permission-mode acceptEdits
