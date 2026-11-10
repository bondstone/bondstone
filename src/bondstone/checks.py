"""All checks: structure, links, traits, rules, code tags, views, diffs, policy."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .graph import Graph, build_graph, glob_files, rel
from .loader import Config, as_list, qualify
from .model import ERROR, OFF, PART_OF, WARN, Diagnostic, Node, Rule
from .parser import ParsedDoc, parse_document
from .select import (
    KNOWN_TRAITS,
    incoming_links,
    link_exists,
    matches,
    outgoing_links,
    validate_selector,
)
from .views import render

TODO_RE = re.compile(r"<!--\s*todo\b", re.I)
CODE_TAG_RE = re.compile(r"\bbondstone:[ \t]+([A-Z][\w-]*(?:[ \t]*,[ \t]*[A-Z][\w-]*)*)")


# =========================================================================== entry point


def run_check(cfg: Config, base: str | None = None, graph: Graph | None = None) -> list[Diagnostic]:
    graph = graph or build_graph(cfg)
    diags: list[Diagnostic] = []
    diags += profile_problems(cfg)
    diags += graph.diagnostics
    diags += check_nodes(cfg, graph)
    diags += check_links(cfg, graph)
    diags += check_supersedable(cfg, graph)
    diags += evaluate_rules(cfg, graph)
    diags += check_code(cfg, graph)
    diags += check_views(cfg, graph)
    if base:
        diags += check_diff(cfg, graph, base)
    return apply_policy(cfg, diags)


def has_errors(diags: list[Diagnostic], fail_on: str = ERROR) -> bool:
    levels = {ERROR} if fail_on == ERROR else {ERROR, WARN}
    return any(d.severity in levels for d in diags)


# =========================================================================== profile


def profile_problems(cfg: Config) -> list[Diagnostic]:
    out = list(cfg.problems)

    def bad(msg: str, severity: str = ERROR) -> None:
        out.append(Diagnostic("bondstone/profile", severity, msg, path=".bondstone/profile.yaml"))

    for tdef in cfg.types.values():
        for trait in tdef.traits:
            if trait not in KNOWN_TRAITS:
                bad(f"type {tdef.qname}: unknown trait '{trait}'")
        items = tdef.spec.get("items")
        if items and qualify(items.get("type", ""), tdef.owner) not in cfg.types:
            bad(f"type {tdef.qname}: items type '{items.get('type')}' is not defined")
        template = tdef.spec.get("template")
        if template and not (tdef.component_dir / template).is_file():
            bad(f"type {tdef.qname}: template '{template}' not found")
        sup = tdef.traits.get("supersedable")
        if sup is not None:
            lq = qualify(sup.get("link", "supersedes"), tdef.owner)
            if lq not in cfg.links:
                bad(f"type {tdef.qname}: supersedable link '{lq}' is not defined")
    for link in cfg.links.values():
        for t in [*link.from_types, *link.to_types]:
            if t not in cfg.types:
                bad(f"link {link.qname}: unknown type '{t}'")
    for role, types in cfg.roles.items():
        for t in types:
            if t not in cfg.types:
                bad(f"role '{role}': unknown type '{t}'")
    for rule in cfg.rules:
        spec = rule.spec
        for msg in validate_selector(cfg, spec.get("when"), rule.context_pack, rule.qid):
            bad(msg)
        if "when" in spec and "on_change" in spec:
            bad(f"{rule.qid}: use either 'when' or 'on_change', not both")
        if not as_list(spec.get("require")):
            bad(f"{rule.qid}: rule has no 'require' clauses")
        for clause in as_list(spec.get("require")):
            for key in ("to", "from", "changed"):
                for msg in validate_selector(cfg, clause.get(key), rule.context_pack, rule.qid):
                    bad(msg)
            for key in ("link", "incoming"):
                name = clause.get(key)
                if name and not link_exists(cfg, name):
                    bad(f"{rule.qid}: unknown link '{name}'")
    for view in cfg.views:
        for msg in validate_selector(cfg, view.spec.get("select"), view.context_pack, view.qid):
            bad(msg)

    # packs that no bridge connects
    packs = [c.id for c in cfg.components if c.kind == "pack"]
    if len(packs) > 1:
        parent = {p: p for p in packs}

        def find(x: str) -> str:
            while parent[x] != x:
                x = parent[x]
            return x

        for comp in cfg.components:
            if comp.kind == "bridge":
                req = [p for p in (comp.data.get("requires") or {}) if p in parent]
                for a, b in zip(req, req[1:]):
                    parent[find(a)] = find(b)
        groups: dict[str, list[str]] = {}
        for p in packs:
            groups.setdefault(find(p), []).append(p)
        if len(groups) > 1:
            listing = "; ".join(", ".join(sorted(g)) for g in groups.values())
            out.append(Diagnostic("bondstone/unbridged-packs", WARN,
                                  f"packs form disconnected groups ({listing}); add a bridge to connect them",
                                  path=".bondstone/profile.yaml"))
    return out


# =========================================================================== nodes


def _schema_for(cfg: Config, type_qname: str) -> dict[str, Any]:
    tdef = cfg.types[type_qname]
    props = dict(tdef.spec.get("fields") or {})
    props.setdefault("title", {"type": "string", "minLength": 1})
    required = list(as_list(tdef.spec.get("required_fields")))
    traits = tdef.traits
    if "lifecycle" in traits:
        props["status"] = {"enum": list(traits["lifecycle"].get("statuses", []))}
        required.append("status")
    if "owned" in traits:
        props["owner"] = {"type": "string", "minLength": 1}
        required.append("owner")
    return {
        "type": "object",
        "properties": props,
        "required": sorted(set(required)),
        "additionalProperties": bool(tdef.spec.get("additional_fields", False)),
    }


def check_nodes(cfg: Config, graph: Graph) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    seen: dict[str, Node] = {}
    for node in graph.nodes:
        tdef = cfg.types[node.type]
        if not node.id:
            out.append(Diagnostic("bondstone/id-missing", ERROR, f"{node.type} document has no `id`",
                                  node.path, node.line,
                                  hint=f"Add `id:` matching {tdef.spec.get('id_pattern', 'the type id format')}."))
        else:
            pattern = tdef.spec.get("id_pattern")
            if pattern and not re.fullmatch(pattern, node.id):
                out.append(Diagnostic("bondstone/id-format", ERROR,
                                      f"id '{node.id}' does not match {pattern}",
                                      node.path, node.field_lines.get("id", node.line), node.id))
            if node.id in seen:
                other = seen[node.id]
                out.append(Diagnostic("bondstone/id-duplicate", ERROR,
                                      f"id '{node.id}' is already used in {other.path}:{other.line}",
                                      node.path, node.field_lines.get("id", node.line), node.id))
            else:
                seen[node.id] = node

        if node.parent is None:  # frontmatter documents only
            validator = Draft202012Validator(_schema_for(cfg, node.type), format_checker=FormatChecker())
            for err in sorted(validator.iter_errors(node.fields), key=lambda e: list(e.path)):
                out.append(_schema_diag(cfg, node, err))

        todo = TODO_RE.search(_mask_code(node.body)) if node.parent is None else None
        if todo:
            lifecycle = tdef.traits.get("lifecycle") or {}
            draft = node.status is not None and node.status == lifecycle.get("initial")
            todo_line = node.body_line + node.body[: todo.start()].count("\n")
            out.append(Diagnostic("bondstone/todo-left", WARN if draft else ERROR,
                                  "document still contains template placeholders (<!-- todo: ... -->)",
                                  node.path, todo_line, node.id,
                                  hint="Replace every `<!-- todo: ... -->` marker with real content."))

        present = node.heading_titles()
        for section in as_list(tdef.spec.get("sections")):
            if section not in present:
                out.append(Diagnostic("bondstone/section-missing", ERROR,
                                      f"{node.type} requires a '{section}' section",
                                      node.path, node.line, node.id,
                                      hint=f"Add a heading '## {section}'."))
    return out


def _mask_code(text: str) -> str:
    """Blank out fenced blocks and inline code spans, keeping offsets and newlines."""
    def blank(m: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"(?ms)^\s*(```|~~~).*?^\s*\1[^\n]*$", blank, text)
    return re.sub(r"(`+)(?!`).+?(?<!`)\1(?!`)", blank, text)


def _schema_diag(cfg: Config, node: Node, err: Any) -> Diagnostic:
    if err.validator == "required":
        missing = re.findall(r"'([^']+)' is a required property", err.message)
        name = missing[0] if missing else "?"
        return Diagnostic("bondstone/field-missing", ERROR, f"missing required field '{name}'",
                          node.path, 1, node.id)
    if err.validator == "additionalProperties":
        extras = [k for k in node.fields if k not in (err.schema.get("properties") or {})]
        links = sorted({l.name for l in cfg.links_from(node.type)})
        fields = sorted((err.schema.get("properties") or {}).keys())
        return Diagnostic("bondstone/field-unknown", ERROR,
                          f"unknown key(s) {', '.join(extras)} for {node.type}",
                          node.path, node.field_lines.get(extras[0]) if extras else 1, node.id,
                          hint=f"Fields: {', '.join(fields)}. Links: {', '.join(links) or 'none'}.")
    key = ".".join(str(p) for p in err.path) or "?"
    top = str(err.path[0]) if err.path else None
    return Diagnostic("bondstone/field-invalid", ERROR, f"field '{key}': {err.message}",
                      node.path, node.field_lines.get(top, 1) if top else 1, node.id)


# =========================================================================== links


def check_links(cfg: Config, graph: Graph) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for node in graph.nodes:
        for lq, refs in node.links.items():
            if lq == PART_OF:
                continue
            link = cfg.links[lq]
            for ref in refs:
                target = graph.by_id.get(ref.target)
                if target is None:
                    out.append(Diagnostic("bondstone/link-broken", ERROR,
                                          f"{link.name} -> '{ref.target}': no such document",
                                          node.path, ref.line, node.id))
                elif link.to_types and target.type not in link.to_types:
                    out.append(Diagnostic("bondstone/link-type", ERROR,
                                          f"{link.name} -> {ref.target} is a {target.type}; "
                                          f"expected {', '.join(link.to_types)}",
                                          node.path, ref.line, node.id))
                elif ref.target == node.id:
                    out.append(Diagnostic("bondstone/link-self", ERROR,
                                          f"{link.name} points to itself", node.path, ref.line, node.id))
        for link in cfg.links_from(node.type):
            count = len(node.links.get(link.qname, []))
            if count < link.min:
                out.append(Diagnostic("bondstone/link-min", ERROR,
                                      f"needs at least {link.min} '{link.name}' link(s) to "
                                      f"{', '.join(link.to_types)}; has {count}",
                                      node.path, node.line, node.id,
                                      hint=f"Add `{link.name}: [<id>]` to the frontmatter."))
            if link.max is not None and count > int(link.max):
                out.append(Diagnostic("bondstone/link-max", ERROR,
                                      f"at most {link.max} '{link.name}' link(s) allowed; has {count}",
                                      node.path, node.field_lines.get(link.name, node.line), node.id))
    return out


def check_supersedable(cfg: Config, graph: Graph) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for tdef in cfg.types.values():
        sup = tdef.traits.get("supersedable")
        if sup is None:
            continue
        lq = qualify(sup.get("link", "supersedes"), tdef.owner)
        has_lifecycle = tdef.has_trait("lifecycle")
        superseded_by: dict[str, list[Node]] = {}
        for node in (n for n in graph.nodes if n.type == tdef.qname):
            for ref in node.links.get(lq, []):
                superseded_by.setdefault(ref.target, []).append(node)
                target = graph.by_id.get(ref.target)
                if target and has_lifecycle and target.status != "superseded":
                    out.append(Diagnostic("bondstone/supersede-status", ERROR,
                                          f"{node.id} supersedes {target.id}, but {target.id} has status "
                                          f"'{target.status}'",
                                          target.path, target.field_lines.get("status", 1), target.id,
                                          hint=f"Set `status: superseded` in {target.path}."))
        for target_id, sources in superseded_by.items():
            if len(sources) > 1:
                target = graph.by_id.get(target_id)
                out.append(Diagnostic("bondstone/supersede-multiple", ERROR,
                                      f"{target_id} is superseded by several nodes: "
                                      f"{', '.join(s.id or '?' for s in sources)}",
                                      target.path if target else None, 1, target_id))
        for node in (n for n in graph.nodes if n.type == tdef.qname):
            if has_lifecycle and node.status == "superseded" and node.id not in superseded_by:
                out.append(Diagnostic("bondstone/supersede-orphan", WARN,
                                      f"{node.id} is superseded but nothing supersedes it",
                                      node.path, node.field_lines.get("status", 1), node.id))
            # cycles
            seen = {node.id}
            current = node
            while current is not None:
                refs = current.links.get(lq, [])
                if not refs:
                    break
                nxt = graph.by_id.get(refs[0].target)
                if nxt is None:
                    break
                if nxt.id in seen:
                    out.append(Diagnostic("bondstone/supersede-cycle", ERROR,
                                          f"supersede chain from {node.id} forms a cycle",
                                          node.path, 1, node.id))
                    break
                seen.add(nxt.id)
                current = nxt
    return out


# =========================================================================== rules


def evaluate_rules(cfg: Config, graph: Graph) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for rule in cfg.rules:
        if "on_change" in rule.spec:
            continue
        for node in graph.nodes:
            if not matches(cfg, node, rule.spec.get("when"), rule.context_pack):
                continue
            for clause in as_list(rule.spec.get("require")):
                failure = _eval_clause(cfg, graph, rule, node, clause)
                if failure:
                    out.append(_rule_diag(rule, failure, node))
    return out


def _rule_diag(rule: Rule, detail: str, node: Node | None) -> Diagnostic:
    message = rule.spec.get("message") or rule.description or rule.qid
    return Diagnostic(rule.qid, rule.severity, f"{message} ({detail})",
                      node.path if node else ".bondstone/profile.yaml",
                      node.line if node else None,
                      node.id if node else None, rule.spec.get("hint"))


def _eval_clause(cfg: Config, graph: Graph, rule: Rule, node: Node, clause: dict[str, Any]) -> str | None:
    ctx = rule.context_pack
    if "link" in clause:
        links = outgoing_links(cfg, node.type, clause["link"])
        targets = [graph.by_id[r.target] for l in links for r in node.links.get(l.qname, [])
                   if r.target in graph.by_id]
        if clause.get("all"):
            bad = [t.id for t in targets if not matches(cfg, t, clause.get("to"), ctx)]
            return f"'{clause['link']}' targets not allowed: {', '.join(bad)}" if bad else None
        good = [t for t in targets if matches(cfg, t, clause.get("to"), ctx)]
        need = int(clause.get("min", 1))
        if len(good) < need:
            return f"needs {need} '{clause['link']}' link(s){_sel_text(clause.get('to'))}, has {len(good)}"
        return None
    if "incoming" in clause:
        qnames = {l.qname for l in incoming_links(cfg, node.type, clause["incoming"])}
        sources = [src for lq, src in graph.incoming.get(node.id or "", []) if lq in qnames]
        good = [s for s in sources if matches(cfg, s, clause.get("from"), ctx)]
        need = int(clause.get("min", 1))
        if len(good) < need:
            return (f"needs {need} incoming '{clause['incoming']}' link(s)"
                    f"{_sel_text(clause.get('from'), 'from')}, has {len(good)}")
        return None
    if "field" in clause:
        value = node.fields.get(clause["field"])
        return None if value not in (None, "", []) else f"field '{clause['field']}' is empty"
    if "section" in clause:
        return None if clause["section"] in node.heading_titles() else f"missing section '{clause['section']}'"
    if "contains" in clause:
        return None if re.search(clause["contains"], node.body, re.M) else f"body must match /{clause['contains']}/"
    return f"unsupported clause {sorted(clause)}"


def _sel_text(sel: dict[str, Any] | None, word: str = "to") -> str:
    if not sel:
        return ""
    parts = [f"{k}={v}" for k, v in sel.items()]
    return f" {word} " + " ".join(parts)


# =========================================================================== code tags


def scan_tags(text: str) -> list[tuple[int, str]]:
    """(line, id) for every `bondstone: ID[, ID…]` tag in a text."""
    found = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in CODE_TAG_RE.finditer(line):
            found.extend((lineno, ref.strip()) for ref in m.group(1).split(","))
    return found


def check_code(cfg: Config, graph: Graph) -> list[Diagnostic]:
    settings = cfg.code_settings()
    include = as_list(settings.get("include"))
    if not include:
        return []
    exclude = as_list(settings.get("exclude"))
    excluded = {rel(cfg.root, p) for pat in exclude for p in glob_files(cfg.root, pat)}
    out: list[Diagnostic] = []
    covered: set[str] = set()
    for pattern in include:
        for file in sorted(glob_files(cfg.root, pattern)):
            path = rel(cfg.root, file)
            if path in excluded:
                continue
            try:
                text = file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, ref in scan_tags(text):
                node = graph.by_id.get(ref)
                if node is None:
                    out.append(Diagnostic("bondstone/code-ref-unknown", ERROR,
                                          f"code references unknown id '{ref}'", path, lineno))
                elif not cfg.types[node.type].has_trait("code-traceable"):
                    out.append(Diagnostic("bondstone/code-ref-not-traceable", ERROR,
                                          f"{ref} is {node.type}, a type that is not code-traceable",
                                          path, lineno, ref))
                else:
                    covered.add(ref)
    for node in graph.nodes:
        trait = cfg.types[node.type].traits.get("code-traceable")
        if trait is None or not node.id:
            continue
        coverage = trait.get("coverage", WARN)
        if coverage != OFF and node.id not in covered:
            out.append(Diagnostic("bondstone/code-coverage", coverage,
                                  f"{node.id} is not referenced from code",
                                  node.path, node.line, node.id,
                                  hint=f"Add a `bondstone: {node.id}` comment where it is implemented."))
    return out


# =========================================================================== views


def check_views(cfg: Config, graph: Graph) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for view in cfg.views:
        output = view.spec.get("output")
        if not output:
            continue
        path = cfg.root / output
        expected = render(cfg, graph, view)
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            out.append(Diagnostic("bondstone/view-stale", ERROR, f"generated view {view.qid} is out of date",
                                  output, None, hint="Run `bondstone gen`."))
    return out


# =========================================================================== diff


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


@dataclass
class Changes:
    files: set[str]          # changed, added or untracked paths (current names)
    renames: dict[str, str]  # new path -> old path
    deleted: set[str]


def changed_files(root: Path, base: str) -> Changes:
    out = _git(root, "diff", "--name-status", "-M", "--relative", base)
    files: set[str] = set()
    renames: dict[str, str] = {}
    deleted: set[str] = set()
    for line in out.splitlines():
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) == 3:
            renames[parts[2]] = parts[1]
            files.add(parts[2])
        elif status.startswith("D"):
            deleted.add(parts[1])
        elif len(parts) >= 2:
            files.add(parts[-1])
    files |= set(_git(root, "ls-files", "--others", "--exclude-standard").split())
    return Changes(files, renames, deleted)


def _base_version(cfg: Config, base: str, changes: Changes, node: Node) -> ParsedDoc | None:
    """The node's document at `base`, following renames and moved ids."""
    candidates = [node.path]
    if node.path in changes.renames:
        candidates.append(changes.renames[node.path])
    candidates += sorted(changes.deleted)
    for path in candidates:
        text = file_at(cfg.root, base, path)
        if text is None:
            continue
        doc = parse_document(text)
        if path in (node.path, changes.renames.get(node.path)) or (
                doc.frontmatter and str(doc.frontmatter.get("id")) == node.id):
            return doc
    return None


def file_at(root: Path, base: str, path: str) -> str | None:
    try:
        return _git(root, "show", f"{base}:./{path}")
    except RuntimeError:
        return None


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    out = ""
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
            continue
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
            continue
        out += {"*": "[^/]*", "?": "[^/]"}.get(c, re.escape(c))
        i += 1
    return re.compile(out + r"\Z")


def check_diff(cfg: Config, graph: Graph, base: str) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    try:
        changes = changed_files(cfg.root, base)
    except RuntimeError as exc:
        return [Diagnostic("bondstone/git", ERROR, f"cannot diff against '{base}': {exc}")]
    changed = changes.files

    for node in graph.nodes:
        if node.parent is not None or node.path not in changed:
            continue
        traits = cfg.types[node.type].traits
        old = _base_version(cfg, base, changes, node)
        if old is None or not old.frontmatter:
            lifecycle = traits.get("lifecycle")
            if lifecycle and node.status is not None:
                allowed = [str(s) for s in as_list(lifecycle.get("create_as"))] or \
                    [str(lifecycle.get("initial") or as_list(lifecycle.get("statuses"))[0])]
                if node.status not in allowed:
                    out.append(Diagnostic("bondstone/status-initial", ERROR,
                                          f"new {node.type} starts as '{node.status}'; "
                                          f"new documents must start as {', '.join(allowed)}",
                                          node.path, node.field_lines.get("status", 1), node.id,
                                          hint="Create it in the initial status and change the status in a "
                                               "later change, or override bondstone/status-initial."))
            continue
        old_status = old.frontmatter.get("status")
        old_status = str(old_status) if old_status is not None else None
        lifecycle = traits.get("lifecycle")
        if lifecycle and old_status and node.status and old_status != node.status:
            allowed = (lifecycle.get("transitions") or {}).get(old_status, [])
            if node.status not in allowed:
                out.append(Diagnostic("bondstone/status-transition", ERROR,
                                      f"status change {old_status} -> {node.status} is not allowed "
                                      f"(allowed: {', '.join(allowed) or 'none'})",
                                      node.path, node.field_lines.get("status", 1), node.id))
        immutable = traits.get("immutable")
        if immutable and old_status in {str(s) for s in as_list(immutable.get("when"))}:
            allow = set(as_list(immutable.get("allow_fields"))) | {"status"}
            new_fm = {k: v for k, v in node.raw_keys.items() if k not in allow}
            old_fm = {k: v for k, v in old.frontmatter.items() if k not in allow}
            if new_fm != old_fm or node.body.strip() != old.body.strip():
                out.append(Diagnostic("bondstone/immutable", ERROR,
                                      f"{node.id} was '{old_status}' and may not be edited "
                                      f"(only {', '.join(sorted(allow))} may change)",
                                      node.path, 1, node.id,
                                      hint="Create a new document that supersedes it instead."))

    for rule in cfg.rules:
        trigger = rule.spec.get("on_change")
        if not trigger:
            continue
        patterns = [glob_to_regex(p) for p in as_list(trigger.get("paths"))]
        triggering = sorted(f for f in changed if any(p.match(f) for p in patterns))
        if not triggering:
            continue
        changed_nodes = [n for n in graph.nodes if n.path in changed]
        for clause in as_list(rule.spec.get("require")):
            if "changed" not in clause:
                continue
            if clause.get("traced"):
                traced = _traced_documents(cfg, graph, base, triggering)
                wanted = {doc_id: files for doc_id, files in traced.items()
                          if matches(cfg, graph.by_id[doc_id], clause["changed"], rule.context_pack)}
                if wanted:
                    for doc_id, files in sorted(wanted.items()):
                        doc = graph.by_id[doc_id]
                        if doc.path not in changed:
                            out.append(_rule_diag(rule, f"{', '.join(sorted(files))} implements {doc_id}, "
                                                        f"which was not updated", doc))
                    continue
            good = [n for n in changed_nodes if matches(cfg, n, clause["changed"], rule.context_pack)]
            need = int(clause.get("min", 1))
            if len(good) < need:
                shown = ", ".join(triggering[:5]) + (" …" if len(triggering) > 5 else "")
                out.append(_rule_diag(rule, f"changed {shown}; needs {need} changed document(s)"
                                            f"{_sel_text(clause['changed'], 'matching')}", None))
    return out


def _traced_documents(cfg: Config, graph: Graph, base: str, files: list[str]) -> dict[str, set[str]]:
    """Top-level documents referenced by tags in `files`, now or at `base` -> referencing files."""
    traced: dict[str, set[str]] = {}
    for path in files:
        texts = [file_at(cfg.root, base, path)]
        current = cfg.root / path
        if current.is_file():
            try:
                texts.append(current.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                pass
        for text in filter(None, texts):
            for _, ref in scan_tags(text):
                node = graph.by_id.get(ref)
                while node is not None and node.parent is not None:
                    node = graph.by_id.get(node.parent)
                if node is not None and node.id:
                    traced.setdefault(node.id, set()).add(path)
    return traced


# =========================================================================== policy


def apply_policy(cfg: Config, diags: list[Diagnostic]) -> list[Diagnostic]:
    today = dt.date.today().isoformat()
    active_waivers = []
    extra: list[Diagnostic] = []
    for w in cfg.waivers:
        if not isinstance(w, dict) or not w.get("rule"):
            extra.append(Diagnostic("bondstone/waiver-invalid", ERROR, f"waiver needs a 'rule': {w}",
                                    ".bondstone/profile.yaml"))
            continue
        if not w.get("reason"):
            extra.append(Diagnostic("bondstone/waiver-invalid", ERROR,
                                    f"waiver for {w['rule']} has no 'reason'", ".bondstone/profile.yaml"))
            continue
        expires = w.get("expires")
        if expires and str(expires) < today:
            extra.append(Diagnostic("bondstone/waiver-expired", ERROR,
                                    f"waiver for {w['rule']} ({w.get('node', 'all nodes')}) expired on {expires}",
                                    ".bondstone/profile.yaml"))
            continue
        active_waivers.append({**w, "_used": False})

    result: list[Diagnostic] = []
    for d in diags:
        severity = cfg.overrides.get(d.rule, d.severity)
        rule = cfg.rule(d.rule)
        if rule and rule.locked and severity != d.severity:
            severity = d.severity
        if severity == OFF:
            continue
        d.severity = severity
        waived = False
        for w in active_waivers:
            if w["rule"] == d.rule and (not w.get("node") or w["node"] == d.node):
                w["_used"] = True
                waived = not (rule and rule.locked)
        if not waived:
            result.append(d)
    for w in active_waivers:
        if not w["_used"]:
            extra.append(Diagnostic("bondstone/waiver-unused", WARN,
                                    f"waiver for {w['rule']} ({w.get('node', 'all nodes')}) matches nothing",
                                    ".bondstone/profile.yaml"))
    result.extend(extra)
    result.sort(key=lambda d: (d.path or "", d.line or 0, d.rule))
    return result
