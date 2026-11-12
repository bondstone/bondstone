"""What agents and people ask before they act: which rules are active, what one rule means,
and the instructions an agent follows in this repository.

Every answer uses effective severities, after the profile's overrides, because that is what
`check` will apply."""

from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass
from typing import Any

import yaml

from .catalogue import ENGINE_RULES, EngineRule
from .config import PLACEHOLDER, Config
from .context import describe_clause
from .model import IGNORE, Refused, Rule


@dataclass
class RuleInfo:
    """One active rule as `bondstone rules` lists it."""

    id: str
    kind: str  # node | diff | existence | engine
    severity: str  # effective
    default: str
    set_by: str  # "default" | "profile": where the effective severity comes from
    locked: bool
    description: str
    declared_in: str | None  # manifest of a declared rule; None for engine rules
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def _info(cfg: Config, rule: Rule | EngineRule) -> RuleInfo:
    if isinstance(rule, Rule):
        rule_id, kind, default, locked = rule.qid, rule.kind, rule.severity, rule.locked
        description, declared_in, hint = rule.description, rule.source, rule.spec.get("hint")
    else:
        rule_id, kind, default, locked = rule.id, "engine", rule.severity, not rule.overridable
        description, declared_in, hint = rule.fires, None, None
    return RuleInfo(rule_id, kind, cfg.severity(rule_id, default), default,
                    "profile" if rule_id in cfg.overrides else "default", locked, description, declared_in, hint)


# bondstone: REQ-AGT-001
def list_rules(cfg: Config) -> list[RuleInfo]:
    """Every rule that can report in this repository: declared rules first, then engine rules."""
    return [_info(cfg, rule) for rule in [*cfg.rules, *ENGINE_RULES]]


def rules_text(rules: list[RuleInfo]) -> str:
    lines = []
    for rule in rules:
        notes = []
        if rule.set_by == "profile":
            notes.append(f"default: {rule.default}")
        if rule.locked:
            notes.append("locked")
        suffix = f" [{'; '.join(notes)}]" if notes else ""
        lines.append(f"{rule.severity:<6} {rule.id}: {rule.description}{suffix}")
    return "\n".join(lines) + "\n"


def _find(cfg: Config, rule_id: str) -> Rule | EngineRule:
    known: dict[str, Rule | EngineRule] = {rule.qid: rule for rule in cfg.rules}
    known.update({rule.id: rule for rule in ENGINE_RULES})
    if rule_id in known:
        return known[rule_id]
    close = difflib.get_close_matches(rule_id, list(known), n=3, cutoff=0.5)
    suffix = [name for name in known if name.split("/", 1)[-1] == rule_id]
    suggestions = list(dict.fromkeys(suffix + close))
    hint = f"; did you mean {', '.join(suggestions)}?" if suggestions else "; `bondstone rules` lists them"
    raise Refused(f"unknown rule '{rule_id}'{hint}")


def _severity_line(info: RuleInfo) -> str:
    if info.set_by == "profile":
        return f"Severity: {info.severity} (set by the profile; default: {info.default})"
    return f"Severity: {info.severity} (default)"


# bondstone: REQ-AGT-002
def explain(cfg: Config, rule_id: str) -> dict[str, Any]:
    """Everything about one rule, declared or engine: what it asks, why, and how to satisfy it."""
    rule = _find(cfg, rule_id)
    info = _info(cfg, rule)
    out = info.to_dict()
    if isinstance(rule, Rule):
        if rule.kind == "diff":
            paths = ", ".join(str(path) for path in rule.spec["on_change"].get("paths") or [])
            out["asks"] = [f"When files matching {paths} change, it asks that {describe_clause(clause)}."
                           for clause in rule.spec.get("require") or []]
        out["spec"] = {key: value for key, value in rule.spec.items()
                       if key not in ("id", "description", "severity", "locked", "hint")}
    else:
        out.update({"fires": rule.fires, "why": rule.why, "fix": rule.fix})
        if rule.note:
            out["note"] = rule.note
        out.pop("description", None)
    return out


def explain_text(cfg: Config, rule_id: str) -> str:
    data = explain(cfg, rule_id)
    info = _info(cfg, _find(cfg, rule_id))
    if info.kind == "engine":
        lines = [f"{info.id} (engine rule)", _severity_line(info), "",
                 f"Fires when: {data['fires']}", f"Why: {data['why']}", f"Fix: {data['fix']}"]
        if data.get("note"):
            lines.append(f"Note: {data['note']}")
        if info.locked:
            lines.append("This rule cannot be overridden or waived.")
        return "\n".join(lines) + "\n"
    lines = [f"{info.id} ({info.kind} rule, declared in {info.declared_in})",
             _severity_line(info) + ("; locked: it can be raised but not lowered or waived" if info.locked else "")]
    if info.description:
        lines += ["", info.description]
    lines += data.get("asks", [])
    if info.hint:
        lines.append(f"Hint: {info.hint}")
    lines += ["", yaml.safe_dump(data["spec"], sort_keys=False, allow_unicode=True, width=100).rstrip()]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- instructions

GENERATED_MARK = "<!-- bondstone:generated agent instructions; do not edit, run `bondstone agent` -->"
MARKDOWN_PATH = "AGENTS.bondstone.md"
SKILL_PATH = ".claude/skills/bondstone/SKILL.md"


def _workflow(cfg: Config) -> list[str]:
    traceable = any("code-traceable" in tdef.traits for tdef in cfg.types.values())
    trailers = sorted({str(rule.spec["exempt"]["trailer"]) for rule in cfg.rules
                       if rule.spec.get("exempt") and cfg.severity(rule.qid, rule.severity) != IGNORE})
    items = any(tdef.embedded for tdef in cfg.types.values())
    steps = [
        "Before you edit code or documents, run `bondstone context --for <paths>`. It lists the documents "
        "to read first and the rules that will fire.",
        "Create a document with `bondstone new <Type> --title \"...\"`, never by hand. It picks the id, the "
        "path and the frontmatter."
        + (" Some types are items: headings inside a document, which you add by hand. The type's entry below "
           "gives the heading and the id to use." if items else ""),
        "Change a status with `bondstone status <ID> <STATUS>`. Replace a document that may no longer be "
        "edited with `bondstone supersede <ID> --title \"...\"`.",
        "Write links as ids in frontmatter, never as paths.",
    ]
    if traceable:
        steps.append("Put a comment `bondstone: <ID>` above the code that implements a node, and update that "
                     "node's document when you change the code.")
    steps += [
        "After you edit documents by hand, run `bondstone gen`. It rewrites the generated files listed below. "
        "Never edit those files or this one yourself.",
        "Before you finish, run `bondstone check --base <upstream branch> --format json` and fix every error. "
        "It compares your working tree, committed or not, with that branch. When a diagnostic has `fix.command`, "
        "run that command. `bondstone explain <rule>` says what a rule wants.",
        "Never weaken `.bondstone/profile.yaml` (overrides, waivers) to make a check pass. Ask the user instead.",
    ]
    if trailers:
        names = ", ".join(f"`{name}`" for name in trailers)
        steps.append(f"Do not add an exemption trailer ({names}) to a commit unless the user asked for one.")
    return steps


def _type_facts(cfg: Config, tdef: Any) -> list[str]:
    spec, traits = tdef.spec, tdef.traits
    facts: list[str] = []
    if tdef.embedded:
        parents = [parent for parent in cfg.types.values() if parent.items and parent.items.type == tdef.qname]
        for parent in parents:
            items = parent.items
            where = f" under `## {items.section}`" if items.section else ""
            facts.append(f"add one by hand inside a `{parent.qname}` document, as a heading "
                         f"`{items.heading_template}`{where}")
            if items.id_template:
                parts = []
                for name, _ in PLACEHOLDER.findall(items.id_template):
                    if name == "n":
                        parts.append("`{n}` is the next free number in that document")
                    elif name != "slug":
                        parts.append(f"`{{{name}}}` is that document's `{name}` field")
                facts.append(f"id: `{items.id_template}`" + (f" ({'; '.join(parts)})" if parts else ""))
    else:
        facts.append(f"location: `{tdef.path_template}`")
        facts.append(f"id: `{tdef.id_template}`")
        schema = cfg.schema_for(tdef.qname)
        needed = [name for name in spec.get("required") or [] if name != "title"
                  and (schema["properties"].get(name) or {}).get("format") != "date"]
        needed += [link.name for link in cfg.links_from(tdef.qname) if link.min > 0]
        sets = "".join(f" --set {name}=..." for name in needed)
        facts.append(f"create: `bondstone new {tdef.qname} --title \"...\"{sets}`")
        fields = [name + (" (required)" if name in schema["required"] else "")
                  for name in schema["properties"] if name not in ("status", "owner")]
        facts.append("fields: " + ", ".join(fields))
        if spec.get("sections"):
            facts.append("required sections: " + ", ".join(spec["sections"]))
    lifecycle = traits.get("lifecycle")
    if lifecycle:
        statuses = " | ".join(str(status) for status in lifecycle.get("statuses") or [])
        notes = []
        if lifecycle.get("initial"):
            notes.append(f"new ones start as `{lifecycle['initial']}`")
        if lifecycle.get("default"):
            notes.append(f"`{lifecycle['default']}` without a `Status:` line under the heading")
        facts.append(f"status: {statuses}" + (f" ({'; '.join(notes)})" if notes else ""))
        if lifecycle.get("transitions"):
            facts.append("allowed status changes: " + "; ".join(
                f"{source} → {', '.join(str(t) for t in targets)}" for source, targets in lifecycle["transitions"].items()))
    if "owned" in traits:
        facts.append("needs an `owner`")
    if "immutable" in traits:
        trait = traits["immutable"]
        when = ", ".join(str(status) for status in trait.get("when") or []) or "created"
        allow = ", ".join(str(key) for key in trait["allow"]) if "allow" in trait else "status"
        facts.append(f"immutable once {when}: only {allow or 'nothing'} may change; supersede it instead of editing it")
    if "code-traceable" in traits:
        trait = traits["code-traceable"]
        text = "tag the code that implements it with a comment `bondstone: <ID>`"
        coverage = cfg.severity("bondstone/code-coverage", str(trait.get("coverage", "warn")))
        if coverage != IGNORE:
            when = f" in status {', '.join(str(s) for s in trait['when'])}" if trait.get("when") else ""
            text += f"; one without a tag{when} is reported ({coverage})"
        if trait.get("retired"):
            text += f"; remove the tag in status {', '.join(str(s) for s in trait['retired'])}"
        facts.append(text)
    links = cfg.links_from(tdef.qname)
    if links:
        facts.append("links: " + "; ".join(
            f"`{link.name}` → {', '.join(link.to_types)}"
            + (f" (at least {link.min})" if link.min else "") + (f" (at most {link.max})" if link.max is not None else "")
            for link in links))
    return facts


# bondstone: REQ-AGT-005
def instructions(cfg: Config) -> str:
    """Agent instructions for this repository, in Markdown.

    They state the workflow, every type, every declared rule with the severity `check` applies,
    the generated views and each component's own guidance."""
    out = [GENERATED_MARK, "# Documentation rules (bondstone)", "",
           "`bondstone` checks this repository's living documentation. The rules below are the ones it enforces.", "",
           "## Workflow", ""]
    out += [f"{number}. {step}" for number, step in enumerate(_workflow(cfg), 1)]
    out += ["", "Active packs and bridges: "
            + (", ".join(f"{c.id}@{c.version} ({c.kind})" for c in cfg.components) or "none"), ""]

    out += ["## Document types", ""]
    for tdef in cfg.types.values():
        out.append(f"### `{tdef.qname}`")
        out.append("")
        if tdef.spec.get("description"):
            out += [" ".join(str(tdef.spec["description"]).split()), ""]
        out += [f"- {fact}" for fact in _type_facts(cfg, tdef)]
        out.append("")

    if cfg.roles:
        out += ["## Roles", "", "Rules name roles so that they work across packs.", ""]
        out += [f"- `{role}`: {', '.join(types)}" for role, types in cfg.roles.items()]
        out.append("")

    out += ["## Rules", "", "Severities are the effective ones, after this repository's overrides.", ""]
    for rule in cfg.rules:
        severity = cfg.severity(rule.qid, rule.severity)
        if severity == IGNORE:
            continue
        line = f"- **`{rule.qid}`** ({severity}{', locked' if rule.locked else ''}): {rule.description}"
        if rule.spec.get("hint"):
            line += f" _{rule.spec['hint']}_"
        out.append(line)
    engine = [f"`{rule_id}` is {severity}" for rule_id, severity in cfg.overrides.items()
              if rule_id.startswith("bondstone/")]
    out += ["", "The engine's own rules (`bondstone/...`) check structure: ids, fields, sections, links, code tags "
            "and stale views. `bondstone rules` lists them all."
            + (f" Changed in this repository: {'; '.join(engine)}." if engine else ""), ""]

    if cfg.views:
        out += ["## Generated files", "", "`bondstone gen` writes these. Do not edit them.", ""]
        out += [f"- `{view.output}` ({view.qid})" for view in cfg.views]
        out.append("")

    for comp in cfg.components:
        name = comp.data.get("instructions")
        if name and (comp.dir / name).is_file():
            out += [f"## Guidance from `{comp.id}`", "", (comp.dir / name).read_text(encoding="utf-8").strip(), ""]
    return "\n".join(out).rstrip() + "\n"


# bondstone: REQ-AGT-006
def skill(cfg: Config) -> str:
    """The same instructions as a Claude Code skill, which an agent loads when a task needs them."""
    folders = sorted({(tdef.path_template or "").split("{", 1)[0].rsplit("/", 1)[0] + "/"
                      for tdef in cfg.types.values() if tdef.path_template})
    where = ", ".join(folders) or "the documentation"
    description = (f"Rules for this repository's living documentation, enforced by bondstone. Use before creating "
                   f"or editing documents in {where}, before changing code that carries `bondstone:` comments, "
                   f"and before finishing a task, to run `bondstone check`.")
    head = yaml.safe_dump({"name": "bondstone", "description": description}, sort_keys=False, allow_unicode=True,
                          width=10_000)
    return f"---\n{head}---\n\n{instructions(cfg)}"


def write(cfg: Config, fmt: str, output: str | None) -> tuple[str, bool]:
    """Write the instructions where they belong: (path, whether the file changed)."""
    text = skill(cfg) if fmt == "skill" else instructions(cfg)
    relative = output or (SKILL_PATH if fmt == "skill" else MARKDOWN_PATH)
    target = cfg.root / relative
    if target.is_file() and target.read_text(encoding="utf-8") == text:
        return relative, False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    return relative, True
