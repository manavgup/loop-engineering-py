"""STATE and provenance persistence helpers (§8 / §6).

state.py keeps the in-memory shape {"items": {}, "last_good_sha": ...};
these functions read/write it as JSON so a halt/crash can resume.
Provenance is append-only JSONL so the audit trail is on disk and never lost.

No async here — unlike the Node originals, all callables are plain synchronous
functions (fs.readFileSync / writeFileSync / appendFileSync → open() / pathlib).
"""

from __future__ import annotations

import pathlib
from typing import Callable


def load_state(path: pathlib.Path | str) -> dict:
    """Load persisted state from *path*; return ``{"items": {}}`` if missing or unreadable."""
    raise NotImplementedError


def make_state_persister(path: pathlib.Path | str) -> Callable[[dict], None]:
    """Return a callable that writes *state* as pretty-printed JSON to *path*."""
    raise NotImplementedError


def make_provenance_writer(path: pathlib.Path | str) -> Callable[[dict], None]:
    """Return a callable that appends *record* as a single JSON line (JSONL) to *path*."""
    raise NotImplementedError
