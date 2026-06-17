"""Feedback utilities: failure fingerprinting, retry-prompt construction, lesson management.

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


# ---------------------------------------------------------------------------
# Constants (mirrors JS module-level consts)
# ---------------------------------------------------------------------------

_LESSON_CAP = 5
_EVICT_THRESHOLD = 0
_RETRACT_DROP = 1


# ---------------------------------------------------------------------------
# signature
# ---------------------------------------------------------------------------


def signature(gate_output: str) -> str:
    """Return a 12-hex-char SHA-1 of the normalised gate output (volatile bits stripped)."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# failure_fingerprint
# ---------------------------------------------------------------------------


def failure_fingerprint(record: dict) -> str:
    """Return a 12-hex-char SHA-1 of the full rejection reason (gate + guards + coverage).

    A failure's identity is the FULL rejection reason, not gate output alone: a coverage or
    scope rejection leaves the gate green, so keying on gate output would collapse two
    different rejections into a false "repeat" and abandon the item prematurely.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# is_repeated_failure
# ---------------------------------------------------------------------------


def is_repeated_failure(prev_records: list[dict], current_record: dict) -> bool:
    """Return True iff current_record's full fingerprint matches any record in prev_records."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# build_retry_prompt
# ---------------------------------------------------------------------------


def build_retry_prompt(item: dict, base_prompt: str, failures: list[dict] | None = None) -> str:
    """Build a retry prompt embedding prior failure details (gate, guards, coverage)."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# append_lesson
# ---------------------------------------------------------------------------


def append_lesson(lessons: list[dict], lesson: dict) -> list[dict]:
    """Return a new lessons list with lesson appended, deduplicated by pattern."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# relevant_lessons
# ---------------------------------------------------------------------------


def relevant_lessons(store: list[dict], item: dict, cap: int = _LESSON_CAP) -> list[dict]:
    """Return active lessons scoped to item's category, ranked by confidence, capped to cap."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# retract_lesson
# ---------------------------------------------------------------------------


def retract_lesson(store: list[dict], lesson_id: str) -> list[dict]:
    """Decrement confidence of lesson_id in store; evict it when confidence falls to threshold."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# make_lessons_adapter
# ---------------------------------------------------------------------------


def make_lessons_adapter(store: list[dict], *, cap: int = _LESSON_CAP) -> object:
    """Return an adapter exposing relevant(item) and retract(item)."""
    raise NotImplementedError
