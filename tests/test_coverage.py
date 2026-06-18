"""Pytest port of coverage.test.mjs — faithful behavioral port, synchronous, PEP-8."""
from backlog_grinder.coverage import changed_lines, check_coverage, is_behavioral

# Unified diff used across multiple tests.
# The hunk "@@ -10,2 +10,3 @@" means the new file starts at line 10.
# The context line " a = 1" is line 10 (no '+'/'-'), "+b = 2" is the added line 11,
# and " return a" is line 12.
DIFF = """\
diff --git a/src/x.py b/src/x.py
--- a/src/x.py
+++ b/src/x.py
@@ -10,2 +10,3 @@ def f():
 a = 1
+b = 2
 return a
"""


def test_changed_lines_extracts_added_line_numbers_per_file():
    m = changed_lines(DIFF)
    assert m["src/x.py"] == {11}


def test_is_behavioral_exempts_docs_config_flags_source():
    assert is_behavioral("src/x.py") is True
    assert is_behavioral("README.md") is False
    assert is_behavioral("config/app.yaml") is False


def test_check_coverage_fails_when_changed_source_line_was_not_executed():
    # Line 11 was added but is not in the covered set {10, 12}.
    cov = {"src/x.py": {10, 12}}
    r = check_coverage(DIFF, cov)
    assert r["ok"] is False
    import re
    assert re.search(r"x\.py", r["uncovered"][0]["file"])


def test_check_coverage_passes_when_changed_lines_were_executed():
    cov = {"src/x.py": {10, 11, 12}}
    assert check_coverage(DIFF, cov)["ok"] is True


# Regression: a real `git diff` for a DELETED file ends its header with
# "+++ /dev/null" (which FILE_RE does not match) and contains only '-' lines.
# changed_lines must not index result[None] (it crashed before the guard was added),
# and a multi-line addition must number each added line distinctly.
def test_changed_lines_handles_deletion_and_multiline_additions():
    diff = (
        "diff --git a/t/test_x.py b/t/test_x.py\n"
        "deleted file mode 100644\n"
        "--- a/t/test_x.py\n"
        "+++ /dev/null\n"
        "@@ -1,2 +0,0 @@\n"
        "-def test_x():\n"
        "-    assert True\n"
        "diff --git a/src/y.py b/src/y.py\n"
        "--- a/src/y.py\n"
        "+++ b/src/y.py\n"
        "@@ -1,0 +1,3 @@\n"
        "+a = 1\n"
        "+b = 2\n"
        "+c = 3\n"
    )
    result = changed_lines(diff)
    # The deleted file contributes no added lines (and must not crash on +++ /dev/null).
    assert result.get("t/test_x.py", set()) == set()
    # Each added line in the multi-line hunk is numbered distinctly from the hunk start.
    assert result["src/y.py"] == {1, 2, 3}
