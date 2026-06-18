"""Tests for backlog_grinder.feedback.

JS assert.match(str, /regex/) -> re.search(pattern, str) is not None.
JS assert.equal -> plain assert with ==.
JS assert.notEqual -> plain assert with !=.
JS assert.deepEqual -> plain assert with ==.
"""

import re

from backlog_grinder.feedback import (
    append_lesson,
    build_retry_prompt,
    is_repeated_failure,
    make_lessons_adapter,
    relevant_lessons,
    retract_lesson,
    signature,
)

# ---------------------------------------------------------------------------
# signature
# ---------------------------------------------------------------------------


def test_signature_normalizes_volatile_bits_so_repeats_match():
    a = signature("FAILED tests/test_x.py::test_a at 0x7f12 in 1.23s")
    b = signature("FAILED tests/test_x.py::test_a at 0x9ab0 in 4.56s")
    assert a == b


def test_distinct_numeric_failures_keep_distinct_signatures_no_over_collapse():
    assert signature("expected 3 got 4") != signature("expected 3 got 99")
    assert signature("x.py:46 failed") != signature("x.py:99 failed")


# ---------------------------------------------------------------------------
# is_repeated_failure (and failure_fingerprint by proxy)
# ---------------------------------------------------------------------------


def test_is_repeated_failure_matches_on_full_rejection_fingerprint_not_gate_output_alone():
    prev = [
        {
            "gate_output": "FAILED test_a at 0xAAAA in 1s",
            "guard_violations": [],
            "coverage_uncovered": [],
        }
    ]
    # volatile-only difference -> same fingerprint -> repeat
    assert (
        is_repeated_failure(
            prev,
            {
                "gate_output": "FAILED test_a at 0xBBBB in 9s",
                "guard_violations": [],
                "coverage_uncovered": [],
            },
        )
        is True
    )
    # different gate output -> different fingerprint
    assert (
        is_repeated_failure(
            prev,
            {
                "gate_output": "FAILED test_z",
                "guard_violations": [],
                "coverage_uncovered": [],
            },
        )
        is False
    )
    # THE BUG WE FIXED: same green gate ('ok'), DIFFERENT coverage rejection -> NOT a repeat
    cov1 = {"gate_output": "ok", "guard_violations": [], "coverage_uncovered": ["src/x.py:11"]}
    cov2 = {"gate_output": "ok", "guard_violations": [], "coverage_uncovered": ["src/x.py:42"]}
    assert is_repeated_failure([cov1], cov2) is False


# ---------------------------------------------------------------------------
# build_retry_prompt
# ---------------------------------------------------------------------------


def test_build_retry_prompt_embeds_prior_failure_output():
    item = {"title": "Fix X", "fix": "do Y"}
    p = build_retry_prompt(item, "BASE", [{"attempt": 1, "gate_output": "AssertionError: nope"}])
    assert re.search(r"BASE", p)
    assert re.search(r"Attempt 1 failed", p)
    assert re.search(r"AssertionError: nope", p)


def test_build_retry_prompt_surfaces_coverage_gap_with_explicit_add_a_test_instruction():
    item = {"title": "Harden parse", "fix": "validate input"}
    p = build_retry_prompt(
        item,
        "BASE",
        [
            {
                "attempt": 1,
                "gate_output": "ok",
                "guard_violations": [],
                "coverage_uncovered": ["src/x.py:11,12"],
            }
        ],
    )
    assert re.search(r"Coverage gap", p, re.IGNORECASE)
    assert re.search(r"src/x\.py:11,12", p)
    assert re.search(r"test", p, re.IGNORECASE)  # tells the implementer to add/extend a test


def test_build_retry_prompt_surfaces_guard_violations():
    item = {"title": "Fix", "fix": ""}
    p = build_retry_prompt(
        item,
        "BASE",
        [
            {
                "attempt": 1,
                "gate_output": "",
                "guard_violations": ["outside allowlist: secrets.py"],
                "coverage_uncovered": [],
            }
        ],
    )
    assert re.search(r"Guard|violation", p, re.IGNORECASE)
    assert re.search(r"outside allowlist: secrets\.py", p)


# ---------------------------------------------------------------------------
# append_lesson
# ---------------------------------------------------------------------------


def test_append_lesson_dedups_by_pattern():
    lessons = []
    lessons = append_lesson(lessons, {"pattern": "SecretStr mask", "fix": "get_secret_value()"})
    lessons = append_lesson(lessons, {"pattern": "SecretStr mask", "fix": "get_secret_value()"})
    assert len(lessons) == 1


# ---------------------------------------------------------------------------
# relevant_lessons
# ---------------------------------------------------------------------------


def test_relevant_lessons_injects_only_category_matching_lessons_ranked_and_capped():
    store = [
        {"id": "l1", "pattern": "p1", "fix": "f1", "confidence": 3,
         "category": "bug-fix", "status": "active"},
        {"id": "l2", "pattern": "p2", "fix": "f2", "confidence": 9,
         "category": "bug-fix", "status": "active"},
        {"id": "l3", "pattern": "p3", "fix": "f3", "confidence": 5,
         "category": "security", "status": "active"},
    ]
    ids = [le["id"] for le in relevant_lessons(store, {"category": "bug-fix"}, cap=5)]
    assert ids == ["l2", "l1"]
    assert len(relevant_lessons(store, {"category": "bug-fix"}, cap=1)) == 1  # capped


def test_unrelated_category_lesson_is_never_injected():
    store = [{"id": "l1", "pattern": "p", "fix": "f", "confidence": 9,
              "category": "security", "status": "active"}]
    assert relevant_lessons(store, {"category": "bug-fix"}) == []


# ---------------------------------------------------------------------------
# retract_lesson
# ---------------------------------------------------------------------------


def test_retract_lesson_drops_confidence_and_evicts_below_threshold():
    store = [{"id": "l1", "pattern": "p", "fix": "f", "confidence": 1,
              "category": "bug-fix", "status": "active"}]
    retract_lesson(store, "l1")
    assert store[0]["status"] == "evicted"  # 1 -> 0 -> evicted
    assert len(relevant_lessons(store, {"category": "bug-fix"})) == 0  # evicted not injected


# ---------------------------------------------------------------------------
# make_lessons_adapter
# ---------------------------------------------------------------------------


def test_lessons_adapter_relevant_and_retract_match_driver_contract():
    store = [{"id": "l1", "pattern": "p", "fix": "f", "confidence": 1,
              "category": "bug-fix", "status": "active"}]
    adapter = make_lessons_adapter(store, cap=5)
    item = {"id": "i1", "category": "bug-fix"}
    ids = [le["id"] for le in adapter.relevant(item)]
    assert ids == ["l1"]  # injected for matching item
    adapter.retract(item)  # item failed attributably
    assert store[0]["status"] == "evicted"  # applied lesson retracted + evicted
    assert adapter.relevant({"id": "i2", "category": "bug-fix"}) == []  # no longer injected
