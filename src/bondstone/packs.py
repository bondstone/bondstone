"""What is available to a profile, and a new profile: `bondstone packs` and `bondstone init`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import PROFILE_PATH, Component, Refused
from .resolve import find_sources, index_sources, shown_path


@dataclass
class Available:
    kind: str  # "pack" | "bridge"
    id: str
    version: str
    source: str  # the folder as the profile names it, or the installed package
    path: str
    description: str
    in_use: bool  # the profile resolved to this copy

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "id": self.id, "version": self.version, "source": self.source,
                "path": self.path, "description": self.description, "in_use": self.in_use}


# bondstone: REQ-PKT-003
def available(root: Path, profile: dict[str, Any] | None = None,
              components: list[Component] | None = None) -> list[Available]:
    """Every pack and bridge in the profile's sources and in installed packages.

    Packs come before bridges, each sorted by id; copies of one component keep the order in
    which the resolver searches them."""
    sources, _ = find_sources(root, profile)
    used = {(c.kind, c.dir.resolve()) for c in components or []}
    found = []
    for (kind, cid), candidates in sorted(index_sources(sources).items(), key=lambda item: (item[0][0] != "pack", item[0][1])):
        for candidate in candidates:
            found.append(Available(kind, cid, candidate.version or "?", candidate.source.label,
                                   shown_path(root, candidate.dir), candidate.description,
                                   (kind, candidate.dir.resolve()) in used))
    return found


def to_text(found: list[Available]) -> str:
    if not found:
        return "no packs or bridges found\n"
    rows = [("in use" if item.in_use else "", item.kind, f"{item.id}@{item.version}", item.source, item.description)
            for item in found]
    widths = [max(len("in use"), *(len(row[column]) for row in rows)) if column == 0
              else max(len(row[column]) for row in rows) for column in range(4)]
    return "".join("  ".join([*(cell.ljust(width) for cell, width in zip(row, widths)), row[4]]).rstrip() + "\n"
                   for row in rows)


EMPTY_PROFILE = """\
# What this repository uses and how strict the rules are.
# `bondstone packs` lists the packs and bridges that are available here: the ones in
# .bondstone/packs and the ones of installed packages such as bondstone-library.
bondstone: 1
packs: []
bridges: []
"""


# bondstone: REQ-PRF-012
def init_profile(root: Path) -> str:
    """Create an empty profile; an existing one is never overwritten."""
    path = root / PROFILE_PATH
    if path.exists():
        raise Refused(f"{PROFILE_PATH} already exists in {root}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(EMPTY_PROFILE, encoding="utf-8")
    return PROFILE_PATH
