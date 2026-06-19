# SPDX-License-Identifier: MIT
"""Adapters for reading LCOV and Cobertura XML coverage reports into a common dict shape.

Location: backlog_grinder/coverage_adapter.py
Authors: Manav Gupta

All public functions return ``{filename: set_of_line_numbers}`` dicts so the
rest of the harness can reason about coverage in a format-agnostic way.
``load_coverage`` is the main entry point; the individual ``parse_*`` and
``cobertura_sources`` functions are exposed for testing.
"""

import os
import xml.etree.ElementTree as ET


def parse_lcov(text: str) -> dict[str, set[int]]:
    """Parse an LCOV text report into a mapping of filename to executed line numbers.

    Args:
        text: Raw LCOV report content as a string.

    Returns:
        A dict mapping each source filename to the set of line numbers that were
        executed at least once (``DA`` count > 0).
    """
    files: dict[str, set[int]] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("SF:"):
            current = line[3:]
            files[current] = set()
        elif line.startswith("DA:"):
            number, count = line[3:].split(",")
            if int(count) > 0:
                files[current].add(int(number))
    return files


def parse_cobertura(text: str) -> dict[str, set[int]]:
    """Parse a Cobertura XML report into a mapping of filename to hit line numbers.

    Args:
        text: Raw Cobertura XML report content as a string.

    Returns:
        A dict mapping each source filename to the set of line numbers whose
        ``hits`` attribute is greater than zero.
    """
    root = ET.fromstring(text)
    files: dict[str, set[int]] = {}
    for cls in root.iter("class"):
        lines = files.setdefault(cls.get("filename"), set())
        for line in cls.iter("line"):
            if int(line.get("hits")) > 0:
                lines.add(int(line.get("number")))
    return files


def parse_cobertura_executable(text: str) -> dict[str, set[int]]:
    """Parse a Cobertura XML report into a mapping of filename to all listed line numbers.

    Every line the report lists is considered executable (hit OR miss).  Lines
    absent from this set are NON-executable (docstrings, blanks, multi-line-literal
    continuations) and can never be "executed by a test".

    Args:
        text: Raw Cobertura XML report content as a string.

    Returns:
        A dict mapping each source filename to the set of all line numbers the
        report records, regardless of hit count.
    """
    root = ET.fromstring(text)
    files: dict[str, set[int]] = {}
    for cls in root.iter("class"):
        lines = files.setdefault(cls.get("filename"), set())
        for line in cls.iter("line"):
            lines.add(int(line.get("number")))
    return files


def cobertura_sources(text: str) -> list[str]:
    """Extract the list of ``<source>`` root paths from a Cobertura XML string.

    Args:
        text: Raw Cobertura XML report content as a string.

    Returns:
        A list of source-root path strings in document order.
    """
    root = ET.fromstring(text)
    return [source.text for source in root.iter("source")]


def _remap(flat: dict[str, set[int]], root: str, repo_cwd: str) -> dict[str, set[int]]:
    """Make cobertura filenames repo-relative so keys match what ``git diff`` emits.

    Resolves both sides with ``os.path.realpath`` because coverage.py writes the
    resolved ``<source>`` path (e.g. ``/private/var/...`` on macOS) while
    ``repo_cwd`` may be a symlink (``/var/...``); without resolving, ``relpath``
    yields a bogus ``../../`` key.
    """
    out: dict[str, set[int]] = {}
    for name, lines in flat.items():
        abs_name = os.path.realpath(os.path.join(root, name))
        out[os.path.relpath(abs_name, os.path.realpath(repo_cwd))] = lines
    return out


def _augment_non_executable(
    hit: dict[str, set[int]], executable: dict[str, set[int]], repo_cwd: str
) -> None:
    """Mark every non-executable source line as covered in-place.

    Coverage-of-change requires every changed line to be executed, but
    trace-based coverage (coverage.py) reports only executable statements.  A
    whole-file diff's docstrings, blanks, and continuation lines would otherwise
    be flagged as uncovered even though no test could ever execute them.
    Executable-but-unhit lines are left out so they remain real coverage gaps.
    """
    for name, exec_lines in executable.items():
        try:
            with open(os.path.join(repo_cwd, name), "rb") as handle:
                total = sum(1 for _ in handle)
        except OSError:
            continue  # source unreadable -> best-effort, leave hit-only
        covered = hit.setdefault(name, set())
        covered.update(n for n in range(1, total + 1) if n not in exec_lines)


def load_coverage(*, format: str, file: str, repo_cwd: str | None = None) -> dict[str, set[int]]:
    """Load a coverage report from *file* and return a filename-to-lines mapping.

    Args:
        format: Coverage report format; must be ``"lcov"``, ``"cobertura"``, or
            ``"coveragepy"`` (alias for ``"cobertura"``).
        file: Path to the coverage report file on disk.
        repo_cwd: Optional path to the repository root.  When provided for
            Cobertura reports, filenames are remapped to repo-relative paths and
            non-executable source lines are treated as satisfied (see
            ``_augment_non_executable``).

    Returns:
        A dict mapping each source filename to the set of line numbers that were
        executed (or are non-executable and therefore implicitly satisfied).

    Raises:
        ValueError: If *format* is not one of the supported values.
        OSError: If *file* cannot be opened for reading.
    """
    with open(file) as handle:
        text = handle.read()
    if format == "lcov":
        return parse_lcov(text)
    if format not in ("cobertura", "coveragepy"):
        raise ValueError(f"unknown coverage format: {format}")
    hit = parse_cobertura(text)
    if repo_cwd is None:
        return hit
    sources = cobertura_sources(text)
    root = sources[0] if sources else ""
    hit = _remap(hit, root, repo_cwd)
    executable = _remap(parse_cobertura_executable(text), root, repo_cwd)
    _augment_non_executable(hit, executable, repo_cwd)
    return hit
