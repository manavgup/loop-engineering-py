# SPDX-License-Identifier: MIT
"""Feedback utilities: failure fingerprinting, retry-prompt construction, lesson management.

Location: backlog_grinder/feedback.py
Authors: Manav Gupta

Canonical dict shapes
---------------------
failure record:
  {item_id, attempt, gate_output, guard_violations: [str], coverage_ok: bool,
   coverage_uncovered: [str], verifier_verdict, diff_summary}

lesson:
  {id, pattern, fix, confidence: int, source_item_id, status: "active"|"evicted", category}

item:
  {id, title, path, status, attempts, failures, fix, category}
"""

import hashlib
import re

# ---------------------------------------------------------------------------
# Constants (mirrors JS module-level consts)
# ---------------------------------------------------------------------------

_LESSON_CAP = 5
_EVICT_THRESHOLD = 0
_RETRACT_DROP = 1

# Volatile bits that must not contribute to a failure's identity.
_HEX_ADDR = re.compile(r"0x[0-9a-fA-F]+")
_DURATION = re.compile(r"\d+(?:\.\d+)?s\b")


def _normalize(text: str) -> str:
    """Strip volatile bits (memory addresses, timings) so repeated failures match."""
    text = _HEX_ADDR.sub("0xADDR", text)
    return _DURATION.sub("DURs", text)


# ---------------------------------------------------------------------------
# signature
# ---------------------------------------------------------------------------


def signature(gate_output: str) -> str:
    """Return a 12-hex-char SHA-1 of the normalised gate output (volatile bits stripped).

    Args:
        gate_output: Raw string output from the gate (may contain addresses/timings).

    Returns:
        A 12-character lowercase hex string identifying the normalised gate output.

    Examples:
        >>> signature("Error: test failed")
        '7e2e6ec17da5'
        >>> signature("Error at 0x7fff1234 took 1.23s")
        '580145bbce7f'
    """
    return hashlib.sha1(_normalize(gate_output).encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# failure_fingerprint
# ---------------------------------------------------------------------------


def failure_fingerprint(record: dict) -> str:
    """Return a 12-hex-char SHA-1 of the full rejection reason (gate + guards + coverage).

    A failure's identity is the FULL rejection reason, not gate output alone: a coverage or
    scope rejection leaves the gate green, so keying on gate output would collapse two
    different rejections into a false "repeat" and abandon the item prematurely.

    Args:
        record: Failure record dict containing ``gate_output`` (str),
            ``guard_violations`` (list[str]), and ``coverage_uncovered`` (list[str]).

    Returns:
        A 12-character lowercase hex string identifying the full rejection reason.

    Examples:
        >>> failure_fingerprint(
        ...     {"gate_output": "FAIL: assertion error",
        ...      "guard_violations": [], "coverage_uncovered": []}
        ... )
        '1b6899112f81'
    """
    parts = [
        _normalize(record["gate_output"]),
        "|".join(record["guard_violations"]),
        "|".join(record["coverage_uncovered"]),
    ]
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# is_repeated_failure
# ---------------------------------------------------------------------------


def is_repeated_failure(prev_records: list[dict], current_record: dict) -> bool:
    """Return True iff current_record's full fingerprint matches any record in prev_records.

    Args:
        prev_records: List of prior failure record dicts to compare against.
        current_record: The new failure record dict being evaluated.

    Returns:
        True if the current record's fingerprint matches any previous record; False otherwise.
    """
    fingerprint = failure_fingerprint(current_record)
    return any(failure_fingerprint(record) == fingerprint for record in prev_records)


# ---------------------------------------------------------------------------
# build_retry_prompt
# ---------------------------------------------------------------------------


def build_retry_prompt(item: dict, base_prompt: str, failures: list[dict] | None = None) -> str:
    """Build a retry prompt embedding prior failure details (gate, guards, coverage).

    Args:
        item: The backlog item dict (currently unused, reserved for future context).
        base_prompt: The original prompt string to prepend before failure details.
        failures: List of failure record dicts from prior attempts; defaults to None.

    Returns:
        A newline-joined string combining base_prompt with per-attempt failure summaries.
    """
    lines = [base_prompt]
    for failure in failures:
        lines.append(f"Attempt {failure['attempt']} failed")
        gate_output = failure.get("gate_output", "")
        if gate_output:
            lines.append(gate_output)
        for violation in failure.get("guard_violations", []):
            lines.append(f"Guard violation: {violation}")
        for uncovered in failure.get("coverage_uncovered", []):
            lines.append(f"Coverage gap: {uncovered} — add or extend a test that covers it")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# append_lesson
# ---------------------------------------------------------------------------


def append_lesson(lessons: list[dict], lesson: dict) -> list[dict]:
    """Return a new lessons list with lesson appended, deduplicated by pattern.

    Args:
        lessons: Existing list of lesson dicts.
        lesson: New lesson dict to append (skipped if its pattern already exists).

    Returns:
        A new list containing all original lessons plus the new lesson, or the
        original list unchanged if the pattern was already present.
    """
    if any(existing["pattern"] == lesson["pattern"] for existing in lessons):
        return lessons
    return lessons + [lesson]


# ---------------------------------------------------------------------------
# relevant_lessons
# ---------------------------------------------------------------------------


def relevant_lessons(store: list[dict], item: dict, cap: int = _LESSON_CAP) -> list[dict]:
    """Return active lessons scoped to item's category, ranked by confidence, capped to cap.

    Args:
        store: Full list of lesson dicts (may include evicted lessons).
        item: Backlog item dict; its ``category`` field filters matching lessons.
        cap: Maximum number of lessons to return.

    Returns:
        A list of up to ``cap`` active lesson dicts matching item's category,
        sorted by confidence descending.
    """
    matches = [
        lesson
        for lesson in store
        if lesson["status"] == "active" and lesson["category"] == item["category"]
    ]
    matches.sort(key=lambda lesson: lesson["confidence"], reverse=True)
    return matches[:cap]


# ---------------------------------------------------------------------------
# retract_lesson
# ---------------------------------------------------------------------------


def retract_lesson(store: list[dict], lesson_id: str) -> list[dict]:
    """Decrement confidence of lesson_id in store; evict it when confidence falls to threshold.

    Args:
        store: List of lesson dicts (mutated in place for the matched lesson).
        lesson_id: The ``id`` value of the lesson to retract.

    Returns:
        The same store list with the matched lesson's confidence decremented
        (and status set to ``"evicted"`` if confidence reaches the eviction threshold).
    """
    for lesson in store:
        if lesson["id"] == lesson_id:
            lesson["confidence"] -= _RETRACT_DROP
            if lesson["confidence"] <= _EVICT_THRESHOLD:
                lesson["status"] = "evicted"
    return store


# ---------------------------------------------------------------------------
# make_lessons_adapter
# ---------------------------------------------------------------------------


def make_lessons_adapter(store: list[dict], *, cap: int = _LESSON_CAP) -> object:
    """Return an adapter exposing relevant(item) and retract(item).

    Args:
        store: The shared lesson store list to read from and mutate.
        cap: Maximum number of lessons to surface per item.

    Returns:
        An object with two methods:

        - ``relevant(item)`` — returns active lessons for item's category (up to ``cap``),
          recording which lesson IDs were applied.
        - ``retract(item)`` — decrements confidence for every lesson previously applied
          to item via ``relevant()``.
    """
    applied: dict[str, list[str]] = {}

    class _LessonsAdapter:
        def relevant(self, item: dict) -> list[dict]:
            lessons = relevant_lessons(store, item, cap)
            applied[item["id"]] = [lesson["id"] for lesson in lessons]
            return lessons

        def retract(self, item: dict) -> None:
            for lesson_id in applied.get(item["id"], []):
                retract_lesson(store, lesson_id)

    return _LessonsAdapter()
