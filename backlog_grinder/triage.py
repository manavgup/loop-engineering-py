"""
Triage module: summarise backlog items and render loop-state markdown.

Deny is injected, never hardcoded (concept §7 — no module carries assumptions).
Segment match so 'auth' flags backend/auth/x.py but not backend/oauth_helper.py.
"""


def summarize(items: list[dict]) -> dict:
    """Return totals (total, stale, queueable) and breakdowns by_severity / by_category."""
    raise NotImplementedError


def to_state_markdown(items: list[dict], options: dict | None = None) -> str:
    """Render the full loop-state markdown document for the given items and options dict."""
    raise NotImplementedError
