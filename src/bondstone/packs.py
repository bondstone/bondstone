"""What is available to a profile, and a new profile: `bondstone packs` and `bondstone init`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import PROFILE_PATH, Component, Refused
from .resolve import find_sources, index_sources, parse_version, shown_path

KINDS = ("pack", "bridge", "preset")  # the order of a listing


@dataclass
class Available:
    kind: str  # "pack" | "bridge" | "preset"
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
    """Every pack, bridge and preset in the profile's sources and in installed packages.

    Packs come first, then bridges, then presets, each sorted by id; copies of one component
    keep the order in which the resolver searches them."""
    sources, _ = find_sources(root, profile)
    used = {(c.kind, c.dir.resolve()) for c in components or []}
    found = []
    index = sorted(index_sources(sources).items(), key=lambda item: (KINDS.index(item[0][0]), item[0][1]))
    for (kind, cid), candidates in index:
        for candidate in candidates:
            found.append(Available(kind, cid, candidate.version or "?", candidate.source.label,
                                   shown_path(root, candidate.dir), candidate.description,
                                   (kind, candidate.dir.resolve()) in used))
    return found


def to_text(found: list[Available]) -> str:
    if not found:
        return "no packs, bridges or presets found\n"
    rows = [("in use" if item.in_use else "", item.kind, f"{item.id}@{item.version}", item.source, item.description)
            for item in found]
    widths = [max(len("in use"), *(len(row[column]) for row in rows)) if column == 0
              else max(len(row[column]) for row in rows) for column in range(4)]
    return "".join("  ".join([*(cell.ljust(width) for cell, width in zip(row, widths)), row[4]]).rstrip() + "\n"
                   for row in rows)


PROFILE = """\
# What this repository uses and how strict the rules are.
# `bondstone packs` lists the packs, bridges and presets that are available here: the ones in
# .bondstone/packs and the ones of installed packages such as bondstone-library.
bondstone: 1
{extends}packs: []
bridges: []
"""
FROM_PRESET = """\
extends: [{ref}]
code:
  include: []   # globs of this repository's source files, such as "src/**/*.py"
"""


# bondstone: REQ-PRF-012
def init_profile(root: Path, preset: str | None = None) -> str:
    """Create a profile, empty or extending a preset; an existing one is never overwritten."""
    path = root / PROFILE_PATH
    if path.exists():
        raise Refused(f"{PROFILE_PATH} already exists in {root}")
    extends = ""
    if preset is not None:
        sources, _ = find_sources(root, None)
        index = index_sources(sources)
        name = preset.partition("@")[0]
        candidates = [c for c in index.get(("preset", name), []) if c.error is None]
        if not candidates:
            known = sorted(cid for (kind, cid) in index if kind == "preset")
            listing = f"available: {', '.join(known)}" if known else "no presets are available here"
            raise Refused(f"preset '{name}' not found ({listing})")
        version = parse_version(candidates[0].version)
        extends = FROM_PRESET.format(ref=preset if "@" in preset or version is None else f"{name}@{version[0]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PROFILE.format(extends=extends), encoding="utf-8")
    return PROFILE_PATH
