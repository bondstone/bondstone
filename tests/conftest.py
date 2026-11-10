from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "habit-tracker"
EXAMPLE_PACKS = EXAMPLE / ".bondstone" / "packs"


class Project:
    """A throwaway repository to run bondstone against."""

    def __init__(self, root: Path):
        self.root = root

    def profile(self, **data) -> "Project":
        data = {"bondstone": 1, **data}
        return self.write(".bondstone/profile.yaml", yaml.safe_dump(data, sort_keys=False))

    def pack(self, pack_id: str, text: str, folder: str = ".bondstone/packs") -> "Project":
        return self.write(f"{folder}/{pack_id}/pack.yaml", text)

    def bridge(self, bridge_id: str, text: str, folder: str = ".bondstone/packs") -> "Project":
        return self.write(f"{folder}/{bridge_id}/bridge.yaml", text)

    def write(self, path: str, text: str) -> "Project":
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")
        return self

    def read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Project:
    return Project(tmp_path)
