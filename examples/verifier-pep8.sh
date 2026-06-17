#!/bin/sh
# PEP-8 verifier for the backlog-grinder.
#
# The harness writes the staged diff to $BG_DIFF_FILE and runs this command:
# exit 0 = APPROVE, non-zero = REJECT (stdout/stderr becomes the rejection reason,
# which is fed back into the next attempt's prompt).
#
# We scope ruff to the *source* files this attempt touched (parsed out of the diff),
# so unrelated pre-existing lint elsewhere never blocks a commit. This is the
# "coverage proves execution, not quality" gap-closer: style is enforced per change.
set -eu

files=$(grep -E '^\+\+\+ b/' "$BG_DIFF_FILE" 2>/dev/null \
        | sed 's|^+++ b/||' \
        | grep -E '^backlog_grinder/.*\.py$' || true)

# Nothing source-y changed (e.g. only a test or doc) -> nothing for us to judge.
[ -z "$files" ] && exit 0

# shellcheck disable=SC2086
ruff check $files
