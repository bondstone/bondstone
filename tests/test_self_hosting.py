"""The exit criterion of phase 2, kept true since: bondstone documents itself.

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
    decisions = {node.id: node.status for node in graph.nodes if node.type == "adr:Decision"}
    design = [f"ADR-{n:03d}" for n in range(1, 16)]  # D1 to D14, and the mandatory `type` key
    assert sorted(decisions)[:15] == design
    assert {decisions[doc_id] for doc_id in design} == {"accepted"}


def test_every_requirement_is_tagged_in_the_source():
    _, graph = load()
    requirements = [node for node in graph.nodes if node.type == "capability:Requirement"]
    assert len(requirements) > 50
    assert [node.id for node in requirements if not node.covered] == []


def test_every_engine_module_implements_a_requirement():
    cfg, graph = load()
    tagged = {tag.path for tag in graph.code_tags}
    untagged = [path for path in code_files(cfg) if path.startswith("src/bondstone/") and path not in tagged
                and not path.endswith("__main__.py") and path != "src/bondstone/__init__.py"]
    assert untagged == []


def test_source_changes_must_update_the_traced_capability():
    cfg, _ = load()
    rule = cfg.rule("starter/code-change-updates-living-spec")  # from the preset the profile extends
    assert rule.kind == "diff" and rule.spec["exempt"] == {"trailer": "Spec-Impact"}
    assert rule.spec["on_change"] == {"code": True}
    assert cfg.code_include == ["src/bondstone/**/*.py", "library/src/**/*.yaml", "library/src/**/*.yml",
                                "library/tests/*.py"]
    assert rule.spec["require"] == [{"changed": {"role": "living-spec"}, "traced": True}]
    assert cfg.code_exclude == ["library/src/**/fixtures/**"]


def test_source_changes_need_a_spec_kit_feature():
    """The exit criterion of phase 4: the profile runs on the library, and features gate changes."""
    cfg, graph = load()
    assert [c.id for c in cfg.components if c.kind == "preset"] == ["starter", "starter-speckit"]
    assert all(c.manifest.startswith("library/src/bondstone_library/packs/") for c in cfg.components)
    rule = cfg.rule("starter-speckit/source-change-has-feature")
    assert rule.spec["on_change"] == {"code": True}
    assert rule.spec["require"] == [{"changed": {"type": "speckit:Feature"}, "min": 1}]
    assert cfg.severity(rule.qid, rule.severity) == "error" and rule.severity == "warn"
    features = [node for node in graph.nodes if node.type == "speckit:Feature"]
    assert features and all(node.status in ("specified", "planned", "implemented") for node in features)
    assert all(node.path == f"specs/{node.id}/spec.md" for node in features)


def test_the_spec_kit_preset_installed_here_is_the_one_the_library_ships():
    """`.specify/presets/bondstone` is a copy made by `specify preset add --dev`; it must not drift."""
    import bondstone_library

    shipped, installed = bondstone_library.speckit_preset(), REPO / ".specify" / "presets" / "bondstone"
    files = sorted(path.relative_to(shipped).as_posix() for path in shipped.rglob("*") if path.is_file())
    assert files == ["commands/specify-bondstone.md", "preset.yml", "templates/spec-frontmatter.md"]
    for name in files:
        assert (installed / name).read_text(encoding="utf-8") == (shipped / name).read_text(encoding="utf-8"), name


def test_library_components_are_traced_to_requirements():
    _, graph = load()
    tagged = {tag.path: tag.id for tag in graph.code_tags if tag.path.startswith("library/")}
    packs = "library/src/bondstone_library/packs"
    assert tagged == {
        f"{packs}/speckit/pack.yaml": "REQ-SKT-001", f"{packs}/speckit/spec-kit/preset.yml": "REQ-SKT-002",
        f"{packs}/speckit-capability/bridge.yaml": "REQ-SKT-003", f"{packs}/speckit-adr/bridge.yaml": "REQ-SKT-004",
        f"{packs}/starter-speckit/preset.yaml": "REQ-SKT-005",
        f"{packs}/cli/pack.yaml": "REQ-LIB-001", f"{packs}/cli-capability/bridge.yaml": "REQ-LIB-002",
        f"{packs}/release/pack.yaml": "REQ-LIB-003", f"{packs}/release-speckit/bridge.yaml": "REQ-LIB-004",
        "library/tests/test_library.py": "REQ-LIB-005",
        f"{packs}/adr/pack.yaml": "REQ-LIB-006", f"{packs}/capability/pack.yaml": "REQ-LIB-007",
        f"{packs}/adr-capability/bridge.yaml": "REQ-LIB-008", f"{packs}/starter/preset.yaml": "REQ-LIB-009"}


def test_bondstone_documents_its_commands_and_its_next_release():
    cfg, graph = load()
    assert {c.id for c in cfg.components} >= {"cli", "release", "cli-capability", "release-speckit"}
    releases = [node for node in graph.nodes if node.type == "release:Release"]
    assert [node.id for node in releases] == ["v1.0.0"]
    assert (REPO / "CHANGELOG.md").read_text(encoding="utf-8").startswith(
        "<!-- bondstone:generated view=release/changelog;")
