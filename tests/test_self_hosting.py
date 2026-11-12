"""The exit criterion of phase 2: bondstone documents itself.

The repository's own profile, decisions and capability specs pass `bondstone check`, and every
requirement is tagged in the engine's source. CI adds `check --base` on pull requests. The date
is pinned, because the profile has waivers that expire."""

import datetime as dt

from conftest import REPO

from bondstone.config import load_config
from bondstone.graph import build_graph, code_files
from bondstone.rules import run_check

TODAY = dt.date(2026, 11, 10)


def load():
    cfg = load_config(REPO)
    assert cfg.problems == []
    return cfg, build_graph(cfg)


def test_bondstone_passes_its_own_check_without_warnings():
    cfg, graph = load()
    assert [(d.rule, d.path, d.message) for d in run_check(cfg, graph, today=TODAY)] == []


def test_the_decisions_of_the_design_are_recorded():
    _, graph = load()
    decisions = sorted(node.id for node in graph.nodes if node.type == "adr:Decision")
    assert decisions == [f"ADR-{n:03d}" for n in range(1, 16)]
    assert {node.status for node in graph.nodes if node.type == "adr:Decision"} == {"accepted"}


def test_every_requirement_is_tagged_in_the_source():
    _, graph = load()
    requirements = [node for node in graph.nodes if node.type == "capability:Requirement"]
    assert len(requirements) > 50
    assert [node.id for node in requirements if not node.covered] == []


def test_every_engine_module_implements_a_requirement():
    cfg, graph = load()
    tagged = {tag.path for tag in graph.code_tags}
    untagged = [path for path in code_files(cfg) if path not in tagged and not path.endswith("__main__.py")
                and path != "src/bondstone/__init__.py"]
    assert untagged == []


def test_source_changes_must_update_the_traced_capability():
    cfg, _ = load()
    rule = cfg.rule("profile/source-change-updates-traced-spec")
    assert rule.kind == "diff" and rule.spec["exempt"] == {"trailer": "Spec-Impact"}
    assert rule.spec["require"] == [{"changed": {"role": "living-spec"}, "traced": True}]
