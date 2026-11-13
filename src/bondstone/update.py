"""Fetch the git sources a profile needs and pin them: `bondstone update`.

This is the only command that touches the network. Plain, it resolves every ref again and
rewrites the lock; with names, only the sources that hold those components move. With
`--locked` it fetches exactly what the lock pins and changes nothing, which is what CI runs
before `check`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import Refused
from .resolve import resolve
from .sources import LOCK_PATH, GitSource, Locked, describe_components, fetch, read_lock, source_dir, verify, write_lock

_ROUNDS = 20  # presets that name sources that hold presets: far more levels than anyone nests


@dataclass
class SourceUpdate:
    source: str
    commit: str
    previous: str | None  # the commit the lock had; None for a new source
    components: list[dict[str, str]]

    @property
    def changed(self) -> bool:
        return self.previous != self.commit

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "commit": self.commit, "previous": self.previous, "changed": self.changed,
                "components": [{"kind": c["kind"], "id": c["id"], "version": c["version"]} for c in self.components]}


@dataclass
class Updated:
    sources: list[SourceUpdate] = field(default_factory=list)
    lock_changed: bool = False
    removed: list[str] = field(default_factory=list)  # sources the lock had that nothing names any more

    def to_dict(self) -> dict[str, Any]:
        return {"sources": [source.to_dict() for source in self.sources], "lock": LOCK_PATH,
                "changed": self.lock_changed, "removed": self.removed}


def _holds(locked: Locked | None, names: set[str]) -> bool:
    return locked is not None and any(component["id"] in names for component in locked.components)


# bondstone: REQ-PRF-020
def update(root: Path, names: list[str] | None = None, locked: bool = False) -> Updated:
    """Bring every git source the profile reaches into the cache, and pin it unless `locked`.

    Sources are found in rounds, because a preset from one source may name another."""
    before, problems = read_lock(root)
    if problems:
        raise Refused(f"{LOCK_PATH}: {problems[0]}" + ("" if locked else "; delete the file to write a new one"))
    wanted = set(names or [])
    known = {component["id"] for entry in before.values() for component in entry.components}
    if wanted - known:
        raise Refused(f"no git source in {LOCK_PATH} holds {', '.join(sorted(wanted - known))}")

    pinned = dict(before)
    done: dict[str, SourceUpdate] = {}

    def bring(source: GitSource) -> None:
        old = before.get(source.spec)
        if locked:
            if old is None:
                raise Refused(f"{LOCK_PATH} does not pin '{source.spec}'; run `bondstone update` and commit the lock")
            if verify(source, old) is not None:
                fetch(source, old.commit)
            problem = verify(source, old)
            if problem is not None:
                raise Refused(f"{source.spec}: {problem}; the lock was edited or is damaged: run `bondstone update`")
            done[source.spec] = SourceUpdate(source.spec, old.commit, old.commit, old.components)
            return
        keep = old is not None and bool(wanted) and not _holds(old, wanted)
        commit = fetch(source, old.commit if keep else None)
        components = describe_components(source_dir(source, commit))
        if not components:
            raise Refused(f"{source.spec}: commit {commit[:12]} has no pack, bridge or preset in "
                          f"'{source.path or '.'}'")
        pinned[source.spec] = Locked(source.spec, commit, components)
        done[source.spec] = SourceUpdate(source.spec, commit, old.commit if old else None, components)

    reached: list[GitSource] = []
    for _ in range(_ROUNDS):
        if not locked:
            write_lock(root, [pinned[spec] for spec in pinned])  # the next round reads what this one pinned
        resolution = resolve(root, fetching=True)
        reached = resolution.git_sources
        todo = [source for source in reached if source.spec not in done]
        if not todo:
            break
        for source in todo:
            bring(source)
    else:
        raise Refused("git sources keep naming new git sources; check the presets for a loop")

    result = Updated(sources=[done[source.spec] for source in reached])
    if not locked:
        named = {source.spec for source in reached}
        result.removed = sorted(spec for spec in before if spec not in named)
        final = [pinned[spec] for spec in pinned if spec in named]
        write_lock(root, final)
        after, _ = read_lock(root)
        result.lock_changed = {s: e.to_dict() for s, e in after.items()} != {s: e.to_dict() for s, e in before.items()}
    return result


def to_text(result: Updated, locked: bool) -> str:
    if not result.sources and not result.removed:
        return "the profile names no git sources\n"
    lines = []
    for source in result.sources:
        count = f"{len(source.components)} component(s)"
        if locked:
            lines.append(f"{source.source}: {source.commit[:12]} is in the cache ({count})")
        elif source.previous is None:
            lines.append(f"{source.source}: pinned at {source.commit[:12]} ({count})")
        elif source.changed:
            lines.append(f"{source.source}: {source.previous[:12]} -> {source.commit[:12]} ({count})")
        else:
            lines.append(f"{source.source}: still {source.commit[:12]} ({count})")
    lines += [f"{spec}: no longer named; removed from the lock" for spec in result.removed]
    if not locked:
        lines.append(f"wrote {LOCK_PATH}" if result.lock_changed else f"{LOCK_PATH} is up to date")
    return "\n".join(lines) + "\n"
