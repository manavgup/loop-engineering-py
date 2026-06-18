"""Make a coverage.py cobertura report safe for the grinder's coverage-of-change.

The harness requires every *changed* line in the git diff to appear as executed
in the coverage map. coverage.py (trace-based) only lists EXECUTABLE statement
lines, so a whole-file diff's docstrings, blank lines, and multi-line-literal
continuations are absent and get flagged "uncovered" — even though such lines
can never be "executed by a test." (V8/lcov, being range-based, covers those
lines implicitly, which is why the Node original never hit this.)

This post-processor marks every NON-executable physical line (any line the
cobertura report does not already list) as hit=1, so coverage-of-change only
gates genuine executable statements. Executable-but-unhit lines are left at
hits=0 — real coverage gaps still fail the gate.

Usage: python3 port/cov-fixup.py coverage.xml
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _resolve(filename, sources):
    cand = Path(filename)
    if cand.exists():
        return cand
    for src in sources:
        p = Path(src) / filename
        if p.exists():
            return p
    return None


def fixup(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    sources = [s.text for s in root.findall(".//sources/source") if s.text]
    for cls in root.iter("class"):
        filename = cls.get("filename")
        if not filename:
            continue
        path = _resolve(filename, sources)
        lines_el = cls.find("lines")
        if path is None or lines_el is None:
            continue
        with open(path, "rb") as fh:
            total = sum(1 for _ in fh)
        listed = {int(le.get("number")) for le in lines_el.findall("line")}
        for n in range(1, total + 1):
            if n not in listed:
                ET.SubElement(lines_el, "line", number=str(n), hits="1")
    tree.write(xml_path)


if __name__ == "__main__":
    fixup(sys.argv[1])
