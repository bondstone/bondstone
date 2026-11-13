"""What to read before editing: the documents behind some code, and the rules that will fire.

`context --for PATH...` answers before a change is made, `context --base REF` for the changes
made so far. Both read the same graph and the same diff rules as `check`."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Config, as_list
from .edit import next_item_id
from .git import ADDED, DELETED, MODIFIED, Change, Repository
from .graph import Graph, code_files, scan_tags
from .model import IGNORE, PART_OF, Node, Refused
from .rules.diff import ChangeSet, document_of, fired_by, traced_ids, unchanged_targets
from .select import describe, matches


@dataclass
class Entry:
    """One node to read, and why."""

    node: Node
    reasons: list[str] = field(default_factory=list)
    note: str | None = None  # a warning, such as immutability
    changed: bool | None = None  # with --base: whether its file changed
    next_item_id: str | None = None  # the id for the next item added to this document

    def to_dict(self) -> dict[str, Any]:
        node = self.node
        out = {"id": node.id, "type": node.type, "path": node.path, "line": node.line, "title": node.title,
               "status": node.status, "reasons": self.reasons, "note": self.note, "changed": self.changed,
               "next_item_id": self.next_item_id}
        return {key: value for key, value in out.items() if value is not None}


@dataclass
class RuleNote:
    """One diff rule that these files trigger, and what it will ask for."""

    id: str
    severity: str
    description: str
    asks: list[str]  # one line per clause
    must_change: list[str]  # ids of the documents a traced clause wants updated
    hint: str | None = None
    exempt: str | None = None  # trailer name, when the rule can be exempted

    def to_dict(self) -> dict[str, Any]:
        out = {"id": self.id, "severity": self.severity, "description": self.description, "asks": self.asks,
               "must_change": self.must_change, "hint": self.hint, "exempt": self.exempt}
        return {key: value for key, value in out.items() if value is not None}


@dataclass
class Context:
    paths: list[str]
    entries: list[Entry] = field(default_factory=list)
    rules: list[RuleNote] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"paths": self.paths, "nodes": [entry.to_dict() for entry in self.entries],
                "rules": [rule.to_dict() for rule in self.rules]}


# --------------------------------------------------------------------------- collecting


def normalize(cfg: Config, given: str, cwd: Path | None = None) -> str:
    """A path as the graph knows it: relative to the repository root, with forward slashes."""
    cwd = cwd or Path.cwd()
    path = Path(given)
    candidates = [path] if path.is_absolute() else [cwd / path, cfg.root / path]
    for candidate in candidates:
        resolved = Path(os.path.normpath(candidate))
        try:
            relative = resolved.relative_to(cfg.root)
        except ValueError:
            continue
        if resolved.exists() or candidate is candidates[-1]:
            return relative.as_posix()
    raise Refused(f"'{given}' is outside the repository {cfg.root}")


def _expand(cfg: Config, graph: Graph, paths: list[str]) -> list[str]:
    """Folders replaced by the code files and documents in them."""
    known = sorted({*code_files(cfg), *(node.path for node in graph.nodes)})
    out: list[str] = []
    for path in paths:
        inside = [name for name in known if name.startswith(path.rstrip("/") + "/")] \
            if (cfg.root / path).is_dir() else [path]
        out += [name for name in inside if name not in out]
    return out


class _Collector:
    def __init__(self, cfg: Config, graph: Graph, changed: set[str] | None):
        self.cfg, self.graph, self.changed = cfg, graph, changed
        self.entries: dict[str, Entry] = {}

    def add(self, node: Node | None, reason: str) -> None:
        if node is None or not node.id:
            return
        entry = self.entries.get(node.id)
        if entry is None:
            entry = self.entries[node.id] = Entry(node, note=self._note(node))
            if not node.is_item:
                entry.next_item_id = next_item_id(self.cfg, self.graph, node)
            if self.changed is not None:
                entry.changed = node.path in self.changed
        if reason not in entry.reasons:
            entry.reasons.append(reason)

    def _note(self, node: Node) -> str | None:
        trait = self.cfg.types[node.type].traits.get("immutable")
        if node.is_item or trait is None:
            return None
        if "when" in trait and node.status not in {str(status) for status in as_list(trait["when"])}:
            return None
        state = f" in status '{node.status}'" if node.status else ""
        supersedable = "supersedable" in self.cfg.types[node.type].traits
        instead = f"; run `bondstone supersede {node.id} --title ...` instead of editing it" if supersedable else ""
        return f"immutable{state}{instead}"

    def neighbours(self, node: Node) -> None:
        """The nodes one link away from a document, in both directions."""
        for link_qname, refs in node.links.items():
            if link_qname == PART_OF:
                continue
            name = self.cfg.links[link_qname].name if link_qname in self.cfg.links else link_qname
            for ref in refs:
                self.add(self.graph.by_id.get(ref.target), f"{node.id} links to it ({name})")
        for link_qname, source in self.graph.incoming.get(node.id or "", []):
            if link_qname != PART_OF and not source.is_item:
                name = self.cfg.links[link_qname].name if link_qname in self.cfg.links else link_qname
                self.add(source, f"it links to {node.id} ({name})")


# bondstone: REQ-AGT-003
def _collect(cfg: Config, graph: Graph, paths: list[str], tags: dict[str, list[tuple[str, int | None]]],
             changed: set[str] | None = None) -> list[Entry]:
    """Entries for the documents among `paths`, the nodes tagged in them, and their neighbours."""
    collector = _Collector(cfg, graph, changed)
    documents: list[Node] = []
    by_path = {node.path: node for node in graph.nodes if not node.is_item}
    for path in paths:
        if path in by_path:
            collector.add(by_path[path], "the document itself")
            documents.append(by_path[path])
        for ref, line in tags.get(path, []):
            node = graph.by_id.get(ref)
            collector.add(node, f"tagged in {path}:{line}" if line else f"tagged in {path}")
            document = document_of(graph, ref)
            if node is not None and document is not None and document is not node:
                collector.add(document, f"document of {ref}")
            if document is not None and document not in documents:
                documents.append(document)
    for document in documents:
        collector.neighbours(document)
    return list(collector.entries.values())


# bondstone: REQ-AGT-004
def _rules(cfg: Config, graph: Graph, changes: list[Change], traced: dict[str, set[str]]) -> list[RuleNote]:
    """The diff rules these changes trigger; `traced` maps a path to the tag ids touched in it."""
    notes = []
    touched = {path for change in changes for path in (change.path, change.old_path) if path}
    changed_nodes = [node for node in graph.nodes
                     if node.path in touched or any(path in touched for path in node.companions)]
    for rule in cfg.rules:
        severity = cfg.severity(rule.qid, rule.severity)
        if rule.kind != "diff" or severity == IGNORE:
            continue
        triggering = fired_by(cfg, rule, changes)
        if not triggering:
            continue
        asks: list[str] = []
        must_change: list[str] = []
        for clause in rule.spec.get("require") or []:
            asks.append(describe_clause(clause))
            if "link_changed" in clause:
                for _, target in unchanged_targets(cfg, graph, rule, changed_nodes, clause):
                    document = document_of(graph, target.id) or target
                    if document.id and document.id not in must_change:
                        must_change.append(document.id)
            if clause.get("traced"):
                for change in triggering:
                    for ref in sorted(traced.get(change.path, ())):
                        document = document_of(graph, ref)
                        if (document is not None and document.id and document.id not in must_change
                                and matches(cfg, document, clause["changed"], rule.context_pack)):
                            must_change.append(document.id)
        exempt = (rule.spec.get("exempt") or {}).get("trailer")
        notes.append(RuleNote(rule.qid, severity, rule.description, asks, must_change, rule.spec.get("hint"),
                              str(exempt) if exempt else None))
    return notes


def describe_clause(clause: dict[str, Any]) -> str:
    """What one clause of a diff rule asks for, in words."""
    if "any" in clause:
        return "one of: " + "; or ".join(describe_clause(alternative) for alternative in clause["any"])
    if "exists" in clause:
        return f"{int(clause.get('min', 1))} document(s){describe(clause['exists'], 'matching')} exist"
    if "link_changed" in clause:
        who = describe(clause.get("from"), "matching")
        return f"every document that a changed document{who} names under `{clause['link_changed']}` changes too"
    selector = describe(clause.get("changed"), "matching")
    if clause.get("traced"):
        extra = f", and at least {clause['min']} such document(s) change" if "min" in clause else ""
        return f"every document{selector} that is tagged in the changed code changes too{extra}"
    return f"{int(clause.get('min', 1))} document(s){selector} change"


# --------------------------------------------------------------------------- the two questions


def context_for(cfg: Config, graph: Graph, paths: list[str]) -> Context:
    """Before editing `paths`: every tag in a file counts, because any line may change."""
    paths = _expand(cfg, graph, paths)
    tags: dict[str, list[tuple[str, int | None]]] = {}
    changes = []
    for path in paths:
        target = cfg.root / path
        changes.append(Change(path, MODIFIED if target.is_file() else ADDED))
        try:
            text = target.read_text(encoding="utf-8") if target.is_file() else ""
        except UnicodeDecodeError:
            text = ""
        tags[path] = [(ref, line) for line, ref in scan_tags(text)]
    traced = {path: {ref for ref, _ in found} for path, found in tags.items()}
    return Context(paths, _collect(cfg, graph, paths, tags), _rules(cfg, graph, changes, traced))


def context_since(cfg: Config, graph: Graph, repo: Repository, base_ref: str) -> Context:
    """For the changes since `base_ref`: only the tags whose code region changed count."""
    base = repo.merge_base(base_ref)
    changes = ChangeSet(base, repo.changes(base))
    traced = {change.path: traced_ids(cfg, repo, changes, change) for change in changes.changes}
    tags = {path: [(ref, None) for ref in sorted(refs)] for path, refs in traced.items()}
    paths = [change.path for change in changes.changes]
    present = [path for path in paths if path in changes.present]
    entries = _collect(cfg, graph, present + [p for p in paths if p not in present], tags, set(changes.present))
    return Context(paths, entries, _rules(cfg, graph, changes.changes, traced))


# --------------------------------------------------------------------------- text


def to_text(context: Context) -> str:
    lines: list[str] = []
    if not context.paths:
        return "Nothing changed.\n"
    shown = ", ".join(context.paths[:5]) + (" …" if len(context.paths) > 5 else "")
    if context.entries:
        lines.append(f"Read before editing {shown}:")
        for entry in context.entries:
            node = entry.node
            status = f" ({node.status})" if node.status else ""
            where = f"{node.path}:{node.line}" if node.is_item else node.path
            changed = {True: " [changed]", False: " [not changed]", None: ""}[entry.changed]
            lines.append(f"  {node.id}  {node.type}  {where}{changed}")
            lines.append(f"      {node.title}{status}: {'; '.join(entry.reasons)}")
            if entry.note:
                lines.append(f"      {entry.note}")
            if entry.next_item_id:
                lines.append(f"      next item id: {entry.next_item_id}")
    else:
        lines.append(f"No document is traced to {shown}.")
    lines.append("")
    if context.rules:
        lines.append("Rules that fire when these files change:")
        for rule in context.rules:
            lines.append(f"  {rule.severity} {rule.id}: {rule.description}")
            lines += [f"      asks that {ask}" for ask in rule.asks]
            if rule.must_change:
                lines.append(f"      must change: {', '.join(rule.must_change)}")
            if rule.hint:
                lines.append(f"      hint: {rule.hint}")
            if rule.exempt:
                lines.append(f"      a `{rule.exempt}: none (<reason>)` commit trailer exempts a change; "
                             "add one only when the user asks for it")
    else:
        lines.append("No diff rule watches these files.")
    return "\n".join(lines) + "\n"
