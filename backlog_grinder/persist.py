"""STATE and provenance persistence helpers (§8 / §6).

state.py keeps the in-memory shape {"items": {}, "last_good_sha": ...};
these functions read/write it as JSON so a halt/crash can resume.
Provenance is append-only JSONL so the audit trail is on disk and never lost.

All callables are plain synchronous
functions (fs.readFileSync / writeFileSync / appendFileSync → open() / pathlib).
"""

from __future__ import annotations

import json
import pathlib
from typing import Callable


def load_state(path: pathlib.Path | str) -> dict:
    """Load persisted state from *path*; return ``{"items": {}}`` if missing or unreadable."""
    path = pathlib.Path(path)
    if not path.exists():
        return {"items": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def make_state_persister(path: pathlib.Path | str) -> Callable[[dict], None]:
    """Return a callable that writes *state* as pretty-printed JSON to *path*."""
    path = pathlib.Path(path)

    def save(state: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return save


def make_provenance_writer(path: pathlib.Path | str) -> Callable[[dict], None]:
    """Return a callable that appends *record* as a single JSON line (JSONL) to *path*."""
    path = pathlib.Path(path)

    def write(record: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    return write
