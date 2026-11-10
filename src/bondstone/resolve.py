"""Find the profile and the packs and bridges it names.

Only local `sources` folders are searched for now; git sources, installed library packages,
presets and the lock file come in later phases."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import __version__
from .manifest import MANIFEST_NAMES, ManifestError, load_manifest, load_yaml
from .model import CONFIG_RULE, ERROR, PROFILE_PATH, Component, Diagnostic, EnvironmentProblem

DEFAULT_SOURCES = [".bondstone/packs"]

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
    """A path as diagnostics show it: relative to the repository root, with forward slashes."""
    return Path(os.path.relpath(path, root)).as_posix()


# --------------------------------------------------------------------------- sources


@dataclass
class Candidate:
    kind: str
    id: str
    version: str
    dir: Path
    manifest: Path
    error: str | None = None  # the manifest could not be read as YAML


def index_sources(dirs: list[Path]) -> dict[tuple[str, str], list[Candidate]]:
    """Packs and bridges found directly under the source folders, in priority order."""
    found: dict[tuple[str, str], list[Candidate]] = {}
    for base in dirs:
        if not base.is_dir():
            continue
        for kind, filename in MANIFEST_NAMES.items():
            for manifest in sorted(base.glob(f"*/{filename}")):
                folder = manifest.parent
                try:
                    data = load_yaml(manifest)
                    error = None
                except ManifestError as exc:
                    data, error = None, str(exc)
                data = data if isinstance(data, dict) else {}
                cid = data.get("id") if isinstance(data.get("id"), str) else folder.name
                candidate = Candidate(kind, cid, str(data.get("version", "")), folder, manifest, error)
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


# bondstone: REQ-PRF-004
def resolve(root: Path, extra_sources: list[Path] | None = None) -> Resolution:
    """Load the profile and every pack and bridge it names from the local sources.

    `extra_sources` are searched before the profile's own; fixtures use them to find the
    component under test."""
    result = Resolution(root)
    profile_file = root / PROFILE_PATH
    if not profile_file.is_file():
        raise EnvironmentProblem(f"no {PROFILE_PATH} in {root}")
    profile, problems = load_manifest("profile", profile_file, PROFILE_PATH)
    result.problems += problems
    if profile is None:
        return result
    result.profile = profile

    if profile.get("extends"):
        result.problems.append(_problem(
            "extends: presets are not supported yet; list the packs and bridges in the profile"))

    source_dirs = list(extra_sources or [])
    for source in profile.get("sources", DEFAULT_SOURCES):
        directory = root / source
        if "sources" in profile and not directory.is_dir():
            result.problems.append(_problem(f"sources: folder '{source}' does not exist"))
        source_dirs.append(directory)
    index = index_sources(source_dirs)

    seen: set[tuple[str, str]] = set()
    for kind, key in (("pack", "packs"), ("bridge", "bridges")):
        for ref in profile.get(key, []):
            cid, spec = parse_ref(ref)
            if (kind, cid) in seen:
                result.problems.append(_problem(f"{key}: {kind} '{cid}' is listed more than once"))
                continue
            seen.add((kind, cid))
            component = _choose(result, index, kind, cid, spec)
            if component is not None:
                result.components.append(component)

    _check_requirements(result)
    return result


# bondstone: REQ-PRF-004
def _choose(result: Resolution, index: dict[tuple[str, str], list[Candidate]], kind: str,
            cid: str, spec: str | None) -> Component | None:
    if spec is not None and not range_is_valid(spec):
        result.problems.append(_problem(f"{kind} '{cid}': invalid version range '{spec}'"))
        return None
    candidates = index.get((kind, cid), [])
    if not candidates:
        other = "bridge" if kind == "pack" else "pack"
        if index.get((other, cid)):
            result.problems.append(_problem(
                f"{kind} '{cid}' not found: '{cid}' is a {other}; list it under `{other}s`"))
        else:
            result.problems.append(_problem(f"{kind} '{cid}' not found in the profile's sources"))
        return None
    broken = next((c for c in candidates if c.error), None)
    if broken is not None:
        result.problems.append(_problem(broken.error, shown_path(result.root, broken.manifest)))
        return None
    chosen = next((c for c in candidates if version_matches(c.version, spec)), None)
    if chosen is None:
        versions = ", ".join(c.version or "?" for c in candidates)
        result.problems.append(_problem(
            f"{kind} '{cid}': no version matches '{spec}' (available: {versions})"))
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
def _check_requirements(result: Resolution) -> None:
    """Every bridge's required packs are in the profile, in a version the bridge accepts."""
    packs = {c.id: c for c in result.components if c.kind == "pack"}
    listed = {parse_ref(ref)[0] for ref in (result.profile or {}).get("packs", [])}
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
