# SPDX-License-Identifier: MIT
"""State and provenance persistence helpers (§8 / §6).

Location: backlog_grinder/persist.py
Authors: Manav Gupta

State is kept in memory as ``{"items": {}, "last_good_sha": ...}``; these
functions read and write it as JSON so a halt or crash can resume cleanly.
Provenance is written as append-only JSONL so the audit trail is durable and
never lost.  All callables are plain synchronous functions built on
``pathlib.Path`` I/O.
"""

from __future__ import annotations

import json
import pathlib
from typing import Callable


def load_state(path: pathlib.Path | str) -> dict:
    """Load persisted state from *path*, returning a default dict if absent.

    Args:
        path: Filesystem path to the JSON state file.

    Returns:
        The parsed state dict, or ``{"items": {}}`` if *path* does not exist
        or cannot be read.
    """
    path = pathlib.Path(path)
    if not path.exists():
        return {"items": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def make_state_persister(path: pathlib.Path | str) -> Callable[[dict], None]:
    """Return a callable that writes state as pretty-printed JSON to *path*.

    Parent directories are created automatically if they do not exist.

    Args:
        path: Filesystem path where the JSON state file should be written.

    Returns:
        A callable ``(state: dict) -> None`` that serialises *state* with a
        two-space indent and writes it atomically to *path*.
    """
    path = pathlib.Path(path)

    def save(state: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return save


def make_provenance_writer(path: pathlib.Path | str) -> Callable[[dict], None]:
    """Return a callable that appends a record as a single JSON line to *path*.

    Parent directories are created automatically if they do not exist.  Each
    call appends exactly one newline-terminated JSON object, maintaining a valid
    JSONL file.

    Args:
        path: Filesystem path to the JSONL provenance file.

    Returns:
        A callable ``(record: dict) -> None`` that serialises *record* and
        appends it to *path*.
    """
    path = pathlib.Path(path)

    def write(record: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    return write
