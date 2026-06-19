# SPDX-License-Identifier: MIT
"""Backlog markdown parser — converts raw markdown to structured item dicts.

Location: backlog_grinder/parse.py
Authors: Manav Gupta

Provides three public helpers:

* ``parse_backlog`` — full document parser that returns every checklist item.
* ``parse_path_ref`` — splits a ``file:line`` reference into its components.
* ``is_stale`` — decides whether an item's source file still exists.
"""


def parse_backlog(markdown: str) -> list:
    """Parse a markdown backlog document into a list of item dicts.

    Scans the document line-by-line, tracking the current severity (``###``
    heading) and category (``####`` heading).  Each checklist row matching the
    canonical format is turned into a dict; trailing *Evidence* and *Fix*
    sub-bullets are attached to the most-recently-created item.

    Args:
        markdown: Full text of the backlog markdown document.

    Returns:
        A list of dicts, one per checklist item, each containing:
        ``title``, ``path``, ``effort``, ``severity``, ``category``,
        ``evidence``, ``fix``, ``checked`` (bool), and ``id`` (12-char hex).
    """
    import hashlib
    import re

    items = []
    severity = ""
    category = ""
    for line in markdown.splitlines():
        crit = re.match(r"^###\s+\S+\s+([A-Za-z]+)", line)
        if crit:
            severity = crit.group(1).lower()
        cat = re.match(r"^####\s+(.+)", line)
        if cat:
            category = cat.group(1).strip()
        row = re.match(r"^- \[([ xX])\]\s+\*\*(.+?)\*\*.*?`(.+?)`.*?_([^_]+)_", line)
        if row:
            item = {}
            item["title"] = row.group(2)
            item["path"] = row.group(3)
            item["effort"] = row.group(4).split("/")[0]
            item["severity"] = severity
            item["category"] = category
            item["evidence"] = ""
            item["fix"] = ""
            item["checked"] = row.group(1).strip().lower() == "x"
            item["id"] = hashlib.sha256((row.group(2) + row.group(3)).encode()).hexdigest()[:12]
            items.append(item)
        evid = re.match(r"^\s+- _Evidence:_\s+(.+)", line)
        if evid:
            items[-1]["evidence"] = evid.group(1).strip()
        fix = re.match(r"^\s+- _Fix:_\s+(.+)", line)
        if fix:
            items[-1]["fix"] = fix.group(1).strip()
    return items


def parse_path_ref(path_field: str) -> dict:
    """Split a ``file:line`` path field into a dict with ``file`` and ``line`` keys.

    Args:
        path_field: A string of the form ``"src/foo.py:12"`` or
            ``"src/foo.py:12-34"`` (range — only the start line is kept).

    Returns:
        A dict ``{"file": str, "line": int}`` where ``line`` is the integer
        start of the referenced line range.

    Examples:
        >>> parse_path_ref("backend/openai.py:46")
        {'file': 'backend/openai.py', 'line': 46}
        >>> parse_path_ref("src/foo.py:12-34")
        {'file': 'src/foo.py', 'line': 12}
    """
    file_part, _, line_part = path_field.rpartition(":")
    return {"file": file_part, "line": int(line_part.split("-")[0])}


def is_stale(item: dict, file_exists) -> bool:
    """Return True when the item's referenced file no longer exists.

    Args:
        item: A backlog item dict containing at least a ``"path"`` key whose
            value is a ``file:line`` reference string (may be empty).
        file_exists: A callable ``(filename: str) -> bool`` that returns
            ``True`` when the given filename is accessible on disk.

    Returns:
        ``True`` if the path field is empty or the referenced file is absent;
        ``False`` otherwise.

    Examples:
        >>> is_stale({"path": "gone.py:1"}, lambda f: False)
        True
        >>> is_stale({"path": ""}, lambda f: True)
        True
        >>> is_stale({"path": "exists.py:1"}, lambda f: True)
        False
    """
    path = item.get("path", "")
    if not path:
        return True
    return not file_exists(parse_path_ref(path)["file"])
