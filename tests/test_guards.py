"""Faithful pytest port of guards.test.mjs.

Covers:
- deleted test file → hard violation
- assertion-count drop → advisory warning (not a block)
- file outside allowlist → hard violation
- clean in-scope diff → ok with no violations
- path matching is segment-based, not substring
- parse_diff output shape
"""

from backlog_grinder.guards import check_guards, parse_diff

# ---------------------------------------------------------------------------
# Fixture diffs (verbatim ports of the JS const strings)
# ---------------------------------------------------------------------------

DELETED_TEST = """\
diff --git a/tests/test_foo.py b/tests/test_foo.py
deleted file mode 100644
--- a/tests/test_foo.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def test_foo():
-    assert bar() == 1
"""

WEAKENED = """\
diff --git a/tests/test_bar.py b/tests/test_bar.py
--- a/tests/test_bar.py
+++ b/tests/test_bar.py
@@ -1,3 +1,2 @@
 def test_bar():
-    assert bar() == 1
     pass
"""

OUT_OF_SCOPE = """\
diff --git a/backend/other.py b/backend/other.py
--- a/backend/other.py
+++ b/backend/other.py
@@ -1 +1 @@
-x = 1
+x = 2
"""

CLEAN = """\
diff --git a/backend/openai.py b/backend/openai.py
--- a/backend/openai.py
+++ b/backend/openai.py
@@ -1 +1 @@
-api_key=str(k)
+api_key=k.get_secret_value()
"""

OAUTH = """\
diff --git a/backend/oauth_helper.py b/backend/oauth_helper.py
--- a/backend/oauth_helper.py
+++ b/backend/oauth_helper.py
@@ -1 +1 @@
-a
+b
"""

BAK = """\
diff --git a/src/a.py.bak b/src/a.py.bak
--- a/src/a.py.bak
+++ b/src/a.py.bak
@@ -1 +1 @@
-a
+b
"""

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_deleted_test_file_is_a_hard_violation():
    r = check_guards(DELETED_TEST, {"allow": ["tests/"], "deny": []})
    assert r["ok"] is False
    assert any("deleted" in v.lower() or "test" in v.lower() for v in r["violations"]), (
        f"Expected a 'deleted.*test' violation, got: {r['violations']}"
    )
    # Combined text must match /deleted.*test/i
    import re
    assert re.search(r"deleted.*test", " ".join(r["violations"]), re.IGNORECASE)


def test_assertion_count_drop_is_advisory_warning_not_a_block():
    r = check_guards(WEAKENED, {"allow": ["tests/"], "deny": []})
    assert r["ok"] is True
    assert any("assertion-count" in w.lower() for w in r["warnings"]), (
        f"Expected 'assertion-count' warning, got: {r['warnings']}"
    )


def test_out_of_allowlist_file_is_a_hard_violation():
    r = check_guards(OUT_OF_SCOPE, {"allow": ["backend/openai.py"], "deny": []})
    assert r["ok"] is False
    assert any("allowlist" in v.lower() for v in r["violations"]), (
        f"Expected 'allowlist' violation, got: {r['violations']}"
    )


def test_passes_a_clean_in_scope_diff():
    r = check_guards(CLEAN, {"allow": ["backend/openai.py"], "deny": ["auth/"]})
    assert r["ok"] is True
    assert r["violations"] == []


def test_path_matching_is_segment_based_not_substring():
    # deny 'auth' must NOT fire on backend/oauth_helper.py (false denial —
    # 'auth' is not a path segment of that file, only a substring)
    r = check_guards(OAUTH, {"allow": ["backend/oauth_helper.py"], "deny": ["auth"]})
    assert r["ok"] is True

    # allow 'src/a.py' must NOT admit src/a.py.bak (false allow — the exact
    # path doesn't match and .bak is not a child path)
    r2 = check_guards(BAK, {"allow": ["src/a.py"], "deny": []})
    assert r2["ok"] is False


def test_parse_diff_returns_file_list():
    """parse_diff returns a list of dicts with file, deleted, added_assert, removed_assert."""
    files = parse_diff(DELETED_TEST)
    assert len(files) == 1
    f = files[0]
    assert f["file"] == "tests/test_foo.py"
    assert f["deleted"] is True
    # The removed lines contain 'assert'
    assert f["removed_assert"] >= 1


def test_parse_diff_counts_added_and_removed_asserts():
    files = parse_diff(WEAKENED)
    assert len(files) == 1
    f = files[0]
    assert f["removed_assert"] == 1
    assert f["added_assert"] == 0


def test_parse_diff_non_deleted_file():
    files = parse_diff(CLEAN)
    assert len(files) == 1
    f = files[0]
    assert f["file"] == "backend/openai.py"
    assert f["deleted"] is False
    assert f["added_assert"] == 0
    assert f["removed_assert"] == 0


def test_check_guards_defaults_allow_deny_to_empty():
    """check_guards with no options should not raise and should return ok for clean diff."""
    r = check_guards(CLEAN)
    assert r["ok"] is True
    assert r["violations"] == []
    assert r["warnings"] == []
