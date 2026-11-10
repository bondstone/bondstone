"""Load the profile and resolve packs and bridges into a Config."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from .model import (
    ERROR,
    OFF,
    PART_OF,
    SEVERITIES,
    WARN,
    BondstoneError,
    Component,
    Diagnostic,
    LinkDef,
    Rule,
    TypeDef,
    View,
)

LIBRARY = Path(__file__).parent / "library"
PROFILE_PATH = Path(".bondstone") / "profile.yaml"


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise BondstoneError(f"{path}: invalid YAML: {exc}") from exc


def find_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / PROFILE_PATH).is_file():
            return candidate
    raise BondstoneError(
        f"no {PROFILE_PATH} found in {start} or its parents (run `bondstone init`)"
    )


# --------------------------------------------------------------------------- versions


def parse_ref(ref: str) -> tuple[str, str | None]:
    if "@" in ref:
        name, spec = ref.split("@", 1)
        return name.strip(), spec.strip()
    return ref.strip(), None


# bondstone: REQ-PRF-001
def version_matches(version: str, spec: str | None) -> bool:
    if not spec:
        return True
    try:
        v = Version(str(version))
    except InvalidVersion:
        return False
    spec = str(spec).strip()
    m = re.fullmatch(r"\^?(\d+)(?:\.(\d+))?(?:\.(\d+))?", spec)
    if m:
        major = int(m.group(1))
        lower = Version(".".join(g for g in m.groups() if g is not None))
        return v >= lower and v.major == major
    try:
        return v in SpecifierSet(spec)
    except InvalidSpecifier:
        return False


# --------------------------------------------------------------------------- components


def index_components(dirs: list[Path]) -> dict[tuple[str, str], list[Component]]:
    """Find pack.yaml / bridge.yaml files (depth <= 2) in source dirs, in priority order."""
    found: dict[tuple[str, str], list[Component]] = {}
    for base in dirs:
        if not base.is_dir():
            continue
        for kind in ("pack", "bridge"):
            manifests = sorted(base.glob(f"*/{kind}.yaml")) + sorted(base.glob(f"*/*/{kind}.yaml"))
            for manifest in manifests:
                if "fixtures" in manifest.relative_to(base).parts:
                    continue
                data = load_yaml(manifest)
                cid = data.get("id") or manifest.parent.name
                comp = Component(kind, cid, str(data.get("version", "0.0.0")), manifest.parent, data)
                found.setdefault((kind, cid), []).append(comp)
    return found


def qualify(name: str, context: str | None) -> str:
    if ":" in name or not context:
        return name
    return f"{context}:{name}"


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


# --------------------------------------------------------------------------- config


@dataclass
class Config:
    root: Path
    profile: dict[str, Any]
    components: list[Component] = field(default_factory=list)
    types: dict[str, TypeDef] = field(default_factory=dict)
    links: dict[str, LinkDef] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    views: list[View] = field(default_factory=list)
    roles: dict[str, list[str]] = field(default_factory=dict)
    problems: list[Diagnostic] = field(default_factory=list)
    overrides: dict[str, str] = field(default_factory=dict)
    waivers: list[dict[str, Any]] = field(default_factory=list)

    # ---- lookups
    def component(self, cid: str) -> Component | None:
        return next((c for c in self.components if c.id == cid), None)

    def links_from(self, type_qname: str) -> list[LinkDef]:
        return [l for l in self.links.values() if type_qname in l.from_types]

    def links_to(self, type_qname: str) -> list[LinkDef]:
        return [l for l in self.links.values() if type_qname in l.to_types]

    # bondstone: REQ-GRA-004
    def resolve_link_key(self, type_qname: str, key: str) -> tuple[LinkDef | None, str | None]:
        """Map a frontmatter key to a link def available for this type.

        Returns (linkdef, error)."""
        candidates = self.links_from(type_qname)
        if ":" in key:
            match = [l for l in candidates if l.qname == key]
        else:
            match = [l for l in candidates if l.name == key]
        if len(match) == 1:
            return match[0], None
        if len(match) > 1:
            names = ", ".join(l.qname for l in match)
            return None, f"link name '{key}' is ambiguous ({names}); use the qualified name"
        return None, None

    def rule(self, qid: str) -> Rule | None:
        return next((r for r in self.rules if r.qid == qid), None)

    def code_settings(self) -> dict[str, Any]:
        return self.profile.get("code") or {}


# bondstone: ENG-001
def _problem(message: str, rule: str = "bondstone/profile", severity: str = ERROR) -> Diagnostic:
    return Diagnostic(rule, severity, message, path=str(PROFILE_PATH))


# bondstone: REQ-PRF-001, REQ-PRF-002, REQ-PRF-003, REQ-PRF-006
def load_config(root: Path, extra_sources: list[Path] | None = None) -> Config:
    profile_file = root / PROFILE_PATH
    if not profile_file.is_file():
        raise BondstoneError(f"missing {profile_file}")
    profile = load_yaml(profile_file)
    if not isinstance(profile, dict):
        raise BondstoneError(f"{profile_file}: expected a mapping")

    cfg = Config(root=root, profile=profile)
    sources = [root / s for s in as_list(profile.get("sources"))]
    sources = [*(extra_sources or []), *sources, LIBRARY / "packs", LIBRARY / "bridges"]
    index = index_components(sources)

    # ---- resolve packs and bridges
    for kind, key in (("pack", "packs"), ("bridge", "bridges")):
        for ref in as_list(profile.get(key)):
            cid, spec = parse_ref(str(ref))
            candidates = index.get((kind, cid), [])
            if not candidates:
                cfg.problems.append(_problem(f"{kind} '{cid}' not found in sources or library"))
                continue
            chosen = next((c for c in candidates if version_matches(c.version, spec)), None)
            if chosen is None:
                versions = ", ".join(c.version for c in candidates)
                cfg.problems.append(
                    _problem(f"{kind} '{cid}': no version matches '{spec}' (available: {versions})")
                )
                continue
            cfg.components.append(chosen)

    packs = {c.id: c for c in cfg.components if c.kind == "pack"}

    for comp in cfg.components:
        if comp.kind != "bridge":
            continue
        for pid, spec in (comp.data.get("requires") or {}).items():
            pack = packs.get(pid)
            if pack is None:
                cfg.problems.append(
                    _problem(f"bridge '{comp.id}' requires pack '{pid}', which is not in the profile")
                )
            elif not version_matches(pack.version, str(spec)):
                cfg.problems.append(
                    _problem(
                        f"bridge '{comp.id}' requires {pid} {spec}, profile has {pack.version}"
                    )
                )

    # ---- types
    for comp in cfg.components:
        if comp.kind != "pack":
            continue
        for name, spec in (comp.data.get("types") or {}).items():
            qname = f"{comp.id}:{name}"
            cfg.types[qname] = TypeDef(qname, comp.id, name, spec or {}, comp.dir)

    # ---- links (packs and bridges)
    cfg.links[PART_OF] = LinkDef(PART_OF, "bondstone", "part_of", [], [], description="item belongs to document")
    for comp in cfg.components:
        context = comp.id if comp.kind == "pack" else None
        for name, spec in (comp.data.get("links") or {}).items():
            spec = spec or {}
            qname = f"{comp.id}:{name}"
            cfg.links[qname] = LinkDef(
                qname=qname,
                owner=comp.id,
                name=name,
                from_types=[qualify(t, context) for t in as_list(spec.get("from"))],
                to_types=[qualify(t, context) for t in as_list(spec.get("to"))],
                min=int(spec.get("min", 0)),
                max=spec.get("max"),
                description=spec.get("description", ""),
            )

    # ---- roles (bridges + profile)
    for comp in cfg.components:
        if comp.kind == "bridge":
            for role, types in (comp.data.get("roles") or {}).items():
                cfg.roles.setdefault(role, []).extend(as_list(types))
        elif comp.data.get("roles"):
            cfg.problems.append(
                _problem(f"pack '{comp.id}' declares roles; roles belong in bridges or the profile")
            )
    for role, types in (profile.get("roles") or {}).items():
        cfg.roles.setdefault(role, []).extend(as_list(types))

    # ---- rules and views
    def add_rules(owner: str, context: str | None, specs: Any) -> None:
        for spec in as_list(specs):
            rid = spec.get("id")
            if not rid:
                cfg.problems.append(_problem(f"{owner}: rule without id"))
                continue
            severity = spec.get("severity", ERROR)
            if severity not in SEVERITIES:
                cfg.problems.append(_problem(f"{owner}/{rid}: invalid severity '{severity}'"))
                severity = ERROR
            cfg.rules.append(
                Rule(f"{owner}/{rid}", owner, spec, severity, bool(spec.get("locked")), context)
            )

    for comp in cfg.components:
        context = comp.id if comp.kind == "pack" else None
        add_rules(comp.id, context, comp.data.get("rules"))
        for spec in as_list(comp.data.get("views")):
            cfg.views.append(View(f"{comp.id}/{spec['id']}", comp.id, spec, context))
    add_rules("profile", None, profile.get("rules"))
    for spec in as_list(profile.get("views")):
        cfg.views.append(View(f"profile/{spec['id']}", "profile", spec, None))

    # ---- overrides
    for qid, ov in (profile.get("overrides") or {}).items():
        severity = (ov or {}).get("severity") if isinstance(ov, dict) else ov
        if severity not in SEVERITIES:
            cfg.problems.append(_problem(f"override for '{qid}': invalid severity '{severity}'"))
            continue
        rule = cfg.rule(qid)
        if rule and rule.locked and _rank(severity) < _rank(rule.severity):
            cfg.problems.append(
                _problem(f"override for '{qid}' ignored: rule is locked and cannot be loosened")
            )
            continue
        if rule is None and not qid.startswith("bondstone/"):
            cfg.problems.append(_problem(f"override for unknown rule '{qid}'", severity=WARN))
        cfg.overrides[qid] = severity

    cfg.roles = {role: list(dict.fromkeys(types)) for role, types in cfg.roles.items()}
    cfg.waivers = as_list(profile.get("waivers"))
    return cfg


def _rank(severity: str) -> int:
    return {OFF: 0, WARN: 1, ERROR: 2}[severity]
