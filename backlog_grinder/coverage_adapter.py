"""Adapters for reading LCOV and Cobertura XML coverage reports into a common dict shape."""


def parse_lcov(text: str) -> dict[str, set[int]]:
    """Parse an LCOV text report and return {filename: set_of_executed_line_numbers}."""
    raise NotImplementedError


def parse_cobertura(text: str) -> dict[str, set[int]]:
    """Parse a Cobertura XML report and return {filename: set_of_hit_line_numbers}."""
    raise NotImplementedError


def cobertura_sources(text: str) -> list[str]:
    """Extract the list of <source> root paths from a Cobertura XML string."""
    raise NotImplementedError


def load_coverage(*, format: str, file: str, repo_cwd: str | None = None) -> dict[str, set[int]]:
    """Load a coverage report from *file* and return {filename: set_of_executed_line_numbers}.

    *format* must be ``"lcov"`` or ``"cobertura"``.  When *repo_cwd* is given, Cobertura
    filenames (which are relative to the ``<source>`` root, not the repo root) are remapped
    so that keys match the repo-relative paths emitted by ``git diff``.
    """
    raise NotImplementedError
