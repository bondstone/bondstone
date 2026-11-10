"""Engine rules: the `bondstone/...` checks on structure, links, traits and code tags."""

from __future__ import annotations

import re
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from ..catalogue import diagnostic
from ..config import Config, as_list, id_regex, qualify
from ..graph import Graph
from ..model import ERROR, IGNORE, PART_OF, WARN, Diagnostic, Node
from ..parse import mask_code

TODO_RE = re.compile(r"<!--\s*todo\b", re.I)
SUPERSEDED = "superseded"


def check_engine(cfg: Config, graph: Graph) -> list[Diagnostic]:
    return [
        *check_nodes(cfg, graph),
        *check_links(cfg, graph),
        *check_supersedable(cfg, graph),
        *check_code(cfg, graph),
    ]


# --------------------------------------------------------------------------- nodes


def check_nodes(cfg: Config, graph: Graph) -> list[Diagnostic]:
    """Ids, frontmatter fields, leftover placeholders and required sections."""
    out: list[Diagnostic] = []
    documents = {node.path: node for node in graph.nodes if not node.is_item}
    validators: dict[str, Draft202012Validator] = {}
    seen: dict[str, Node] = {}
    for node in graph.nodes:
        tdef = cfg.types[node.type]
        out += _check_id(cfg, node, documents.get(node.path), seen)

        if node.is_item:
            statuses = (tdef.traits.get("lifecycle") or {}).get("statuses")
            if statuses is not None and node.status not in statuses:
                out.append(diagnostic(
                    "bondstone/field-invalid",
                    f"status '{node.status}' is not one of {', '.join(statuses)}",
                    node.path, node.field_lines.get("status", node.line), node.id))
        else:
            if node.type not in validators:
                validators[node.type] = Draft202012Validator(cfg.schema_for(node.type),
                                                             format_checker=FormatChecker())
            errors = sorted(validators[node.type].iter_errors(node.fields),
                            key=lambda e: ([str(p) for p in e.path], e.message))
            out += [_schema_diagnostic(cfg, node, error) for error in errors]
            todo = TODO_RE.search(mask_code(node.body))
            if todo:
                initial = (tdef.traits.get("lifecycle") or {}).get("initial")
                draft = node.status is not None and node.status == initial
                out.append(diagnostic(
                    "bondstone/todo-left",
                    "document still contains template placeholders (<!-- todo: ... -->)",
                    node.path, node.body_line + node.body[:todo.start()].count("\n"), node.id,
                    hint="Replace every `<!-- todo: ... -->` marker with real content.",
                    severity=WARN if draft else ERROR))

        present = node.heading_titles()
        for section in tdef.spec.get("sections") or []:
            if section not in present:
                out.append(diagnostic(
                    "bondstone/section-missing", f"{node.type} requires a '{section}' section",
                    node.path, node.line, node.id, hint=f"Add a heading '## {section}'."))
    return out


def _check_id(cfg: Config, node: Node, document: Node | None, seen: dict[str, Node]) -> list[Diagnostic]:
    tdef = cfg.types[node.type]
    if node.is_item:
        items = cfg.types[document.type].items if document else None
        template = items.id_template if items else None
        pattern = id_regex(template, document.fields) if template else None
        values = document.fields if document else {}
    else:
        template = tdef.id_template
        pattern = tdef.id_pattern or (id_regex(template, node.fields) if template else None)
        values = node.fields
    line = node.line if node.is_item else node.field_lines.get("id", node.line)
    if not node.id:
        return [diagnostic("bondstone/id-missing", f"{node.type} document has no `id`", node.path, node.line,
                           hint=f"Add `id:` following the template '{template}'." if template else None)]
    out = []
    if pattern and not re.fullmatch(pattern, node.id):
        if tdef.id_pattern and not node.is_item:
            expected = tdef.id_pattern
        else:
            used = [name for name in re.findall(r"\{(\w+)", template) if name not in ("n", "slug")]
            known = [f"{name}: {values[name]}" for name in used if values.get(name) not in (None, "")]
            expected = f"the id template '{template}'" + (f" ({', '.join(known)})" if known else "")
        out.append(diagnostic("bondstone/id-format", f"id '{node.id}' does not match {expected}",
                              node.path, line, node.id))
    if node.id in seen:
        other = seen[node.id]
        out.append(diagnostic("bondstone/id-duplicate",
                              f"id '{node.id}' is already used in {other.path}:{other.line}",
                              node.path, line, node.id))
    else:
        seen[node.id] = node
    return out


def _schema_diagnostic(cfg: Config, node: Node, error: Any) -> Diagnostic:
    if error.validator == "required":
        found = re.match(r"'(.+)' is a required property", error.message)
        name = found.group(1) if found else "?"
        return diagnostic("bondstone/field-missing", f"missing required field '{name}'", node.path, 1, node.id)
    if error.validator == "additionalProperties":
        properties = error.schema.get("properties") or {}
        extras = [key for key in node.fields if key not in properties]
        links = sorted({link.name for link in cfg.links_from(node.type)})
        return diagnostic(
            "bondstone/field-unknown", f"unknown key(s) {', '.join(extras)} for {node.type}",
            node.path, node.field_lines.get(extras[0], 1) if extras else 1, node.id,
            hint=f"Fields: {', '.join(sorted(properties))}. Links: {', '.join(links) or 'none'}.")
    key = ".".join(str(part) for part in error.path) or "?"
    top = str(error.path[0]) if error.path else None
    return diagnostic("bondstone/field-invalid", f"field '{key}': {error.message}",
                      node.path, node.field_lines.get(top, 1) if top else 1, node.id)


# --------------------------------------------------------------------------- links


def check_links(cfg: Config, graph: Graph) -> list[Diagnostic]:
    """Every link points at an existing node of an allowed type, within its min and max."""
    out: list[Diagnostic] = []
    for node in graph.nodes:
        for link_qname, refs in node.links.items():
            if link_qname == PART_OF:
                continue
            link = cfg.links[link_qname]
            for ref in refs:
                target = graph.by_id.get(ref.target)
                if target is None:
                    out.append(diagnostic("bondstone/link-broken",
                                          f"{link.name} -> '{ref.target}': no such document",
                                          node.path, ref.line, node.id))
                elif link.to_types and target.type not in link.to_types:
                    out.append(diagnostic("bondstone/link-type",
                                          f"{link.name} -> {ref.target} is a {target.type}; "
                                          f"expected {', '.join(link.to_types)}",
                                          node.path, ref.line, node.id))
                elif ref.target == node.id:
                    out.append(diagnostic("bondstone/link-self", f"{link.name} points to itself",
                                          node.path, ref.line, node.id))
        for link in cfg.links_from(node.type):
            count = len(node.links.get(link.qname, []))
            if count < link.min:
                out.append(diagnostic(
                    "bondstone/link-min",
                    f"needs at least {link.min} '{link.name}' link(s) to {', '.join(link.to_types)}; has {count}",
                    node.path, node.line, node.id, hint=f"Add `{link.name}: [<id>]` to the frontmatter."))
            if link.max is not None and count > link.max:
                out.append(diagnostic(
                    "bondstone/link-max", f"at most {link.max} '{link.name}' link(s) allowed; has {count}",
                    node.path, node.field_lines.get(link.name, node.line), node.id))
    return out


# --------------------------------------------------------------------------- supersedable


def check_supersedable(cfg: Config, graph: Graph) -> list[Diagnostic]:
    """Supersession forms single chains, and a superseded node says so in its status."""
    out: list[Diagnostic] = []
    for tdef in cfg.types.values():
        options = tdef.traits.get("supersedable")
        if options is None:
            continue
        link = qualify(options.get("link", "supersedes"), tdef.owner)
        statuses = (tdef.traits.get("lifecycle") or {}).get("statuses") or []
        tracks_status = SUPERSEDED in statuses
        nodes = [node for node in graph.nodes if node.type == tdef.qname]
        superseded_by: dict[str, list[Node]] = {}
        for node in nodes:
            for ref in node.links.get(link, []):
                superseded_by.setdefault(ref.target, []).append(node)
                target = graph.by_id.get(ref.target)
                if target is not None and tracks_status and target.status != SUPERSEDED:
                    out.append(diagnostic(
                        "bondstone/supersede-status",
                        f"{node.id} supersedes {target.id}, but {target.id} has status '{target.status}'",
                        target.path, target.field_lines.get("status", 1), target.id,
                        hint=f"Set `status: {SUPERSEDED}` in {target.path}."))
        for target_id, sources in superseded_by.items():
            if len(sources) > 1:
                target = graph.by_id.get(target_id)
                out.append(diagnostic(
                    "bondstone/supersede-multiple",
                    f"{target_id} is superseded by several nodes: {', '.join(s.id or '?' for s in sources)}",
                    target.path if target else sources[0].path, 1, target_id))
        for node in nodes:
            if tracks_status and node.status == SUPERSEDED and node.id not in superseded_by:
                out.append(diagnostic("bondstone/supersede-orphan",
                                      f"{node.id} is superseded but nothing supersedes it",
                                      node.path, node.field_lines.get("status", 1), node.id))
            visited = {node.id}
            current: Node | None = node
            while current is not None:
                refs = current.links.get(link, [])
                current = graph.by_id.get(refs[0].target) if refs else None
                if current is not None and current.id in visited:
                    out.append(diagnostic("bondstone/supersede-cycle",
                                          f"supersede chain from {node.id} forms a cycle",
                                          node.path, 1, node.id))
                    break
                if current is not None:
                    visited.add(current.id)
    return out


# --------------------------------------------------------------------------- code tags


def check_code(cfg: Config, graph: Graph) -> list[Diagnostic]:
    """Tags point at code-traceable nodes, and nodes that need code are tagged (D9)."""
    if not cfg.code_include:
        return []
    out: list[Diagnostic] = []
    for tag in graph.code_tags:
        node = graph.by_id.get(tag.id)
        if node is None:
            out.append(diagnostic("bondstone/code-ref-unknown", f"code references unknown id '{tag.id}'",
                                  tag.path, tag.line))
            continue
        tracing = cfg.types[node.type].traits.get("code-traceable")
        if tracing is None:
            out.append(diagnostic("bondstone/code-ref-not-traceable",
                                  f"{tag.id} is {node.type}, a type that is not code-traceable",
                                  tag.path, tag.line, tag.id))
        elif node.status in as_list(tracing.get("retired")):
            out.append(diagnostic(
                "bondstone/tag-retired",
                f"code is tagged with {tag.id}, which has status '{node.status}'",
                tag.path, tag.line, tag.id, hint="Remove the tag, or the code if it is no longer needed."))
    for node in graph.nodes:
        tracing = cfg.types[node.type].traits.get("code-traceable")
        if tracing is None or not node.id or node.covered:
            continue
        coverage = tracing.get("coverage", WARN)
        needs_code = tracing.get("when") is None or node.status in tracing["when"]
        if coverage != IGNORE and needs_code:
            out.append(diagnostic(
                "bondstone/code-coverage", f"{node.id} is not referenced from code",
                node.path, node.line, node.id,
                hint=f"Add a `bondstone: {node.id}` comment where it is implemented.", severity=coverage))
    return out
