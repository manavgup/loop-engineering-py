"""Backlog markdown parser — stubs only.

Public API:
  parse_backlog(markdown: str) -> list[dict]
  parse_path_ref(path_field: str) -> dict
  is_stale(item: dict, file_exists: callable) -> bool
"""


def parse_backlog(markdown: str) -> list:
    """Parse a markdown backlog into a list of item dicts."""
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
    """Split a path field (e.g. 'src/foo.py:12') into {file, line}."""
    file_part, _, line_part = path_field.rpartition(":")
    return {"file": file_part, "line": int(line_part.split("-")[0])}


def is_stale(item: dict, file_exists) -> bool:
    """Return True when the item's referenced file no longer exists."""
    path = item.get("path", "")
    if not path:
        return True
    return not file_exists(parse_path_ref(path)["file"])
