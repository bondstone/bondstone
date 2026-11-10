"""Generate agent instructions and rule documentation from the active profile."""

from __future__ import annotations

from .loader import Config, as_list
from .model import Rule

HEADER = "<!-- bondstone:generated agent instructions; run `bondstone agent` to refresh -->"


def describe_rule(rule: Rule) -> str:
    spec = rule.spec
    parts = [f"**`{rule.qid}`** ({rule.severity}{', locked' if rule.locked else ''})"]
    if rule.description:
        parts.append(f": {rule.description}")
    if spec.get("hint"):
        parts.append(f" — _{spec['hint']}_")
    return "".join(parts)


# bondstone: REQ-AGT-002
def explain_rule(cfg: Config, qid: str) -> str | None:
    rule = cfg.rule(qid)
    if rule is None:
        return None
    import yaml

    severity = cfg.overrides.get(qid, rule.severity)
    lines = [f"{rule.qid}  (from {rule.owner}, severity {severity}{', locked' if rule.locked else ''})"]
    if rule.description:
        lines.append(rule.description)
    lines.append("")
    lines.append(yaml.safe_dump({k: v for k, v in rule.spec.items() if k not in ("id", "description")},
                                sort_keys=False).rstrip())
    return "\n".join(lines)


# bondstone: REQ-AGT-001
def agent_instructions(cfg: Config) -> str:
    out = [HEADER, "# Documentation rules (bondstone)", ""]
    out.append(
        "This repository's living documentation is validated by `bondstone`. "
        "Before finishing any task:\n\n"
        "1. Create new documents with `bondstone new <Type> --title \"...\"` instead of by hand.\n"
        "2. Keep frontmatter links (ids, not paths) accurate. To replace a document, run\n"
        "   `bondstone supersede <ID> --title \"...\"` instead of editing it.\n"
        "3. Run `bondstone gen` to refresh generated views.\n"
        "4. Run `bondstone check --format json` (add `--base origin/main` on branches) and fix every error.\n"
        "5. Never weaken `.bondstone/profile.yaml` (overrides, waivers) to make a check pass; ask instead.\n"
    )
    comps = ", ".join(f"{c.id}@{c.version} ({c.kind})" for c in cfg.components)
    out.append(f"Active packs and bridges: {comps}\n")

    out.append("## Document types\n")
    for tdef in cfg.types.values():
        spec = tdef.spec
        out.append(f"### `{tdef.qname}`")
        if spec.get("description"):
            out.append(spec["description"])
        facts = []
        if spec.get("embedded"):
            facts.append("written as headings inside its parent document")
        if spec.get("paths"):
            facts.append("location: " + ", ".join(f"`{p}`" for p in as_list(spec["paths"])))
        if spec.get("id_pattern"):
            facts.append(f"id: `{spec['id_pattern']}`")
        if spec.get("required_fields"):
            facts.append("required fields: " + ", ".join(as_list(spec["required_fields"])))
        if spec.get("sections"):
            facts.append("required sections: " + ", ".join(as_list(spec["sections"])))
        lifecycle = tdef.traits.get("lifecycle")
        if lifecycle:
            facts.append("status: " + " | ".join(as_list(lifecycle.get("statuses"))))
            transitions = lifecycle.get("transitions") or {}
            if transitions:
                facts.append("transitions: " + "; ".join(
                    f"{a} → {', '.join(as_list(b))}" for a, b in transitions.items()))
        if "owned" in tdef.traits:
            facts.append("requires `owner`")
        if "immutable" in tdef.traits:
            when = ", ".join(as_list(tdef.traits["immutable"].get("when")))
            facts.append(f"immutable once {when}: supersede instead of editing")
        if "code-traceable" in tdef.traits:
            facts.append("reference it from code with a `bondstone: <id>` comment")
        links = cfg.links_from(tdef.qname)
        if links:
            facts.append("links: " + "; ".join(
                f"`{l.name}` → {', '.join(l.to_types)}"
                + (f" (min {l.min})" if l.min else "") + (f" (max {l.max})" if l.max is not None else "")
                for l in links))
        out.extend(f"- {f}" for f in facts)
        out.append("")

    if cfg.roles:
        out.append("## Roles\n")
        out.extend(f"- `{role}`: {', '.join(types)}" for role, types in cfg.roles.items())
        out.append("")

    out.append("## Rules\n")
    for rule in cfg.rules:
        if cfg.overrides.get(rule.qid) == "off":
            continue
        out.append("- " + describe_rule(rule))
    out.append("")

    for comp in cfg.components:
        file = comp.data.get("instructions")
        if file and (comp.dir / file).is_file():
            out.append(f"## Guidance from `{comp.id}`\n")
            out.append((comp.dir / file).read_text(encoding="utf-8").strip())
            out.append("")
    return "\n".join(out).rstrip() + "\n"
