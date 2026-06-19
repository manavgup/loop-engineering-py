"""Adapters for reading LCOV and Cobertura XML coverage reports into a common dict shape."""

import os
import xml.etree.ElementTree as ET


def parse_lcov(text: str) -> dict[str, set[int]]:
    """Parse an LCOV text report and return {filename: set_of_executed_line_numbers}."""
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
    """Parse a Cobertura XML report and return {filename: set_of_hit_line_numbers}."""
    root = ET.fromstring(text)
    files: dict[str, set[int]] = {}
    for cls in root.iter("class"):
        lines = files.setdefault(cls.get("filename"), set())
        for line in cls.iter("line"):
            if int(line.get("hits")) > 0:
                lines.add(int(line.get("number")))
    return files


def parse_cobertura_executable(text: str) -> dict[str, set[int]]:
    """Return {filename: set_of_listed_line_numbers} — every line the report lists (hit OR miss).

    These are the lines coverage.py considers executable. Lines absent from this set are
    NON-executable (docstrings, blanks, multi-line-literal continuations) and can never be
    "executed by a test".
    """
    root = ET.fromstring(text)
    files: dict[str, set[int]] = {}
    for cls in root.iter("class"):
        lines = files.setdefault(cls.get("filename"), set())
        for line in cls.iter("line"):
            lines.add(int(line.get("number")))
    return files


def cobertura_sources(text: str) -> list[str]:
    """Extract the list of <source> root paths from a Cobertura XML string."""
    root = ET.fromstring(text)
    return [source.text for source in root.iter("source")]


def _remap(flat: dict[str, set[int]], root: str, repo_cwd: str) -> dict[str, set[int]]:
    """Make cobertura filenames repo-relative so keys match what ``git diff`` emits.

    realpath both sides: coverage.py writes the resolved <source> path (e.g. /private/var/...
    on macOS) while repo_cwd may be the symlink (/var/...); without resolving, relpath yields
    a bogus ../../ key.
    """
    out: dict[str, set[int]] = {}
    for name, lines in flat.items():
        abs_name = os.path.realpath(os.path.join(root, name))
        out[os.path.relpath(abs_name, os.path.realpath(repo_cwd))] = lines
    return out


def _augment_non_executable(
    hit: dict[str, set[int]], executable: dict[str, set[int]], repo_cwd: str
) -> None:
    """Mark every NON-executable source line (not listed by the report) as covered.

    Coverage-of-change requires every changed line to be executed, but trace-based coverage
    (coverage.py) reports only executable statements — a whole-file diff's docstrings/blanks/
    continuations would otherwise be flagged uncovered though no test could ever execute them.
    Executable-but-unhit lines are left out, so they stay real coverage gaps.
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
    """Load a coverage report from *file* and return {filename: set_of_executed_line_numbers}.

    *format* must be ``"lcov"`` or ``"cobertura"``.  When *repo_cwd* is given, Cobertura
    filenames (relative to the ``<source>`` root) are remapped to repo-relative paths and
    non-executable source lines are treated as satisfied (see :func:`_augment_non_executable`).
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
