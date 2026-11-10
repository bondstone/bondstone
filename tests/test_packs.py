"""Fixtures of the example's local packs and bridges: a valid and an invalid case each.

A fixture is a small repository with an `expected.yaml` that lists the rule of every expected
error and warning. `bondstone pack test` will run the same fixtures once it exists."""

import datetime as dt
from collections import Counter
from pathlib import Path

import pytest
import yaml
from conftest import EXAMPLE_PACKS

from bondstone.config import load_config
from bondstone.graph import build_graph
from bondstone.model import ERROR, WARN
from bondstone.rules import run_check

TODAY = dt.date(2026, 11, 10)
COMPONENTS = sorted(p.parent for p in [*EXAMPLE_PACKS.glob("*/pack.yaml"), *EXAMPLE_PACKS.glob("*/bridge.yaml")])
CASES = [(component, case) for component in COMPONENTS for case in ("valid", "invalid")]


def run_fixture(case: Path) -> dict[str, Counter]:
    cfg = load_config(case, extra_sources=[EXAMPLE_PACKS])
    assert cfg.errors == [], [f"{d.path}: {d.message}" for d in cfg.errors]
    diagnostics = run_check(cfg, build_graph(cfg), today=TODAY)
    return {level: Counter(d.rule for d in diagnostics if d.severity == level) for level in (ERROR, WARN)}


def test_the_example_ships_the_three_packs_and_their_bridges():
    assert [c.name for c in COMPONENTS] == ["adr", "adr-capability", "capability", "ost", "ost-capability"]


@pytest.mark.parametrize("component,case", CASES, ids=[f"{c.name}/{case}" for c, case in CASES])
def test_fixture(component: Path, case: str):
    folder = component / "fixtures" / case
    assert folder.is_dir(), f"{component.name} has no {case} fixture"
    expected = yaml.safe_load((folder / "expected.yaml").read_text(encoding="utf-8"))
    found = run_fixture(folder)
    assert sorted(found[ERROR].elements()) == sorted(expected.get("errors") or [])
    assert sorted(found[WARN].elements()) == sorted(expected.get("warnings") or [])


@pytest.mark.parametrize("component", COMPONENTS, ids=lambda c: c.name)
def test_valid_fixture_is_clean_and_invalid_fixture_fails(component: Path):
    valid, invalid = run_fixture(component / "fixtures/valid"), run_fixture(component / "fixtures/invalid")
    assert not valid[ERROR] and not valid[WARN]
    assert invalid[ERROR]
