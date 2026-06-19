# SPDX-License-Identifier: MIT
"""Identify changed source lines and check execution coverage.

Location: backlog_grinder/coverage.py
Authors: Manav Gupta

Parses a unified diff to extract the set of added line numbers per file, then
cross-references those lines against a coverage map to report which behavioral
(source code) lines were never executed by the test suite.

Non-behavioral files (docs, config, lock files) are excluded from the check
because they cannot be exercised by a test runner.
"""

import re

# Matches a unified-diff hunk header; group 1 = new-file start line, group 2 = length (optional).
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

# Matches the "+++ b/<path>" line that names the new version of a file.
FILE_RE = re.compile(r"^\+\+\+ b\/(.+)$")

# Non-behavioral file extensions: docs, config, lock files.
# Changes to these files don't need test coverage.
NON_BEHAVIORAL = re.compile(r"\.(md|txt|rst|json|ya?ml|toml|ini|cfg|lock)$", re.IGNORECASE)


def is_behavioral(file: str) -> bool:
    """Return True if the file requires test coverage.

    A file is considered behavioral if it is source code rather than
    documentation, configuration, or a lock file.

    Args:
        file: File path or name to classify.

    Returns:
        True if the file extension is not in the non-behavioral list.

    Examples:
        >>> is_behavioral("backlog_grinder/guards.py")
        True
        >>> is_behavioral("README.md")
        False
        >>> is_behavioral("pyproject.toml")
        False
    """
    return NON_BEHAVIORAL.search(file) is None


def changed_lines(diff: str) -> dict[str, set[int]]:
    """Parse a unified diff and return the set of added line numbers per file.

    Args:
        diff: Raw unified diff text (output of ``git diff``).

    Returns:
        A dict mapping each new-side file path to the set of line numbers
        (1-based) that were added in the diff.  Deleted files produce an
        empty set because their ``+++ /dev/null`` line does not match
        ``FILE_RE``.
    """
    result: dict[str, set[int]] = {}
    current = None
    line_no = 0
    for line in diff.splitlines():
        file_match = FILE_RE.match(line)
        if file_match:
            current = file_match.group(1)
            result[current] = set()
            continue
        hunk_match = HUNK_RE.match(line)
        if hunk_match:
            line_no = int(hunk_match.group(1))
            continue
        # Before any file header (e.g. a deletion's '+++ /dev/null', which FILE_RE
        # does not match) there is no current file — skip, never index result[None].
        if current is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            result[current].add(line_no)
            line_no += 1
        elif not line.startswith("-"):
            line_no += 1
    return result


def check_coverage(diff: str, coverage: dict[str, set[int]]) -> dict:
    """Return a coverage-check result for changed behavioral lines.

    Identifies every added line in ``diff`` that belongs to a behavioral file
    and is absent from the provided coverage map.

    Args:
        diff: Raw unified diff text (output of ``git diff``).
        coverage: Map of file path → set of line numbers executed by the test
            suite (e.g. produced by ``pytest-cov`` or a coverage adapter).

    Returns:
        A dict with keys:
            ``ok`` (bool): True iff no uncovered lines were found.
            ``uncovered`` (list[dict]): Each entry has ``file`` (str) and
                ``line`` (int) for every behavioral added line that was not
                executed.
    """
    uncovered = []
    for file, lines in changed_lines(diff).items():
        covered = coverage.get(file, set())
        for line_no in sorted(lines):
            if is_behavioral(file) and line_no not in covered:
                uncovered.append({"file": file, "line": line_no})
    return {"ok": not uncovered, "uncovered": uncovered}
