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


def cobertura_sources(text: str) -> list[str]:
    """Extract the list of <source> root paths from a Cobertura XML string."""
    root = ET.fromstring(text)
    return [source.text for source in root.iter("source")]


def load_coverage(*, format: str, file: str, repo_cwd: str | None = None) -> dict[str, set[int]]:
    """Load a coverage report from *file* and return {filename: set_of_executed_line_numbers}.

    *format* must be ``"lcov"`` or ``"cobertura"``.  When *repo_cwd* is given, Cobertura
    filenames (which are relative to the ``<source>`` root, not the repo root) are remapped
    so that keys match the repo-relative paths emitted by ``git diff``.
    """
    with open(file) as handle:
        text = handle.read()
    parsers = {"lcov": parse_lcov, "cobertura": parse_cobertura}
    coverage = parsers[format](text)
    sources = cobertura_sources(text) if repo_cwd is not None else []
    root = sources[0] if sources else ""
    remapped: dict[str, set[int]] = {}
    for name, lines in coverage.items():
        if repo_cwd is not None:
            # realpath both sides: coverage.py writes the resolved <source> path
            # (e.g. /private/var/... on macOS) while repo_cwd may be the symlink
            # (/var/...); without resolving, relpath yields a bogus ../../ key.
            abs_name = os.path.realpath(os.path.join(root, name))
            name = os.path.relpath(abs_name, os.path.realpath(repo_cwd))
        remapped[name] = lines
    return remapped
