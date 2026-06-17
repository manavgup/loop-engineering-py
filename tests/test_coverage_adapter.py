"""Pytest port of coverage-adapter.test.mjs — faithful behavioral port, synchronous, PEP-8."""
import os
import tempfile

from backlog_grinder.coverage_adapter import (
    cobertura_sources,
    load_coverage,
    parse_cobertura,
    parse_lcov,
)


def test_parse_lcov_maps_executed_lines_per_file_count_gt_0_only():
    lcov = "SF:src/x.js\nDA:1,1\nDA:2,0\nDA:3,5\nend_of_record\n"
    c = parse_lcov(lcov)
    assert sorted(c["src/x.js"]) == [1, 3]


def test_parse_cobertura_maps_hit_lines_per_file():
    xml = (
        "<coverage><packages><package><classes>"
        '<class filename="src/x.py"><lines>'
        '<line number="10" hits="1"/>'
        '<line number="11" hits="0"/>'
        '<line number="12" hits="3"/>'
        "</lines></class></classes></package></packages></coverage>"
    )
    c = parse_cobertura(xml)
    assert sorted(c["src/x.py"]) == [10, 12]


def test_load_coverage_remaps_cobertura_filenames_against_source_to_repo_relative_paths():
    # coverage.py `--cov=mathy` from repo root /repo yields filename="ops.py"
    # under source=/repo/mathy.  load_coverage must remap to "mathy/ops.py" so
    # the result key matches what `git diff` emits (repo-relative path).
    with tempfile.TemporaryDirectory(prefix="bg-cov-") as tmpdir:
        repo_cwd = os.path.join(tmpdir, "repo")
        source_root = os.path.join(repo_cwd, "mathy")
        xml = (
            "<coverage>"
            "<sources><source>" + source_root + "</source></sources>"
            "<packages><package><classes>"
            '<class filename="ops.py"><lines>'
            '<line number="2" hits="1"/>'
            "</lines></class></classes></package></packages>"
            "</coverage>"
        )
        cov_file = os.path.join(tmpdir, "cov.xml")
        with open(cov_file, "w") as f:
            f.write(xml)

        # cobertura_sources must extract the full absolute source path
        assert cobertura_sources(xml) == [source_root]

        cov = load_coverage(format="cobertura", file=cov_file, repo_cwd=repo_cwd)

        # key is now repo-relative 'mathy/ops.py', matching what `git diff` emits
        assert cov.get("mathy/ops.py"), "expected repo-relative key mathy/ops.py"
        assert sorted(cov["mathy/ops.py"]) == [2]
