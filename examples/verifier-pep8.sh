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

# 1. Reject test WEAKENING. The harness lets the implementer extend tests to
#    close a coverage gap, but a dropped assertion shows up as a guard warning
#    (BG_WARNINGS). Treat that as a hard reject so coverage can't be "satisfied"
#    by gutting an assertion instead of adding real ones.
case "${BG_WARNINGS:-}" in
  *assertion-count*)
    echo "REJECT: a test assertion was removed/weakened (guard warning): $BG_WARNINGS" >&2
    exit 1
    ;;
esac

# 2. PEP-8 on the *source* files this attempt touched (parsed out of the diff),
#    so unrelated pre-existing lint never blocks a commit. This is the
#    "coverage proves execution, not quality" gap-closer: style enforced per change.
files=$(grep -E '^\+\+\+ b/' "$BG_DIFF_FILE" 2>/dev/null \
        | sed 's|^+++ b/||' \
        | grep -E '^backlog_grinder/.*\.py$' || true)

# Nothing source-y changed (e.g. only a test or doc) -> nothing for us to judge.
[ -z "$files" ] && exit 0

# shellcheck disable=SC2086
ruff check $files
