"""Coverage utilities: identify changed source lines and check execution coverage."""
import re

# Matches a unified-diff hunk header; group 1 = new-file start line, group 2 = length (optional).
HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')

# Matches the "+++ b/<path>" line that names the new version of a file.
FILE_RE = re.compile(r'^\+\+\+ b\/(.+)$')

# Non-behavioral file extensions: docs, config, lock files.
# Changes to these files don't need test coverage.
NON_BEHAVIORAL = re.compile(r'\.(md|txt|rst|json|ya?ml|toml|ini|cfg|lock)$', re.IGNORECASE)


def is_behavioral(file: str) -> bool:
    """Return True if the file is a behavioral (source code) file that needs coverage."""
    raise NotImplementedError


def changed_lines(diff: str) -> dict[str, set[int]]:
    """Parse a unified diff and return {filename: set_of_added_line_numbers}."""
    raise NotImplementedError


def check_coverage(diff: str, coverage: dict[str, set[int]]) -> dict:
    """Return {ok, uncovered} for changed behavioral lines missing coverage."""
    raise NotImplementedError
