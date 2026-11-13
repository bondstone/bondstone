"""What the engine package ships: its schemas, and no packs (D12)."""

from pathlib import Path

import bondstone
from bondstone.manifest import KINDS, SCHEMA_DIR

PACKAGE = Path(bondstone.__file__).parent


def test_schemas_ship_inside_the_package():
    assert SCHEMA_DIR.parent == PACKAGE
    assert sorted(p.name for p in SCHEMA_DIR.glob("*.json")) == sorted(
        [f"{kind}.schema.json" for kind in KINDS]
        + ["common.schema.json", "graph.schema.json", "known.schema.json", "lock.schema.json"])


def test_the_engine_ships_no_packs_or_bridges():
    assert [p for p in PACKAGE.rglob("*.yaml")] == []
    assert not (PACKAGE / "library").exists()
