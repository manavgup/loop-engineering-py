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
