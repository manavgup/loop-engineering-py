# SPDX-License-Identifier: MIT
"""Triage module: summarise backlog items and render loop-state markdown.

Location: backlog_grinder/triage.py
Authors: Manav Gupta

Deny-list is injected at call time via the *options* dict, never hardcoded
(concept §7 — no module carries assumptions).  Path segment matching ensures
that ``"auth"`` flags ``backend/auth/x.py`` but not ``backend/oauth_helper.py``.
"""


def summarize(items: list[dict]) -> dict:
    """Return aggregate counts and per-field breakdowns for a list of backlog items.

    Args:
        items: A list of backlog item dicts.  Each dict must contain
            ``"severity"`` (str), ``"category"`` (str), and ``"stale"`` (bool).

    Returns:
        A dict with the following keys:

        - ``"total"`` — total number of items.
        - ``"stale"`` — count of items whose ``stale`` flag is truthy.
        - ``"queueable"`` — ``total - stale``.
        - ``"by_severity"`` — ``{severity: count}`` mapping.
        - ``"by_category"`` — ``{category: count}`` mapping.
    """
    by_severity: dict = {}
    by_category: dict = {}
    stale = 0
    for item in items:
        severity = item["severity"]
        by_severity[severity] = by_severity.get(severity, 0) + 1
        category = item["category"]
        by_category[category] = by_category.get(category, 0) + 1
        if item["stale"]:
            stale += 1
    return {
        "total": len(items),
        "stale": stale,
        "queueable": len(items) - stale,
        "by_severity": by_severity,
        "by_category": by_category,
    }


def to_state_markdown(items: list[dict], options: dict | None = None) -> str:
    """Render the full loop-state markdown document for a list of backlog items.

    Non-stale items are placed under the ``## Queue`` heading as unchecked
    checkboxes.  Stale items are collected under
    ``## Stale / needs human re-validation``.  Any non-stale item whose path
    contains a segment that appears in the deny-list receives a
    ``[DENYLIST: human gate]`` suffix.

    Args:
        items: A list of backlog item dicts.  Each dict must contain
            ``"id"`` (str), ``"title"`` (str), ``"path"`` (str), and
            ``"stale"`` (bool).
        options: Optional configuration dict.  Recognised keys:

            - ``"project_name"`` (str) — used in the document heading.
            - ``"deny"`` (list[str]) — path segments that trigger the denylist
              label; defaults to an empty list.

    Returns:
        A single string containing the rendered markdown document.
    """
    options = options or {}
    deny = options.get("deny", [])
    lines = ["# Loop State — " + options.get("project_name", ""), "", "## Queue", ""]
    stale_lines = []
    for item in items:
        label = item["id"] + " — " + item["title"]
        if item["stale"]:
            stale_lines.append("- " + label)
            continue
        if any(segment in item["path"].split("/") for segment in deny):
            label += " [DENYLIST: human gate]"
        lines.append("- [ ] " + label)
    lines += ["", "## Stale / needs human re-validation", ""]
    lines += stale_lines
    return "\n".join(lines)
