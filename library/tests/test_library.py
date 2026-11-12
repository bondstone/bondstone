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
    assert [c.name for c in COMPONENTS] == ["adr", "adr-capability", "capability"]
    assert [p.name for p in PRESETS] == ["starter"]


def test_the_library_registers_its_folder_with_bondstone():
    sources, errors = installed_sources()
    assert errors == []
    assert (SOURCE, "bondstone-library") in [(s.dir, s.label) for s in sources]


def test_every_folder_is_named_after_its_component():
    for component in [*COMPONENTS, *PRESETS]:
        manifest = next(p for name in ("pack.yaml", "bridge.yaml", "preset.yaml") if (p := component / name).is_file())
        assert yaml.safe_load(manifest.read_text(encoding="utf-8"))["id"] == component.name


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
