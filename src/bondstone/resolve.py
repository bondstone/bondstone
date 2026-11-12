"""Find the profile and the packs and bridges it names.

The profile's `sources` folders are searched first, then the folders that installed packages
such as bondstone-library register. Presets named under `extends` add their packs and bridges
to the profile's. Git sources and the lock file come later."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from . import __version__
from .manifest import MANIFEST_NAMES, ManifestError, load_manifest, load_yaml
from .model import CONFIG_RULE, ERROR, PROFILE_PATH, Component, Diagnostic, EnvironmentProblem

DEFAULT_SOURCES = [".bondstone/packs"]
ENTRY_POINT_GROUP = "bondstone.sources"  # installed packages register a folder of packs here

# --------------------------------------------------------------------------- versions

_VERSION = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")
_SHORT = re.compile(r"\^?(\d+(?:\.\d+){0,2})")
_TERM = re.compile(r"(>=|<=|==|>|<|=)\s*(\d+(?:\.\d+){0,2})")
_COMPARE = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "=": lambda a, b: a == b,
}


def parse_version(text: str) -> tuple[int, int, int] | None:
    """Major, minor and patch of a version; a pre-release suffix is ignored."""
    match = _VERSION.match(str(text).strip())
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def _terms(spec: str) -> list[str]:
    spec = re.sub(r"(>=|<=|==|>|<|=)\s+", r"\1", spec.strip())  # ">= 1.0" is one term
    return [term for term in re.split(r"[,\s]+", spec) if term]


def range_is_valid(spec: str) -> bool:
    if _SHORT.fullmatch(spec.strip()):
        return True
    terms = _terms(spec)
    return bool(terms) and all(_TERM.fullmatch(term) for term in terms)


# bondstone: REQ-PRF-004
def version_matches(version: str, spec: str | None) -> bool:
    """Whether a version satisfies a range.

    `1`, `1.2` and `^1.2` mean "at least that version, same major version"; comparators such
    as `>=1.0` or `>=1,<2` are combined with AND. No range matches everything."""
    if spec is None or not str(spec).strip():
        return True
    actual = parse_version(version)
    spec = str(spec).strip()
    if actual is None or not range_is_valid(spec):
        return False
    short = _SHORT.fullmatch(spec)
    if short:
        lower = parse_version(short.group(1))
        return actual >= lower and actual[0] == lower[0]
    for term in _terms(spec):
        operator, number = _TERM.fullmatch(term).groups()
        if not _COMPARE[operator](actual, parse_version(number)):
            return False
    return True


def parse_ref(ref: str) -> tuple[str, str | None]:
    """Split `adr@1` into the component id and its version range."""
    name, sep, spec = str(ref).partition("@")
    return name.strip(), (spec.strip() if sep else None)


# --------------------------------------------------------------------------- root


# bondstone: REQ-PRF-003
def find_root(start: Path) -> Path:
    """The nearest folder at or above `start` that holds `.bondstone/profile.yaml`."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / PROFILE_PATH).is_file():
            return candidate
    raise EnvironmentProblem(f"no {PROFILE_PATH} found in {start} or its parents")


def shown_path(root: Path, path: Path) -> str:
    """A path as diagnostics show it: relative to the repository root, with forward slashes.

    A file outside the repository, such as a pack of an installed package, keeps its full path."""
    root, path = root.resolve(), path.resolve()
    if path.is_relative_to(root):
        return path.relative_to(root).as_posix()
    return path.as_posix()


# --------------------------------------------------------------------------- sources


@dataclass
class Source:
    """A folder that holds packs and bridges, one per subfolder."""

    dir: Path
    label: str  # how listings name it: the folder as the profile writes it, or the package
    installed: bool = False


@dataclass
class Candidate:
    kind: str
    id: str
    version: str
    dir: Path
    manifest: Path
    error: str | None = None  # the manifest could not be read as YAML
    source: Source | None = None
    description: str = ""


# bondstone: REQ-PRF-011
def installed_sources() -> tuple[list[Source], list[str]]:
    """The folders installed packages register, by entry point name, and what failed to load.

    An entry point of the group `bondstone.sources` names a function that returns the folder."""
    sources: list[Source] = []
    errors: list[str] = []
    for entry in sorted(entry_points(group=ENTRY_POINT_GROUP), key=lambda e: e.name):
        package = entry.dist.name if entry.dist is not None else entry.name
        try:
            target = entry.load()
            folder = Path(target() if callable(target) else target)
        except Exception as exc:  # a broken plugin must not take the checker down with a traceback
            errors.append(f"installed package '{package}': its pack source '{entry.name}' "
                          f"could not be loaded ({type(exc).__name__}: {exc})")
            continue
        if not folder.is_dir():
            errors.append(f"installed package '{package}': its pack source '{folder}' is not a folder")
            continue
        sources.append(Source(folder, package, installed=True))
    return sources, errors


# bondstone: REQ-PRF-004, REQ-PRF-011
def find_sources(root: Path, profile: dict[str, Any] | None,
                 extra_sources: list[Path] | None = None) -> tuple[list[Source], list[str]]:
    """Every folder to search, in priority order: the profile's `sources`, then installed packages.

    `extra_sources` come first; fixtures use them to find the component under test."""
    profile = profile or {}
    sources = [Source(path, shown_path(root, path)) for path in extra_sources or []]
    errors: list[str] = []
    for name in profile.get("sources", DEFAULT_SOURCES):
        directory = root / name
        if "sources" in profile and not directory.is_dir():
            errors.append(f"sources: folder '{name}' does not exist")
        sources.append(Source(directory, name))
    installed, problems = installed_sources()
    return sources + installed, errors + problems


def index_sources(sources: list[Source]) -> dict[tuple[str, str], list[Candidate]]:
    """Packs, bridges and presets found directly under the source folders, in priority order."""
    found: dict[tuple[str, str], list[Candidate]] = {}
    for source in sources:
        if not source.dir.is_dir():
            continue
        for kind, filename in MANIFEST_NAMES.items():
            for manifest in sorted(source.dir.glob(f"*/{filename}")):
                folder = manifest.parent
                try:
                    data = load_yaml(manifest)
                    error = None
                except ManifestError as exc:
                    data, error = None, str(exc)
                data = data if isinstance(data, dict) else {}
                cid = data.get("id") if isinstance(data.get("id"), str) else folder.name
                description = data.get("description") if isinstance(data.get("description"), str) else ""
                candidate = Candidate(kind, cid, str(data.get("version", "")), folder, manifest, error,
                                      source, " ".join(description.split()))
                found.setdefault((kind, cid), []).append(candidate)
    return found


# --------------------------------------------------------------------------- resolution


@dataclass
class Resolution:
    root: Path
    profile: dict[str, Any] | None = None
    components: list[Component] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)


def _problem(message: str, path: str = PROFILE_PATH) -> Diagnostic:
    return Diagnostic(CONFIG_RULE, ERROR, message, path=path)


# bondstone: REQ-PRF-004, REQ-PRF-013
def resolve(root: Path, extra_sources: list[Path] | None = None) -> Resolution:
    """Load the profile and every preset, pack and bridge it needs.

    The components come back as packs, bridges and then presets, each in the order in which
    they are first named: presets in `extends` order, then the profile. `extra_sources` are
    searched before the profile's own; fixtures use them to find the component under test."""
    result = Resolution(root)
    profile_file = root / PROFILE_PATH
    if not profile_file.is_file():
        raise EnvironmentProblem(f"no {PROFILE_PATH} in {root}")
    profile, problems = load_manifest("profile", profile_file, PROFILE_PATH)
    result.problems += problems
    if profile is None:
        return result
    result.profile = profile

    sources, errors = find_sources(root, profile, extra_sources)
    result.problems += [_problem(message) for message in errors]
    index = index_sources(sources)

    presets = _presets(result, index, profile)
    requested: dict[tuple[str, str], list[tuple[str | None, str]]] = {}  # ranges and where each is written
    for where, data in [*((preset.manifest, preset.data) for preset in presets), (PROFILE_PATH, profile)]:
        for kind, key in (("pack", "packs"), ("bridge", "bridges")):
            here: set[str] = set()
            for ref in data.get(key, []):
                cid, spec = parse_ref(ref)
                if cid in here:
                    result.problems.append(_problem(f"{key}: {kind} '{cid}' is listed more than once", where))
                    continue
                here.add(cid)
                requested.setdefault((kind, cid), []).append((spec, where))
    for kind in ("pack", "bridge"):
        for (wanted, cid), specs in requested.items():
            if wanted == kind:
                component = _choose(result, index, kind, cid, specs)
                if component is not None:
                    result.components.append(component)
    result.components += presets

    _check_requirements(result, {cid for kind, cid in requested if kind == "pack"})
    return result


# bondstone: REQ-PRF-013
def _presets(result: Resolution, index: dict[tuple[str, str], list[Candidate]],
             profile: dict[str, Any]) -> list[Component]:
    """The presets a profile extends, each after the presets it extends itself.

    A preset reached more than once is applied once, where it is first needed."""
    ordered: list[Component] = []
    visited: dict[str, Component | None] = {}

    def visit(ref: str, chain: list[str], where: str) -> None:
        cid, spec = parse_ref(ref)
        if cid in chain:
            loop = " -> ".join([*chain[chain.index(cid):], cid])
            result.problems.append(_problem(f"extends: preset '{cid}' extends itself ({loop})", where))
            return
        if cid in visited:
            known = visited[cid]
            if known is not None and spec is not None and range_is_valid(spec) \
                    and not version_matches(known.version, spec):
                result.problems.append(_problem(
                    f"extends: preset '{cid}' is needed as '{spec}', but {known.version} is already in use", where))
            return
        visited[cid] = None  # also stops a second report when it cannot be loaded
        preset = _choose(result, index, "preset", cid, [(spec, where)])
        visited[cid] = preset
        if preset is None:
            return
        for parent in preset.data.get("extends", []):
            visit(parent, [*chain, cid], preset.manifest)
        ordered.append(preset)

    for ref in profile.get("extends", []):
        visit(ref, [], PROFILE_PATH)
    return ordered


_LISTS = {"pack": "packs", "bridge": "bridges", "preset": "extends"}


# bondstone: REQ-PRF-004
def _choose(result: Resolution, index: dict[tuple[str, str], list[Candidate]], kind: str,
            cid: str, specs: list[tuple[str | None, str]]) -> Component | None:
    """The first copy of a component, in the order of the sources, that fits every range asked for.

    `specs` pairs each range with the file that asks for it; problems are reported there."""
    where = specs[0][1]
    for spec, asked_in in specs:
        if spec is not None and not range_is_valid(spec):
            result.problems.append(_problem(f"{kind} '{cid}': invalid version range '{spec}'", asked_in))
            return None
    candidates = index.get((kind, cid), [])
    if not candidates:
        other = next((k for k in _LISTS if k != kind and index.get((k, cid))), None)
        if other is not None:
            result.problems.append(_problem(
                f"{kind} '{cid}' not found: '{cid}' is a {other}; list it under `{_LISTS[other]}`", where))
        else:
            result.problems.append(_problem(
                f"{kind} '{cid}' not found in the profile's sources or in an installed package", where))
        return None
    broken = next((c for c in candidates if c.error), None)
    if broken is not None:
        result.problems.append(_problem(broken.error, shown_path(result.root, broken.manifest)))
        return None
    chosen = next((c for c in candidates if all(version_matches(c.version, spec) for spec, _ in specs)), None)
    if chosen is None:
        versions = ", ".join(dict.fromkeys(c.version or "?" for c in candidates))
        ranges = list(dict.fromkeys(spec for spec, _ in specs if spec is not None))
        if len(ranges) == 1:
            wanted = f"'{ranges[0]}'"
        else:
            wanted = "all of " + ", ".join(f"'{spec}' ({asked_in})" for spec, asked_in in specs if spec is not None)
        result.problems.append(_problem(
            f"{kind} '{cid}': no version matches {wanted} (available: {versions})", where))
        return None
    shown = shown_path(result.root, chosen.manifest)
    data, problems = load_manifest(kind, chosen.manifest, shown)
    result.problems += problems
    if data is None:
        return None
    engine = data.get("bondstone")
    if engine is not None:
        if not range_is_valid(engine):
            result.problems.append(_problem(f"bondstone: invalid version range '{engine}'", shown))
            return None
        if not version_matches(__version__, engine):
            result.problems.append(_problem(
                f"{kind} '{cid}' needs bondstone {engine}; this is bondstone {__version__}", shown))
            return None
    return Component(kind, cid, data["version"], chosen.dir, shown, data)


# bondstone: REQ-PRF-005
def _check_requirements(result: Resolution, listed: set[str]) -> None:
    """Every bridge's required packs are named by the profile or a preset, in a version the bridge accepts."""
    packs = {c.id: c for c in result.components if c.kind == "pack"}
    for bridge in (c for c in result.components if c.kind == "bridge"):
        for pack_id, spec in bridge.data["requires"].items():
            if not range_is_valid(spec):
                result.problems.append(_problem(
                    f"requires.{pack_id}: invalid version range '{spec}'", bridge.manifest))
            elif pack_id not in listed:
                result.problems.append(_problem(
                    f"bridge '{bridge.id}' requires pack '{pack_id}', which is not in the profile"))
            elif pack_id in packs and not version_matches(packs[pack_id].version, spec):
                result.problems.append(_problem(
                    f"bridge '{bridge.id}' requires {pack_id} {spec}; "
                    f"the profile has {packs[pack_id].version}"))
