"""The exit criterion of phase 1: examples/habit-tracker gives the results the POC gave.

The POC reported `0 error(s), 0 warning(s), 15 nodes` and up-to-date views for the example,
and the failures in its README when the example is broken on purpose. Two of those four
failures (bondstone/immutable and the diff rule) compare with a base commit and arrive with
the git layer; the other two are pinned here. The dates are pinned too, because the example
profile has a waiver that expires."""

import datetime as dt
import json
import shutil
from pathlib import Path

import pytest
from conftest import EXAMPLE
from test_cli import assert_golden

from bondstone.config import load_config
from bondstone.format import to_json, to_text
from bondstone.graph import build_graph
from bondstone.rules import fails, run_check
from bondstone.views import generate, stale_views

TODAY = dt.date(2026, 11, 10)


def check(root: Path):
    cfg = load_config(root)
    assert cfg.problems == []
    graph = build_graph(cfg)
    return run_check(cfg, graph, today=TODAY), len(graph.nodes)


def test_example_is_clean_with_fifteen_nodes():
    diagnostics, nodes = check(EXAMPLE)
    assert to_text(diagnostics, nodes) == "✓ 0 error(s), 0 warning(s), 15 nodes\n"
    assert json.loads(to_json(diagnostics, nodes)) == {
        "version": 1, "summary": {"errors": 0, "warnings": 0, "info": 0, "nodes": 15}, "diagnostics": []}


def test_example_graph_has_the_documents_and_requirements_of_the_poc():
    graph = build_graph(load_config(EXAMPLE))
    assert sorted(n.id for n in graph.nodes) == [
        "ADR-001", "ADR-002", "ADR-003", "CAP-habits", "CAP-reminders", "EXP-1", "OPP-1", "OPP-2", "OUT-1",
        "REQ-HAB-001", "REQ-HAB-002", "REQ-REM-001", "REQ-REM-002", "SOL-1", "SOL-2"]
    assert all(n.covered for n in graph.nodes if n.is_item)
    assert [(r.id, r.start, r.end) for r in graph.code_regions if r.path == "app/lib/habits.dart"] == [
        ("REQ-HAB-001", 1, 4), ("REQ-HAB-002", 6, 9)]


def test_example_views_are_what_gen_writes():
    cfg = load_config(EXAMPLE)
    assert stale_views(cfg, build_graph(cfg)) == []
    assert sorted(view.output for view in cfg.views) == sorted(
        path.relative_to(EXAMPLE).as_posix() for path in (EXAMPLE / "docs/generated").glob("*.md"))


def test_the_waiver_and_the_override_of_the_example_are_in_use():
    cfg = load_config(EXAMPLE)
    assert cfg.overrides == {"ost/committed-solution-has-evidence": "warn"}
    cfg.waivers = []
    diagnostics = run_check(cfg, build_graph(cfg), today=TODAY)
    assert [(d.rule, d.severity, d.node) for d in diagnostics] == [
        ("ost-capability/capability-traces-to-discovery", "warn", "CAP-habits")]


@pytest.fixture
def broken(tmp_path):
    """The example, broken as in the POC README."""
    root = tmp_path / "habit-tracker"
    shutil.copytree(EXAMPLE, root)

    def edit(path: str, old: str, new: str) -> None:
        text = (root / path).read_text(encoding="utf-8")
        assert old in text
        (root / path).write_text(text.replace(old, new), encoding="utf-8")

    with (root / "app/lib/habits.dart").open("a", encoding="utf-8") as code:
        code.write("// bondstone: REQ-HAB-009\n")
    edit("docs/discovery/solutions/SOL-2-streak-freeze.md", "addresses: [OPP-2]", "addresses: [OPP-9]")
    # editing an accepted decision is `bondstone/immutable` once checks compare with a base commit
    edit("docs/adr/ADR-002-store-habits-locally-with-sqlite.md", "on-device SQLite database", "SQLite database")
    return root


def test_broken_example_text_output(broken):
    diagnostics, nodes = check(broken)
    assert fails(diagnostics)
    text = to_text(diagnostics, nodes)
    assert_golden("example-broken.txt", text)
    assert "app/lib/habits.dart:10: error bondstone/code-ref-unknown: code references unknown id 'REQ-HAB-009'\n" in text
    # line 6, not the POC's 5: every document now has a `type` line
    assert ("docs/discovery/solutions/SOL-2-streak-freeze.md:6: error bondstone/link-broken: "
            "addresses -> 'OPP-9': no such document\n") in text


def test_broken_example_json_output(broken):
    diagnostics, nodes = check(broken)
    assert_golden("example-broken.json", to_json(diagnostics, nodes))


def test_gen_is_idempotent(broken):
    cfg = load_config(broken)
    assert generate(cfg, build_graph(cfg)) == [
        "docs/generated/opportunity-solution-tree.md", "docs/generated/outcome-to-capability.md"]
    snapshot = {p.name: p.read_bytes() for p in (broken / "docs/generated").iterdir()}
    cfg = load_config(broken)
    assert generate(cfg, build_graph(cfg)) == []
    assert {p.name: p.read_bytes() for p in (broken / "docs/generated").iterdir()} == snapshot
    diagnostics, _ = check(broken)
    assert [d.rule for d in diagnostics] == ["bondstone/code-ref-unknown", "bondstone/link-broken"]


def test_gen_on_the_untouched_example_writes_nothing(tmp_path):
    root = tmp_path / "habit-tracker"
    shutil.copytree(EXAMPLE, root)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    cfg = load_config(root)
    assert generate(cfg, build_graph(cfg)) == []
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
