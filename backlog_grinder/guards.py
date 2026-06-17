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


def parse_diff(diff_text):
    """Parse a unified diff string into a list of per-file metadata dicts.

    Each dict has keys: file (str), deleted (bool), added_assert (int),
    removed_assert (int).
    """
    raise NotImplementedError


def check_guards(diff, options=None):
    """Inspect a unified diff against allow/deny path lists and test-safety rules.

    Parameters
    ----------
    diff : str
        Raw unified diff text (output of ``git diff``).
    options : dict, optional
        Keys:
            allow (list[str]): if non-empty, every touched file must match at
                least one entry; otherwise it is a hard violation.
            deny  (list[str]): any touched file matching an entry is a hard
                violation.

    Returns
    -------
    dict with keys:
        ok         (bool)    : True iff violations is empty.
        violations (list[str]): Hard violations that block the commit.
        warnings   (list[str]): Advisory issues surfaced to the verifier but
                                not auto-blocking (e.g. assertion-count drop,
                                which is gameable and may be a legit refactor).
    """
    raise NotImplementedError
