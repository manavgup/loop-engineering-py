"""Provenance (§6): every approved commit emits a machine-generated audit record
so "why did the system make this edit and what did it check" is answerable from
disk without re-running anything.

make_record builds the §6 record from the item + the run artifacts.
append_record stores it append-only (one record per commit).
The clock is injected so the timestamp is deterministic in tests.
"""


def make_record(item, opts=None, *, clock=None):
    """Build a §6 provenance audit record from an item and run artifacts.

    Returns a dict with all §6 fields in snake_case.
    """
    raise NotImplementedError


def append_record(store, record):
    """Return a new list with *record* appended to *store* (append-only, no mutation)."""
    raise NotImplementedError
