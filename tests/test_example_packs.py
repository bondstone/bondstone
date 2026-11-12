"""Fixtures of the example's local packs and bridges: a valid and an invalid case each."""

import datetime as dt
from pathlib import Path

import pytest
from conftest import EXAMPLE_PACKS

from bondstone.packtest import run_fixtures

TODAY = dt.date(2026, 11, 10)
COMPONENTS = sorted(p.parent for p in [*EXAMPLE_PACKS.glob("*/pack.yaml"), *EXAMPLE_PACKS.glob("*/bridge.yaml")])


def test_the_example_ships_the_three_packs_and_their_bridges():
    assert [c.name for c in COMPONENTS] == ["adr", "adr-capability", "capability", "ost", "ost-capability"]


@pytest.mark.parametrize("component", COMPONENTS, ids=lambda c: c.name)
def test_fixtures_pass_with_a_valid_and_an_invalid_case(component: Path):
    results = run_fixtures(component, today=TODAY)
    assert [r.case for r in results] == ["invalid", "valid"]
    assert [r.problems for r in results] == [[], []]
    expected = {case: (component / "fixtures" / case / "expected.yaml").read_text(encoding="utf-8")
                for case in ("valid", "invalid")}
    assert expected["valid"].split() == ["errors:", "[]", "warnings:", "[]"]
    assert "errors:\n- " in expected["invalid"]
