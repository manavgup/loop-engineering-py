"""Backlog markdown parser — stubs only.

Public API:
  parse_backlog(markdown: str) -> list[dict]
  parse_path_ref(path_field: str) -> dict
  is_stale(item: dict, file_exists: callable) -> bool
"""


def parse_backlog(markdown: str) -> list:
    """Parse a markdown backlog into a list of item dicts."""
    raise NotImplementedError


def parse_path_ref(path_field: str) -> dict:
    """Split a path field (e.g. 'src/foo.py:12') into {file, line}."""
    raise NotImplementedError


def is_stale(item: dict, file_exists) -> bool:
    """Return True when the item's referenced file no longer exists."""
    raise NotImplementedError
