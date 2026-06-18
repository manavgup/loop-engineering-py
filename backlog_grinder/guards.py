"""Guards: diff inspection to block forbidden changes before commit.

Public API
----------
parse_diff(diff_text)          -> list[dict]
check_guards(diff, options)    -> dict
"""

import re

# Matches the "diff --git a/<path> b/<path>" header line.
_FILE_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$")

# Patterns that identify test files (mirrors the JS isTestFile defaults).
_TEST_GLOBS = [
    re.compile(r"(^|\/)tests?\/"),
    re.compile(r"test_.*\.py$"),
    re.compile(r"_test\."),
    re.compile(r"\.test\."),
]


def _is_test_file(path):
    """Return True if ``path`` looks like a test file."""
    return any(glob.search(path) for glob in _TEST_GLOBS)


def _path_matches(path, pattern):
    """Segment-based match: ``path`` equals ``pattern`` or sits under it."""
    pattern = pattern.rstrip("/")
    return path == pattern or path.startswith(pattern + "/")


def parse_diff(diff_text):
    """Parse a unified diff string into a list of per-file metadata dicts.

    Each dict has keys: file (str), deleted (bool), added_assert (int),
    removed_assert (int).
    """
    files = []
    current = None
    for line in diff_text.splitlines():
        match = _FILE_RE.match(line)
        if match:
            current = {
                "file": match.group(2),
                "deleted": False,
                "added_assert": 0,
                "removed_assert": 0,
            }
            files.append(current)
        elif line.startswith("deleted file mode"):
            current["deleted"] = True
        elif line.startswith("+") and not line.startswith("+++"):
            current["added_assert"] += "assert" in line
        elif line.startswith("-") and not line.startswith("---"):
            current["removed_assert"] += "assert" in line
    return files


def check_guards(diff, options=None):
    """Inspect a unified diff against an allowlist and test-safety rules.

    Parameters
    ----------
    diff : str
        Raw unified diff text (output of ``git diff``).
    options : dict, optional
        Key ``allow`` (list[str]): if non-empty, every touched file must match
        at least one entry; otherwise it is a hard violation.

    Returns
    -------
    dict with keys:
        ok         (bool)    : True iff violations is empty.
        violations (list[str]): Hard violations that block the commit.
        warnings   (list[str]): Advisory issues surfaced to the verifier but
                                not auto-blocking (e.g. assertion-count drop,
                                which is gameable and may be a legit refactor).
    """
    options = options or {}
    allow = options.get("allow", [])
    violations = []
    warnings = []
    for entry in parse_diff(diff):
        path = entry["file"]
        if entry["deleted"] and _is_test_file(path):
            violations.append(f"deleted test file: {path}")
        if allow and not any(_path_matches(path, p) for p in allow):
            violations.append(f"file outside allowlist: {path}")
        if entry["removed_assert"] > entry["added_assert"]:
            warnings.append(f"assertion-count drop in {path}")
    return {"ok": not violations, "violations": violations, "warnings": warnings}
