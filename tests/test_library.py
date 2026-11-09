from pathlib import Path

import pytest

from bondstone.checks import run_check
from bondstone.loader import load_config
from bondstone.packtest import run_fixtures

from .conftest import EXAMPLE, LIBRARY

COMPONENTS = sorted(p.parent for p in [*LIBRARY.glob("packs/*/pack.yaml"), *LIBRARY.glob("bridges/*/bridge.yaml")])


@pytest.mark.parametrize("component", COMPONENTS, ids=lambda p: p.name)
def test_component_fixtures(component: Path):
    results = run_fixtures(component)
    assert results, f"{component.name} has no fixtures"
    failures = [f"{r.name}: {r.detail}" for r in results if not r.passed]
    assert not failures, "\n".join(failures)


def test_example_project_is_clean():
    diags = run_check(load_config(EXAMPLE))
    assert [d.format() for d in diags] == []
