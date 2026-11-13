"""Build the effective configuration from the profile and its packs and bridges.

This is also where the checks live that a JSON Schema cannot express, such as whether a type
that a rule names exists. `bondstone profile check` reports exactly `Config.problems`."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .catalogue import engine_rule
from .model import (
    CONFIG_RULE,
    ERROR,
    PART_OF,
    PROFILE_PATH,
    TRAITS,
    WARN,
    Component,
    Diagnostic,
    ItemsDef,
    LinkDef,
    Rule,
    TypeDef,
    View,
    rank,
)
from .resolve import resolve

RESERVED_KEYS = ("id", "type")
RESERVED_OWNERS = ("bondstone", "profile")
SELECTOR_KEYS = ("type", "role", "trait", "status", "where", "covered")
DEFAULT_ITEM_HEADING = "### {id}: {title}"

# clause kind -> the other keys it accepts
NODE_CLAUSES: dict[str, tuple[str, ...]] = {
    "link": ("to", "min", "all"),
    "incoming": ("from", "min"),
    "field": (),
    "section": (),
    "contains": (),
    "items": (),
    "covered": (),
    "file_field": (),
    "any": (),
}
DIFF_CLAUSES: dict[str, tuple[str, ...]] = {
    "changed": ("traced", "min"),
    "exists": ("min",),
    "any": (),
}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def qualify(name: str, context: str | None) -> str:
    """Type names are unqualified inside their own pack and qualified everywhere else."""
    if ":" in name or not context:
        return name
    return f"{context}:{name}"


# --------------------------------------------------------------------------- templates (D8)

PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(?::([^{}]*))?\}")
SLUG_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_NUMBER_FORMAT = re.compile(r"0?(\d+)?d?")


def placeholders(template: str) -> list[str]:
    return [match.group(1) for match in PLACEHOLDER.finditer(template)]


def template_problem(template: str) -> str | None:
    """Why a template is malformed, or None."""
    if "{" in PLACEHOLDER.sub("", template) or "}" in PLACEHOLDER.sub("", template):
        return f"'{template}' has an unbalanced or empty placeholder"
    for match in PLACEHOLDER.finditer(template):
        name, fmt = match.groups()
        if fmt is not None and (name != "n" or not _NUMBER_FORMAT.fullmatch(fmt)):
            return f"'{template}': only {{n}} takes a format, such as {{n:03d}}"
    return None


# bondstone: REQ-GRA-002
def id_regex(template: str, values: dict[str, Any] | None = None) -> str:
    """The pattern an id must match in full, derived from its template.

    `{n}` is a number (`{n:03d}`: at least three digits), `{slug}` a lower-case slug. Any
    other placeholder is a field: its value when `values` has one, anything otherwise."""
    out, position = "", 0
    for match in PLACEHOLDER.finditer(template):
        out += re.escape(template[position:match.start()])
        position = match.end()
        name, fmt = match.groups()
        if name == "n":
            number = _NUMBER_FORMAT.fullmatch(fmt or "")
            width = number.group(1) if number else None
            out += rf"\d{{{int(width)},}}" if width else r"\d+"
        elif name == "slug":
            out += SLUG_PATTERN
        elif values is not None and values.get(name) not in (None, ""):
            out += re.escape(str(values[name]))
        else:
            out += r"[^\s/]+"
    return "^" + out + re.escape(template[position:]) + "$"


# bondstone: REQ-GRA-002
def path_glob(template: str) -> str:
    """The glob that finds a type's documents: `docs/adr/{id}-{slug}.md` gives `docs/adr/*.md`."""
    segments = []
    for segment in template.split("/"):
        matches = list(PLACEHOLDER.finditer(segment))
        if matches:
            segment = segment[:matches[0].start()] + "*" + segment[matches[-1].end():]
        segments.append(segment)
    return "/".join(segments)


def heading_pattern(template: str) -> tuple[int, re.Pattern[str]] | None:
    """Level and text pattern of an item heading template such as `### {id}: {title}`."""
    match = re.fullmatch(r"(#{1,6})\s+(.+)", template.strip())
    if not match or "{id}" not in match.group(2):
        return None
    text, out, position = match.group(2), "", 0
    for found in PLACEHOLDER.finditer(text):
        out += _literal(text[position:found.start()])
        position = found.end()
        if found.group(1) == "id":
            out += r"(?P<id>[^\s:]+)"
        elif found.group(1) == "title":
            out += r"(?P<title>.+?)"
        else:
            return None
    try:
        return len(match.group(1)), re.compile("^" + out + _literal(text[position:]) + "$")
    except re.error:
        return None


def _literal(text: str) -> str:
    return r"\s*".join(re.escape(part) for part in re.split(r"\s+", text))


# --------------------------------------------------------------------------- configuration


@dataclass
class Lock:
    """A rule whose severity may be raised but not lowered, and that cannot be waived."""

    severity: str  # the lowest severity the rule may have
    by: str  # the pack, bridge or preset that locks it


@dataclass
class Config:
    root: Path
    profile: dict[str, Any] = field(default_factory=dict)
    components: list[Component] = field(default_factory=list)
    types: dict[str, TypeDef] = field(default_factory=dict)
    links: dict[str, LinkDef] = field(default_factory=dict)
    roles: dict[str, list[str]] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    views: list[View] = field(default_factory=list)
    overrides: dict[str, str] = field(default_factory=dict)
    override_sources: dict[str, str] = field(default_factory=dict)  # rule id -> "profile" | "preset <id>"
    locks: dict[str, Lock] = field(default_factory=dict)
    waivers: list[dict[str, Any]] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)

    @property
    def errors(self) -> list[Diagnostic]:
        """Configuration errors: with any of these the checker cannot run (exit code 2)."""
        return [p for p in self.problems if p.rule == CONFIG_RULE and p.severity == ERROR]

    @property
    def docs(self) -> list[str]:
        return list(self.profile.get("docs") or [])

    @property
    def code_include(self) -> list[str]:
        return list((self.profile.get("code") or {}).get("include") or [])

    @property
    def code_exclude(self) -> list[str]:
        return list((self.profile.get("code") or {}).get("exclude") or [])

    @property
    def baseline(self) -> str | None:
        """The commit whose documents count as already adopted (`bondstone baseline`)."""
        value = self.profile.get("baseline")
        return str(value) if value else None

    def rule(self, qid: str) -> Rule | None:
        return next((r for r in self.rules if r.qid == qid), None)

    # bondstone: REQ-PRF-007
    def severity(self, qid: str, default: str) -> str:
        """A rule's effective severity: its default unless a preset or the profile overrides it."""
        return self.overrides.get(qid, default)

    def links_from(self, type_qname: str) -> list[LinkDef]:
        return [link for link in self.links.values() if type_qname in link.from_types]

    def links_to(self, type_qname: str) -> list[LinkDef]:
        return [link for link in self.links.values() if type_qname in link.to_types]

    def resolve_link_key(self, type_qname: str, key: str) -> tuple[LinkDef | None, str | None]:
        """Map a frontmatter key to a link that may start at this type: (link, error)."""
        candidates = self.links_from(type_qname)
        if ":" in key:
            found = [link for link in candidates if link.qname == key]
        else:
            found = [link for link in candidates if link.name == key]
        if len(found) > 1:
            names = ", ".join(link.qname for link in found)
            return None, f"link name '{key}' is ambiguous ({names}); use the qualified name"
        return (found[0], None) if found else (None, None)

    # bondstone: REQ-GRA-008, REQ-RUL-006
    def schema_for(self, type_qname: str) -> dict[str, Any]:
        """The JSON Schema of a document type's frontmatter fields."""
        tdef = self.types[type_qname]
        properties = dict(tdef.spec.get("fields") or {})
        properties.setdefault("title", {"type": "string", "minLength": 1})
        required = list(tdef.spec.get("required") or [])
        traits = tdef.traits
        if "lifecycle" in traits:
            properties["status"] = {"enum": list(traits["lifecycle"].get("statuses") or [])}
            required.append("status")
        if "owned" in traits:
            properties.setdefault("owner", {"type": "string", "minLength": 1})
            required.append("owner")
        return {
            "type": "object",
            "properties": properties,
            "required": sorted(set(required)),
            "additionalProperties": False,
        }


# bondstone: REQ-PRF-006, REQ-PRF-010
def load_config(root: Path, extra_sources: list[Path] | None = None) -> Config:
    """The effective configuration of a repository, with every problem found on the way.

    Raises EnvironmentProblem when there is no profile; everything else is reported in
    `Config.problems`."""
    resolution = resolve(root, extra_sources)
    cfg = Config(root=root, components=resolution.components, problems=list(resolution.problems))
    if resolution.profile is None:
        return cfg
    cfg.profile = resolution.profile
    if cfg.errors:
        return cfg  # a pack or bridge is missing or invalid: checking the rest would only add noise
    builder = _Builder(cfg)
    builder.types()
    builder.links()
    builder.roles()
    builder.rules_and_views()
    builder.overrides()
    builder.unbridged_packs()
    cfg.waivers = list(cfg.profile.get("waivers") or [])
    return cfg


# bondstone: REQ-PRF-006
class _Builder:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def bad(self, message: str, path: str = PROFILE_PATH) -> None:
        self.cfg.problems.append(Diagnostic(CONFIG_RULE, ERROR, message, path=path))

    # ----------------------------------------------------------------------- types

    def types(self) -> None:
        cfg = self.cfg
        for comp in cfg.components:
            if comp.id in RESERVED_OWNERS:
                self.bad(f"id: '{comp.id}' is reserved", comp.manifest)
            instructions = comp.data.get("instructions")
            if instructions and not (comp.dir / instructions).is_file():
                self.bad(f"instructions: file '{instructions}' not found", comp.manifest)
            if comp.kind != "pack":
                continue
            for name, spec in (comp.data.get("types") or {}).items():
                spec = spec or {}
                qname = f"{comp.id}:{name}"
                cfg.types[qname] = TypeDef(
                    qname=qname, owner=comp.id, name=name, spec=spec, component_dir=comp.dir,
                    embedded=bool(spec.get("embedded")), id_template=spec.get("id"),
                    id_pattern=spec.get("id_pattern"), path_template=spec.get("path"),
                    path_glob=path_glob(spec["path"]) if spec.get("path") else None,
                )
        used_as_items: set[str] = set()
        for comp in cfg.components:
            if comp.kind != "pack":
                continue
            for name in comp.data.get("types") or {}:
                tdef = cfg.types[f"{comp.id}:{name}"]
                self._check_type(comp, tdef)
                if tdef.items is not None:
                    used_as_items.add(tdef.items.type)
        for tdef in cfg.types.values():
            if tdef.embedded and tdef.qname not in used_as_items:
                comp = next(c for c in cfg.components if c.id == tdef.owner)
                self.bad(f"types.{tdef.name}: embedded type is not used by any type's `items`", comp.manifest)

    def _check_type(self, comp: Component, tdef: TypeDef) -> None:
        spec, where = tdef.spec, f"types.{tdef.name}"

        def bad(message: str) -> None:
            self.bad(f"{where}: {message}", comp.manifest)

        fields = spec.get("fields") or {}
        traits = tdef.traits
        known_fields = {"title", *fields}
        if "lifecycle" in traits:
            known_fields.add("status")
        if "owned" in traits:
            known_fields.add("owner")

        for key in RESERVED_KEYS:
            if key in fields:
                bad(f"field '{key}' is reserved; every document has it already")
        if fields:
            try:
                Draft202012Validator.check_schema({"type": "object", "properties": fields})
            except SchemaError as exc:
                location = ".".join(str(p) for p in list(exc.absolute_path)[1:]) or "fields"
                bad(f"fields are not valid JSON Schema ({location}: {exc.message})")
        for name in spec.get("required") or []:
            if name not in known_fields:
                bad(f"required field '{name}' is not declared in `fields`")

        if tdef.embedded:
            for key in ("id", "id_pattern", "path", "template", "items", "fields", "required"):
                if key in spec:
                    bad(f"an embedded type takes no `{key}`; its documents' type declares the items")
            for trait in ("owned", "supersedable", "immutable"):
                if trait in traits:
                    bad(f"trait '{trait}' needs frontmatter and is not available on an embedded type")
        else:
            if not tdef.id_template or not tdef.path_template:
                bad("needs an `id` template and a `path` template (or `embedded: true`)")
            for key, template in (("id", tdef.id_template), ("path", tdef.path_template)):
                problem = template_problem(template) if template else None
                if problem:
                    bad(f"{key}: {problem}")
            if tdef.id_template and not template_problem(tdef.id_template):
                for name in placeholders(tdef.id_template):
                    if name not in ("n", "slug") and name not in fields:
                        bad(f"id: placeholder {{{name}}} is neither n, slug nor a declared field")
            if tdef.path_template and (tdef.path_template.startswith("/") or ".." in tdef.path_template.split("/")):
                bad("path: must be relative to the repository root")
            template = spec.get("template")
            if template and not (tdef.component_dir / template).is_file():
                bad(f"template '{template}' not found")
        if tdef.id_pattern:
            try:
                re.compile(tdef.id_pattern)
            except re.error as exc:
                bad(f"id_pattern is not a valid regular expression ({exc})")

        self._check_traits(tdef, bad)
        if "items" in spec and not tdef.embedded:
            self._check_items(tdef, fields, bad)

    def _check_traits(self, tdef: TypeDef, bad: Any) -> None:
        traits = tdef.traits
        lifecycle = traits.get("lifecycle")
        statuses = list((lifecycle or {}).get("statuses") or [])

        def known(values: Any, what: str) -> None:
            for value in as_list(values):
                if value not in statuses:
                    bad(f"{what}: '{value}' is not one of the lifecycle statuses")

        if lifecycle is not None:
            known(lifecycle.get("initial"), "lifecycle.initial")
            known(lifecycle.get("default"), "lifecycle.default")
            for source, targets in (lifecycle.get("transitions") or {}).items():
                known(source, "lifecycle.transitions")
                known(targets, f"lifecycle.transitions.{source}")
            if tdef.embedded and not lifecycle.get("default"):
                bad("lifecycle.default is required on an embedded type: "
                    "an item without a `Status:` line takes it")
        for trait, keys in (("immutable", ("when",)), ("code-traceable", ("when", "retired"))):
            options = traits.get(trait)
            if options is None:
                continue
            for key in keys:
                if options.get(key) is not None:
                    if lifecycle is None:
                        bad(f"{trait}.{key} lists statuses, so the type needs the lifecycle trait")
                    else:
                        known(options[key], f"{trait}.{key}")
        tracing = traits.get("code-traceable") or {}
        both = sorted(set(as_list(tracing.get("when"))) & set(as_list(tracing.get("retired"))))
        if both:
            bad(f"code-traceable: {', '.join(both)} cannot be in both `when` and `retired`")

    def _check_items(self, tdef: TypeDef, fields: dict[str, Any], bad: Any) -> None:
        spec = tdef.spec["items"]
        if ":" in spec["type"]:
            bad(f"items.type '{spec['type']}' must be a type of the same pack")
            return
        item_type = self.cfg.types.get(qualify(spec["type"], tdef.owner))
        if item_type is None:
            bad(f"items.type '{spec['type']}' is not defined")
            return
        if not item_type.embedded:
            bad(f"items.type '{spec['type']}' must be declared with `embedded: true`")
        heading_template = spec.get("heading", DEFAULT_ITEM_HEADING)
        heading = heading_pattern(heading_template)
        if heading is None:
            bad(f"items.heading '{heading_template}' must look like '### {{id}}: {{title}}': "
                "a heading level, {id} and optionally {title}")
            return
        id_template = spec.get("id")
        if id_template:
            problem = template_problem(id_template)
            if problem:
                bad(f"items.id: {problem}")
                id_template = None
            else:
                for name in placeholders(id_template):
                    if name not in ("n", "slug") and name not in fields:
                        bad(f"items.id: placeholder {{{name}}} is neither n, slug nor a field of {tdef.name}")
        tdef.items = ItemsDef(type=item_type.qname, level=heading[0], heading=heading[1],
                              heading_template=heading_template, section=spec.get("section"),
                              id_template=id_template)

    # ----------------------------------------------------------------------- links and roles

    def links(self) -> None:
        cfg = self.cfg
        cfg.links[PART_OF] = LinkDef(PART_OF, "bondstone", "part_of", [], [],
                                     description="An item belongs to its document.")
        for comp in cfg.components:
            context = comp.id if comp.kind == "pack" else None
            for name, spec in (comp.data.get("links") or {}).items():
                where = f"links.{name}"
                link = LinkDef(
                    qname=f"{comp.id}:{name}", owner=comp.id, name=name,
                    from_types=[qualify(t, context) for t in as_list(spec["from"])],
                    to_types=[qualify(t, context) for t in as_list(spec["to"])],
                    min=int(spec.get("min", 0)), max=spec.get("max"),
                    description=spec.get("description", ""),
                )
                cfg.links[link.qname] = link
                for type_name in [*link.from_types, *link.to_types]:
                    if type_name not in cfg.types:
                        self.bad(f"{where}: {self._unknown_type(type_name)}", comp.manifest)
                for type_name in link.from_types:
                    tdef = cfg.types.get(type_name)
                    if tdef is None:
                        continue
                    if tdef.embedded:
                        self.bad(f"{where}: links are written in frontmatter, so they cannot start "
                                 f"at the embedded type {type_name}", comp.manifest)
                    elif name in RESERVED_KEYS or name in cfg.schema_for(type_name)["properties"]:
                        self.bad(f"{where}: '{name}' is already a frontmatter key of {type_name}", comp.manifest)
                if link.max is not None and link.max < link.min:
                    self.bad(f"{where}: max is lower than min", comp.manifest)
        for tdef in cfg.types.values():
            options = tdef.traits.get("supersedable")
            if options is not None and not tdef.embedded:
                name = qualify(options.get("link", "supersedes"), tdef.owner)
                link = cfg.links.get(name)
                if link is None or tdef.qname not in link.from_types:
                    comp = next(c for c in cfg.components if c.id == tdef.owner)
                    self.bad(f"types.{tdef.name}: supersedable link '{name}' is not a link from this type",
                             comp.manifest)

    def _unknown_type(self, name: str) -> str:
        if ":" not in name:
            return f"unknown type '{name}' (use a qualified name such as pack:Type)"
        return f"unknown type '{name}'"

    def roles(self) -> None:
        cfg = self.cfg
        sources = [(c.manifest, c.data.get("roles") or {}) for c in cfg.components if c.kind == "bridge"]
        sources.append((PROFILE_PATH, cfg.profile.get("roles") or {}))
        for path, roles in sources:
            for role, types in roles.items():
                for type_name in as_list(types):
                    if type_name not in cfg.types:
                        self.bad(f"roles.{role}: {self._unknown_type(type_name)}", path)
                    elif type_name not in cfg.roles.setdefault(role, []):
                        cfg.roles[role].append(type_name)
                cfg.roles.setdefault(role, [])

    # ----------------------------------------------------------------------- rules and views

    def rules_and_views(self) -> None:
        cfg = self.cfg
        owners = [(c.id, c.id if c.kind == "pack" else None, c.manifest, c.data) for c in cfg.components]
        owners.append(("profile", None, PROFILE_PATH, cfg.profile))
        outputs: dict[str, str] = {}
        for owner, context, path, data in owners:
            seen: set[str] = set()
            for spec in data.get("rules") or []:
                rule = Rule(f"{owner}/{spec['id']}", owner, spec, spec.get("severity", ERROR),
                            bool(spec.get("locked")), context, path)
                if spec["id"] in seen:
                    self.bad(f"rules: rule id '{spec['id']}' is used more than once", path)
                    continue
                seen.add(spec["id"])
                cfg.rules.append(rule)
                if rule.locked:
                    cfg.locks[rule.qid] = Lock(rule.severity, owner)
                self._check_rule(rule)
            seen = set()
            for spec in data.get("views") or []:
                view = View(f"{owner}/{spec['id']}", owner, spec, context)
                if spec["id"] in seen:
                    self.bad(f"views: view id '{spec['id']}' is used more than once", path)
                    continue
                seen.add(spec["id"])
                cfg.views.append(view)
                self._check_view(view, path, outputs)

    def _selector_problems(self, selector: Any, context: str | None) -> list[str]:
        problems: list[str] = []
        if not selector:
            return problems
        for type_name in as_list(selector.get("type")):
            qname = qualify(type_name, context)
            if qname not in self.cfg.types:
                problems.append(self._unknown_type(qname))
        for role in as_list(selector.get("role")):
            if role not in self.cfg.roles:
                problems.append(f"role '{role}' is not assigned by any bridge or the profile")
        for trait in as_list(selector.get("trait")):
            if trait not in TRAITS:
                problems.append(f"unknown trait '{trait}'")
        return problems

    def _link_exists(self, name: str) -> bool:
        return any(name in (link.qname, link.name) for link in self.cfg.links.values() if link.qname != PART_OF)

    def _check_rule(self, rule: Rule) -> None:
        spec, path = rule.spec, rule.source

        def bad(message: str) -> None:
            self.bad(f"{rule.qid}: {message}", path or PROFILE_PATH)

        kinds = [key for key in ("when", "on_change", "for_each") if key in spec]
        if len(kinds) != 1:
            bad("a rule needs exactly one of `when`, `on_change` and `for_each`")
            return
        if "exempt" in spec and "on_change" not in spec:
            bad("`exempt` only applies to diff rules (`on_change`)")
        if "on_change" in spec and ("paths" in spec["on_change"]) == ("code" in spec["on_change"]):
            bad("`on_change` needs exactly one of `paths` and `code: true`")
        if "for_each" in spec:
            if "require" in spec:
                bad("an existence rule (`for_each`) takes no `require`")
            for type_name in as_list(spec["for_each"].get("type")):
                qname = qualify(type_name, rule.context_pack)
                if qname not in self.cfg.types:
                    bad(self._unknown_type(qname))
            return
        for message in self._selector_problems(spec.get("when"), rule.context_pack):
            bad(message)
        if not spec.get("require"):
            bad("rule has no `require` clauses")
            return
        allowed = DIFF_CLAUSES if "on_change" in spec else NODE_CLAUSES
        for clause in spec["require"]:
            self._check_clause(rule, clause, allowed, bad, nested=False)

    def _check_clause(self, rule: Rule, clause: dict[str, Any], allowed: dict[str, tuple[str, ...]],
                      bad: Any, nested: bool) -> None:
        every = {**NODE_CLAUSES, **DIFF_CLAUSES}
        kinds = [key for key in every if key in clause]
        if len(kinds) != 1:
            bad(f"a clause needs exactly one of {', '.join(allowed)}; got {', '.join(sorted(clause)) or 'nothing'}")
            return
        kind = kinds[0]
        if kind not in allowed:
            where = "diff rule (`on_change`)" if allowed is DIFF_CLAUSES else "node rule (`when`)"
            bad(f"clause `{kind}` is not available in a {where}")
            return
        stray = sorted(key for key in clause if key != kind and key not in every[kind])
        if stray:
            bad(f"clause `{kind}` does not take {', '.join(f'`{k}`' for k in stray)}")
        if kind == "any":
            for alternative in clause["any"]:
                self._check_clause(rule, alternative, allowed, bad, nested=True)
            return
        if nested and clause.get("traced"):
            bad("`traced` is not supported inside `any`")
        for key in ("to", "from", "changed", "exists"):
            for message in self._selector_problems(clause.get(key), rule.context_pack):
                bad(message)
        if kind in ("link", "incoming") and not self._link_exists(clause[kind]):
            bad(f"unknown link '{clause[kind]}'")
        if kind == "contains":
            try:
                re.compile(clause["contains"])
            except re.error as exc:
                bad(f"`contains` is not a valid regular expression ({exc})")
        if kind == "items":
            qname = qualify(clause["items"]["type"], rule.context_pack)
            if qname not in self.cfg.types:
                bad(self._unknown_type(qname))

    def _check_view(self, view: View, path: str, outputs: dict[str, str]) -> None:
        spec = view.spec

        def bad(message: str) -> None:
            self.bad(f"{view.qid}: {message}", path)

        output = view.output
        if output.startswith("/") or ".." in output.split("/"):
            bad(f"output '{output}' must be a path inside the repository")
        if output in outputs:
            bad(f"output '{output}' is already written by view {outputs[output]}")
        outputs.setdefault(output, view.qid)
        for key in ("select", "rows", "cols"):
            for message in self._selector_problems(spec.get(key), view.context_pack):
                bad(message)
        for level in spec.get("levels") or []:
            name = level.get("link") or level.get("incoming")
            if not self._link_exists(name):
                bad(f"unknown link '{name}'")
        # bondstone: REQ-VIE-006, REQ-VIE-007
        matrix = spec.get("render") == "matrix"
        only_matrix = [key for key in ("rows", "cols", "via") if key in spec]
        if matrix and len(only_matrix) < 3:
            bad("a matrix needs `rows`, `cols` and `via`")
        elif not matrix and only_matrix:
            bad(f"{', '.join(f'`{key}`' for key in only_matrix)} only appl{'ies' if len(only_matrix) == 1 else 'y'} "
                "to `render: matrix`")
        backwards = [c for c in spec.get("columns") or [] if c.startswith("<-")]
        for name in [*spec.get("via", []), *backwards]:
            if not self._link_exists(name.removeprefix("<-")):
                bad(f"unknown link '{name.removeprefix('<-')}'")

    # ----------------------------------------------------------------------- overrides

    # bondstone: REQ-PRF-007, REQ-PRF-014, REQ-PRF-015
    def overrides(self) -> None:
        """Severities and locks, layer by layer: presets in the order they apply, then the profile."""
        cfg = self.cfg
        layers = [(c.manifest, c.id, c.data) for c in cfg.components if c.kind == "preset"]
        layers.append((PROFILE_PATH, None, cfg.profile))
        for path, preset, data in layers:
            for qid, severity in (data.get("overrides") or {}).items():
                where = f"overrides.{qid}"
                if self._default_severity(qid, where, path) is None:
                    continue
                lock = cfg.locks.get(qid)
                if lock is not None and rank(severity) < rank(lock.severity):
                    rule = cfg.rule(qid)
                    by = "" if rule is not None and rule.owner == lock.by else f" by preset '{lock.by}'"
                    self.bad(f"{where}: the rule is locked{by}; its severity ({lock.severity}) "
                             "can be raised but not lowered", path)
                    continue
                cfg.overrides[qid] = severity
                cfg.override_sources[qid] = f"preset {preset}" if preset else "profile"
            for qid in data.get("lock") or []:
                default = self._default_severity(qid, f"lock: {qid}", path)
                if default is None or qid in cfg.locks:
                    continue  # the first lock sets the floor
                cfg.locks[qid] = Lock(cfg.severity(qid, default), preset or "profile")
                rule = cfg.rule(qid)
                if rule is not None:
                    rule.locked = True

    def _default_severity(self, qid: str, where: str, path: str) -> str | None:
        """The default severity of a rule that may be overridden; None, after reporting, when it may not."""
        if qid.startswith("bondstone/"):
            engine = engine_rule(qid)
            if engine is None:
                self.bad(f"{where}: unknown engine rule", path)
                return None
            if not engine.overridable:
                self.bad(f"{where}: configuration errors cannot be overridden", path)
                return None
            return engine.severity
        rule = self.cfg.rule(qid)
        if rule is None:
            self.bad(f"{where}: unknown rule", path)
            return None
        return rule.severity

    # ----------------------------------------------------------------------- bridges

    # bondstone: REQ-PRF-009
    def unbridged_packs(self) -> None:
        """Warn when the packs fall into groups that no bridge connects."""
        cfg = self.cfg
        packs = [c.id for c in cfg.components if c.kind == "pack"]
        group = {pack: pack for pack in packs}

        def find(pack: str) -> str:
            while group[pack] != pack:
                pack = group[pack]
            return pack

        for comp in cfg.components:
            if comp.kind == "bridge":
                required = [pack for pack in comp.data["requires"] if pack in group]
                for first, second in zip(required, required[1:]):
                    group[find(first)] = find(second)
        groups: dict[str, list[str]] = {}
        for pack in packs:
            groups.setdefault(find(pack), []).append(pack)
        if len(groups) > 1:
            listing = "; ".join(", ".join(sorted(members)) for members in groups.values())
            cfg.problems.append(Diagnostic(
                "bondstone/unbridged-packs", WARN,
                f"packs form disconnected groups ({listing}); add a bridge to connect them",
                path=PROFILE_PATH))
