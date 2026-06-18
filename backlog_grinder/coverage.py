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
    return NON_BEHAVIORAL.search(file) is None


def changed_lines(diff: str) -> dict[str, set[int]]:
    """Parse a unified diff and return {filename: set_of_added_line_numbers}."""
    result: dict[str, set[int]] = {}
    current = None
    line_no = 0
    for line in diff.splitlines():
        file_match = FILE_RE.match(line)
        if file_match:
            current = file_match.group(1)
            result[current] = set()
            continue
        hunk_match = HUNK_RE.match(line)
        if hunk_match:
            line_no = int(hunk_match.group(1))
            continue
        # Before any file header (e.g. a deletion's '+++ /dev/null', which FILE_RE
        # does not match) there is no current file — skip, never index result[None].
        if current is None:
            continue
        if line.startswith('+') and not line.startswith('+++'):
            result[current].add(line_no)
            line_no += 1
        elif not line.startswith('-'):
            line_no += 1
    return result


def check_coverage(diff: str, coverage: dict[str, set[int]]) -> dict:
    """Return {ok, uncovered} for changed behavioral lines missing coverage."""
    uncovered = []
    for file, lines in changed_lines(diff).items():
        covered = coverage.get(file, set())
        for line_no in sorted(lines):
            if is_behavioral(file) and line_no not in covered:
                uncovered.append({"file": file, "line": line_no})
    return {"ok": not uncovered, "uncovered": uncovered}
