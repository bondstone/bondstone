"""Node rules (`when` + `require`) and existence rules (`for_each`)."""

from __future__ import annotations

import posixpath
import re
from typing import Any

import yaml

from ..config import Config, as_list, qualify
from ..graph import Graph, glob_files
from ..model import PROFILE_PATH, Diagnostic, Node, Rule
from ..select import describe, items, matches, sources, targets

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


# bondstone: REQ-RUL-002
def check_rules(cfg: Config, graph: Graph) -> list[Diagnostic]:
    """Evaluate every node and existence rule. Diff rules need a base commit and are skipped."""
    out: list[Diagnostic] = []
    for rule in cfg.rules:
        if rule.kind == "existence":
            out += _existence(cfg, graph, rule)
        elif rule.kind == "node":
            for node in graph.nodes:
                if not matches(cfg, node, rule.spec.get("when"), rule.context_pack):
                    continue
                for clause in rule.spec["require"]:
                    failure = clause_failure(cfg, graph, rule, node, clause)
                    if failure:
                        out.append(rule_diagnostic(rule, failure, node,
                                                   key=clause_key(cfg, graph, rule, node, clause)))
    return out


# bondstone: REQ-RUL-009
def rule_diagnostic(rule: Rule, detail: str, node: Node | None, path: str | None = None,
                    key: str | None = None) -> Diagnostic:
    """A violation of a declared rule; `{id}` in the hint and the fix stands for the node's id.

    `key` names the clause that failed, for the fingerprint of a known violation."""
    node_id = node.id if node else None

    def fill(text: str) -> str:
        return text.replace("{id}", node_id) if node_id else text

    hint = rule.spec.get("hint")
    fix = rule.spec.get("fix")
    return Diagnostic(
        rule.qid, rule.severity, f"{rule.description or rule.qid} ({detail})",
        path=node.path if node else (path or PROFILE_PATH), line=node.line if node else None,
        node=node_id, hint=fill(hint) if hint else None,
        fix={"command": [fill(part) for part in fix["command"]]} if fix else None, key=key,
    )


# --------------------------------------------------------------------------- clauses


# bondstone: REQ-RUL-002, REQ-TRC-007
def clause_failure(cfg: Config, graph: Graph, rule: Rule, node: Node, clause: dict[str, Any]) -> str | None:
    """Why a clause does not hold for a node, or None when it holds."""
    context = rule.context_pack
    if "link" in clause:
        found = targets(cfg, graph, node, clause["link"])
        if clause.get("all"):
            wrong = _wrong_targets(cfg, graph, rule, node, clause)
            return f"'{clause['link']}' targets not allowed: {', '.join(wrong)}" if wrong else None
        good = [t for t in found if matches(cfg, t, clause.get("to"), context)]
        need = int(clause.get("min", 1))
        if len(good) < need:
            return f"needs {need} '{clause['link']}' link(s){describe(clause.get('to'))}, has {len(good)}"
        return None
    if "incoming" in clause:
        good = [s for s in sources(cfg, graph, node, clause["incoming"])
                if matches(cfg, s, clause.get("from"), context)]
        need = int(clause.get("min", 1))
        if len(good) < need:
            return (f"needs {need} incoming '{clause['incoming']}' link(s)"
                    f"{describe(clause.get('from'), 'from')}, has {len(good)}")
        return None
    if "field" in clause:
        value = node.fields.get(clause["field"])
        return None if value not in (None, "", [], {}) else f"field '{clause['field']}' is empty"
    if "section" in clause:
        return None if clause["section"] in node.heading_titles() else f"missing section '{clause['section']}'"
    if "contains" in clause:
        return None if re.search(clause["contains"], node.body, re.M) else f"body must match /{clause['contains']}/"
    if "items" in clause:
        wanted = qualify(clause["items"]["type"], context)
        count = sum(1 for item in items(graph, node) if item.type == wanted)
        need = int(clause["items"].get("min", 1))
        return None if count >= need else f"needs {need} {wanted} item(s), has {count}"
    if "covered" in clause:
        if node.covered == clause["covered"]:
            return None
        return "is not tagged in code" if clause["covered"] else "is tagged in code"
    if "file_field" in clause:
        return _file_field(cfg, node, clause["file_field"])
    if "any" in clause:
        failures = [clause_failure(cfg, graph, rule, node, alternative) for alternative in clause["any"]]
        return "needs one of: " + "; or ".join(failures) if all(failures) else None
    return f"unsupported clause {sorted(clause)}"


def _wrong_targets(cfg: Config, graph: Graph, rule: Rule, node: Node, clause: dict[str, Any]) -> list[str]:
    """Ids of the targets of a `link ... all: true` clause that its `to` selector does not allow."""
    return [target.id or "?" for target in targets(cfg, graph, node, clause["link"])
            if not matches(cfg, target, clause.get("to"), rule.context_pack)]


# bondstone: REQ-KNV-002
def clause_key(cfg: Config, graph: Graph, rule: Rule, node: Node, clause: dict[str, Any]) -> str:
    """What names a failed clause in the fingerprint of a known violation.

    It says what the clause asks for and leaves out counts, so the key stays the same while
    the document changes elsewhere. For `link ... all: true` it is the targets that are not
    allowed: one more wrong target is a new violation."""
    if "link" in clause:
        if clause.get("all"):
            return ", ".join(_wrong_targets(cfg, graph, rule, node, clause))
        return str(clause["link"])
    if "incoming" in clause:
        return f"<-{clause['incoming']}"
    for kind in ("field", "section", "contains"):
        if kind in clause:
            return str(clause[kind])
    if "items" in clause:
        return qualify(clause["items"]["type"], rule.context_pack)
    if "covered" in clause:
        return "covered"
    if "file_field" in clause:
        return f"{clause['file_field']['path']}#{clause['file_field']['key']}"
    if "any" in clause:
        return " | ".join(clause_key(cfg, graph, rule, node, alternative) for alternative in clause["any"])
    return ""


def _render(template: str, values: dict[str, Any]) -> str | None:
    """Fill `{name}` placeholders; None when a value is missing."""
    missing = [name for name in _PLACEHOLDER.findall(template) if values.get(name) in (None, "")]
    if missing:
        return None
    return _PLACEHOLDER.sub(lambda match: str(values[match.group(1)]), template)


# bondstone: REQ-RUL-004
def _file_field(cfg: Config, node: Node, spec: dict[str, Any]) -> str | None:
    """A value in a YAML or JSON file equals a field of the node (`equals`) or a literal (`value`)."""
    values = {**node.fields, "id": node.id, "dir": posixpath.dirname(node.path)}
    rendered = _render(spec["path"], values)
    if rendered is None:
        return f"cannot build the path '{spec['path']}': a field is missing"
    relative = posixpath.normpath(rendered)
    target = cfg.root / relative
    if relative.startswith("..") or not target.is_file():
        return f"{relative} does not exist"
    try:
        data: Any = yaml.safe_load(target.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        return f"{relative} is not valid YAML or JSON ({exc.__class__.__name__})"
    for part in spec["key"].split("."):
        if not isinstance(data, dict) or part not in data:
            return f"{relative} has no '{spec['key']}'"
        data = data[part]
    if "equals" in spec:
        expected, what = node.fields.get(spec["equals"]), f"field '{spec['equals']}'"
    else:
        expected, what = spec.get("value"), "the expected value"
    if str(data) != str(expected):
        return f"{relative} {spec['key']} is '{data}', {what} is '{expected}'"
    return None


# --------------------------------------------------------------------------- existence rules


# bondstone: REQ-RUL-003
def _existence(cfg: Config, graph: Graph, rule: Rule) -> list[Diagnostic]:
    """Every file matching `for_each.glob` has a document at `for_each.document`."""
    spec = rule.spec["for_each"]
    types = {qualify(name, rule.context_pack) for name in as_list(spec.get("type"))}
    documents = {(node.path, node.type) for node in graph.nodes if not node.is_item}
    out = []
    for path in glob_files(cfg.root, spec["glob"]):
        name = posixpath.basename(path)
        values = {"dir": posixpath.dirname(path), "name": name.rsplit(".", 1)[0] if "." in name else name,
                  "path": path}
        expected = posixpath.normpath(_render(spec["document"], values) or spec["document"])
        if not any(p == expected and (not types or t in types) for p, t in documents):
            kind = " or ".join(sorted(types)) if types else "document"
            out.append(rule_diagnostic(rule, f"{path} has no {kind} at {expected}", None, path, key=expected))
    return out
