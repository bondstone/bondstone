"""What bondstone-library ships: every pack and bridge with a valid and an invalid fixture."""

import datetime as dt
from pathlib import Path

import pytest
import yaml

import bondstone_library
from bondstone.packtest import run_fixtures
from bondstone.resolve import installed_sources

TODAY = dt.date(2026, 11, 10)
SOURCE = bondstone_library.source()
COMPONENTS = sorted(p.parent for p in [*SOURCE.glob("*/pack.yaml"), *SOURCE.glob("*/bridge.yaml")])
PRESETS = sorted(p.parent for p in SOURCE.glob("*/preset.yaml"))


def test_the_library_ships_these_packs_bridges_and_presets():
    assert [c.name for c in COMPONENTS] == ["adr", "adr-capability", "capability", "cli", "cli-capability", "release",
                                            "release-speckit", "speckit", "speckit-adr", "speckit-capability"]
    assert [p.name for p in PRESETS] == ["starter", "starter-speckit"]


def test_the_library_registers_its_folder_with_bondstone():
    sources, errors = installed_sources()
    assert errors == []
    assert (SOURCE, "bondstone-library") in [(s.dir, s.label) for s in sources]


def test_every_folder_is_named_after_its_component():
    for component in [*COMPONENTS, *PRESETS]:
        manifest = next(p for name in ("pack.yaml", "bridge.yaml", "preset.yaml") if (p := component / name).is_file())
        assert yaml.safe_load(manifest.read_text(encoding="utf-8"))["id"] == component.name


# bondstone: REQ-LIB-005
@pytest.mark.parametrize("component", COMPONENTS, ids=lambda c: c.name)
def test_fixtures_pass_with_a_valid_and_an_invalid_case(component: Path):
    results = run_fixtures(component, today=TODAY)
    assert [r.case for r in results] == ["invalid", "valid"]
    assert [r.problems for r in results] == [[], []]
    expected = {case: yaml.safe_load((component / "fixtures" / case / "expected.yaml").read_text(encoding="utf-8"))
                for case in ("valid", "invalid")}
    assert not expected["valid"].get("errors") and not expected["valid"].get("warnings")
    assert expected["invalid"].get("errors")


@pytest.mark.parametrize("preset", PRESETS, ids=lambda p: p.name)
def test_every_preset_has_a_fixture_that_passes(preset: Path):
    """A preset's own rules are mostly diff rules, which a fixture cannot break: one valid case is enough."""
    results = run_fixtures(preset, today=TODAY)
    assert "valid" in [r.case for r in results]
    assert [r.problems for r in results] == [[] for _ in results]


# ----------------------------------------------------------------------- the Spec Kit preset

SPECKIT_VERSION = "1.4.0"  # the Spec Kit release the adapter was tested with (ADR-017)


def test_the_spec_kit_preset_is_pinned_to_the_tested_release():
    folder = bondstone_library.speckit_preset()
    manifest = yaml.safe_load((folder / "preset.yml").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0" and manifest["preset"]["id"] == "bondstone"
    assert manifest["requires"]["speckit_version"] == f">={SPECKIT_VERSION},<1.5"
    assert SPECKIT_VERSION in (SOURCE / "speckit" / "README.md").read_text(encoding="utf-8")
    provided = {(item["type"], item["name"]): item for item in manifest["provides"]["templates"]}
    assert provided[("template", "spec-template")]["strategy"] == "prepend"
    assert provided[("command", "speckit.specify")]["strategy"] == "append"
    for item in provided.values():
        assert (folder / item["file"]).is_file(), item["file"]


def test_the_frontmatter_the_preset_adds_is_what_the_packs_expect():
    """The block must stay a valid bondstone frontmatter, with the links the bridges define."""
    text = (bondstone_library.speckit_preset() / "templates" / "spec-frontmatter.md").read_text(encoding="utf-8")
    assert text.startswith("---\n") and text.rstrip().endswith("---")
    block = yaml.safe_load(text.split("---")[1])
    assert block["type"] == "speckit:Feature" and set(block) == {"id", "type", "title", "modifies", "delivers", "decided_by"}
    links = {}
    for bridge in ("speckit-capability", "speckit-adr"):
        links.update(yaml.safe_load((SOURCE / bridge / "bridge.yaml").read_text(encoding="utf-8"))["links"])
    assert {"modifies", "delivers", "decided_by"} == set(links)
    feature = yaml.safe_load((SOURCE / "speckit" / "pack.yaml").read_text(encoding="utf-8"))["types"]["Feature"]
    assert feature["path"] == "specs/{id}/spec.md" and "title" in feature["fields"]
    assert list(feature["traits"]["derived-status"]) == ["implemented", "planned", "specified"]
