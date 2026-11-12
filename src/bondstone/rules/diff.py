"""Checks that compare the working tree with a base commit (`check --base REF`).

Three things need history: lifecycles (what status a node had before), immutability (what a
document said before) and diff rules (which files changed). All of them compare with the merge
base of REF and HEAD, so commits added to REF after the branch left it do not count as changes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..catalogue import diagnostic
from ..config import Config, as_list
from ..git import ADDED, DELETED, KINDS, Change, Repository, Trailer
from ..graph import Graph, scan_tags, tag_regions
from ..model import IGNORE, PROFILE_PATH, Diagnostic, Node, Rule
from ..parse import ParsedDoc, find_items, parse_document
from ..select import describe, matches
from .node import rule_diagnostic

# `none (reason)` or `none [ID, ID] (reason)`
_EXEMPTION = re.compile(r"^none\s*(?:\[([^\]]*)\])?\s*\((.*\S.*)\)$", re.S)
_SHOWN_FILES = 5


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """A path glob as a regular expression: `*` stays inside a folder, `**` crosses folders."""
    out = ""
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out += "(?:.*/)?"
            index += 3
        elif pattern.startswith("**", index):
            out += ".*"
            index += 2
        else:
            char = pattern[index]
            out += {"*": "[^/]*", "?": "[^/]"}.get(char, re.escape(char))
            index += 1
    return re.compile(out + r"\Z")


# bondstone: REQ-DIF-007, REQ-DIF-013
def fired_by(cfg: Config, rule: Rule, changes: list[Change]) -> list[Change]:
    """The changes that set a diff rule off: the right kind, at a path the rule watches.

    A rule watches the globs under `paths`, or with `code: true` the files that the profile
    selects as code. A renamed file counts at its old and at its new path."""
    trigger = rule.spec["on_change"]
    kinds = set(trigger.get("kinds") or KINDS)
    if trigger.get("code"):
        include = [glob_to_regex(pattern) for pattern in cfg.code_include]
        exclude = [glob_to_regex(pattern) for pattern in cfg.code_exclude]

        def watched(path: str) -> bool:
            return any(p.match(path) for p in include) and not any(p.match(path) for p in exclude)
    else:
        patterns = [glob_to_regex(pattern) for pattern in as_list(trigger.get("paths"))]

        def watched(path: str) -> bool:
            return any(p.match(path) for p in patterns)
    return [change for change in changes
            if change.kind in kinds and any(watched(path) for path in (change.path, change.old_path) if path)]


def describe_trigger(cfg: Config, rule: Rule) -> str:
    """The files a diff rule watches, in words."""
    trigger = rule.spec["on_change"]
    if trigger.get("code"):
        globs = ", ".join(cfg.code_include) or "none yet: set `code.include` in the profile"
        return f"files that the profile selects as code ({globs})"
    return "files matching " + ", ".join(str(path) for path in trigger.get("paths") or [])


@dataclass
class ChangeSet:
    """What differs between the base commit and the working tree."""

    base: str
    changes: list[Change]
    present: dict[str, Change] = field(default_factory=dict)  # added and modified files, by path
    deleted: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.present = {c.path: c for c in self.changes if c.kind != DELETED}
        self.deleted = sorted(c.path for c in self.changes if c.kind == DELETED)


# bondstone: REQ-DIF-002, REQ-DIF-012
def check_changes(cfg: Config, graph: Graph, repo: Repository, base_ref: str,
                  exemptions: bool = True) -> list[Diagnostic]:
    """Lifecycle, immutability and diff-rule diagnostics for the changes since `base_ref`."""
    base = repo.merge_base(base_ref)
    changes = ChangeSet(base, repo.changes(base))
    out: list[Diagnostic] = []
    baseline = _baseline(cfg, repo, out)
    out += _check_history(cfg, graph, repo, changes, baseline)
    trailers = repo.trailers(changes.base) if exemptions else []
    out += _check_diff_rules(cfg, graph, repo, changes, trailers)
    return out


# --------------------------------------------------------------------------- previous versions


# bondstone: REQ-DIF-010
def _baseline(cfg: Config, repo: Repository, out: list[Diagnostic]) -> str | None:
    """The profile's baseline commit, when the clone has it."""
    if cfg.baseline is None:
        return None
    if repo.commit(cfg.baseline) is None:
        out.append(diagnostic(
            "bondstone/baseline-missing", f"baseline commit {cfg.baseline} is not available in this clone",
            PROFILE_PATH,
            hint=f"Fetch the full history (`git fetch --unshallow`) or the commit (`git fetch origin {cfg.baseline}`), "
                 "or record a new one with `bondstone baseline`."))
        return None
    return cfg.baseline


class _History:
    """Earlier versions of documents: at the base, or else at the baseline commit."""

    def __init__(self, repo: Repository, changes: ChangeSet, baseline: str | None):
        self.repo = repo
        self.changes = changes
        self.baseline = baseline
        self._deleted: dict[str, ParsedDoc] | None = None

    def _at(self, commit: str, path: str) -> ParsedDoc | None:
        text = self.repo.file_at(commit, path)
        if text is None:
            return None
        doc = parse_document(text)
        return doc if doc.frontmatter and not doc.error else None

    def _same_id(self, doc: ParsedDoc | None, node: Node) -> bool:
        return doc is not None and str((doc.frontmatter or {}).get("id")) == node.id

    # bondstone: REQ-DIF-003, REQ-DIF-010
    def previous(self, node: Node) -> ParsedDoc | None:
        """The document as it was before this change, or None when it is new.

        It is looked for at its path, at the path it was renamed from, among the deleted files
        (a move that git did not report as a rename), and last at the baseline commit."""
        change = self.changes.present[node.path]
        paths = [] if change.kind == ADDED else [node.path]
        if change.old_path:
            paths.append(change.old_path)
        for path in paths:
            doc = self._at(self.changes.base, path)
            if doc is not None:
                return doc
        if self._deleted is None:
            parsed = {path: self._at(self.changes.base, path) for path in self.changes.deleted}
            self._deleted = {path: doc for path, doc in parsed.items() if doc is not None}
        for doc in self._deleted.values():
            if self._same_id(doc, node):
                return doc
        if self.baseline:
            for path in [node.path, *([change.old_path] if change.old_path else [])]:
                doc = self._at(self.baseline, path)
                if self._same_id(doc, node):
                    return doc
        return None


# --------------------------------------------------------------------------- lifecycle and immutability


def _check_history(cfg: Config, graph: Graph, repo: Repository, changes: ChangeSet,
                   baseline: str | None) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    history = _History(repo, changes, baseline)
    items_by_path: dict[str, list[Node]] = {}
    for node in graph.nodes:
        if node.is_item:
            items_by_path.setdefault(node.path, []).append(node)
    for node in graph.nodes:
        if node.is_item or node.path not in changes.present:
            continue
        tdef = cfg.types[node.type]
        items = items_by_path.get(node.path, [])
        old = history.previous(node)
        if old is None:
            for new in [node, *items]:
                out += _initial(cfg, new)
            continue
        old_status = _text((old.frontmatter or {}).get("status"))
        out += _transition(cfg, node, old_status)
        out += _immutable(cfg, node, old, old_status)
        old_items = _item_statuses(cfg, node, old)
        for item in items:
            if item.id in old_items:
                out += _transition(cfg, item, old_items[item.id])
            else:
                out += _initial(cfg, item)
    return out


def _text(value: Any) -> str | None:
    return str(value) if value is not None else None


# bondstone: REQ-DIF-005
def _item_statuses(cfg: Config, parent: Node, old: ParsedDoc) -> dict[str, str | None]:
    """The status every item had in an earlier version of its document."""
    items = cfg.types[parent.type].items
    if items is None:
        return {}
    default = (cfg.types[items.type].traits.get("lifecycle") or {}).get("default")
    scan = find_items(old, items.level, items.heading, items.section)
    return {item.id: item.status if item.status is not None else _text(default) for item in scan.items}


# bondstone: REQ-DIF-004
def _initial(cfg: Config, node: Node) -> list[Diagnostic]:
    """A new node starts in its lifecycle's `initial` status, when the lifecycle declares one."""
    initial = (cfg.types[node.type].traits.get("lifecycle") or {}).get("initial")
    if initial is None or node.status is None or node.status == str(initial):
        return []
    return [diagnostic(
        "bondstone/status-initial",
        f"new {node.type} starts as '{node.status}'; it must start as '{initial}'",
        node.path, node.field_lines.get("status", node.line), node.id,
        hint="Create it in the initial status and change the status in a later change. "
             "For documents that existed before bondstone, record them with `bondstone baseline`.")]


# bondstone: REQ-DIF-005
def _transition(cfg: Config, node: Node, old_status: str | None) -> list[Diagnostic]:
    """A status change follows the lifecycle's `transitions`, when the lifecycle declares them."""
    transitions = (cfg.types[node.type].traits.get("lifecycle") or {}).get("transitions")
    if transitions is None or old_status is None or node.status is None or old_status == node.status:
        return []
    allowed = [str(status) for status in as_list(transitions.get(old_status))]
    if node.status in allowed:
        return []
    return [diagnostic(
        "bondstone/status-transition",
        f"status change {old_status} -> {node.status} is not allowed (allowed: {', '.join(allowed) or 'none'})",
        node.path, node.field_lines.get("status", node.line), node.id)]


# bondstone: REQ-DIF-006
def _immutable(cfg: Config, node: Node, old: ParsedDoc, old_status: str | None) -> list[Diagnostic]:
    """A document that was in an immutable status only changes in the fields its type allows."""
    traits = cfg.types[node.type].traits
    if "immutable" not in traits:
        return []
    trait = traits["immutable"]
    if "when" in trait and old_status not in {str(status) for status in as_list(trait["when"])}:
        return []
    allow = {str(key) for key in as_list(trait["allow"])} if "allow" in trait else {"status"}
    try:
        current = parse_document((cfg.root / node.path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return []
    before = {key: value for key, value in (old.frontmatter or {}).items() if key not in allow}
    after = {key: value for key, value in (current.frontmatter or {}).items() if key not in allow}
    if before == after and old.body.strip() == current.body.strip():
        return []
    was = f"was '{old_status}'" if old_status is not None else "is immutable"
    may = f"only {', '.join(sorted(allow))} may change" if allow else "nothing may change"
    return [diagnostic(
        "bondstone/immutable", f"{node.id} {was} and may not be edited ({may})", node.path, 1, node.id,
        hint="Create a new document that supersedes it instead.")]


# --------------------------------------------------------------------------- diff rules


# bondstone: REQ-DIF-007
def _check_diff_rules(cfg: Config, graph: Graph, repo: Repository, changes: ChangeSet,
                      trailers: list[Trailer]) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    rules = [rule for rule in cfg.rules
             if rule.kind == "diff" and cfg.severity(rule.qid, rule.severity) != IGNORE]
    out += _invalid_exemptions(rules, trailers)
    touched = {path for change in changes.changes for path in (change.path, change.old_path) if path}
    # bondstone: REQ-DIF-014
    changed_nodes = [node for node in graph.nodes
                     if node.path in changes.present or any(path in touched for path in node.companions)]
    for rule in rules:
        triggering = fired_by(cfg, rule, changes.changes)
        if not triggering:
            continue
        found = _evaluate(cfg, graph, repo, changes, rule, triggering, changed_nodes)
        out += [_exempt(rule, diag, trailers) for diag in found]
    return out


# bondstone: REQ-DIF-008
def _evaluate(cfg: Config, graph: Graph, repo: Repository, changes: ChangeSet, rule: Rule,
              triggering: list[Change], changed_nodes: list[Node]) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    names = [change.path for change in triggering]
    shown = ", ".join(names[:_SHOWN_FILES]) + (" …" if len(names) > _SHOWN_FILES else "")
    where = rule.source or PROFILE_PATH

    def general(detail: str) -> None:
        out.append(rule_diagnostic(rule, f"changed {shown}; {detail}", None, where))

    for clause in rule.spec.get("require") or []:
        if "any" in clause:
            failures = [_clause_failure(cfg, graph, rule, changed_nodes, alternative)
                        for alternative in clause["any"]]
            if all(failures):
                general("needs one of: " + "; or ".join(str(failure) for failure in failures))
            continue
        if clause.get("traced"):
            # bondstone: REQ-DIF-009
            traced = _traced_documents(cfg, graph, repo, changes, triggering)
            wanted = {doc_id: files for doc_id, files in traced.items()
                      if matches(cfg, graph.by_id[doc_id], clause["changed"], rule.context_pack)}
            if wanted:
                for doc_id, files in sorted(wanted.items()):
                    doc = graph.by_id[doc_id]
                    if doc.path not in changes.present:
                        out.append(rule_diagnostic(
                            rule, f"{', '.join(sorted(files))} implements {doc_id}, which was not updated", doc))
                continue
            if "min" not in clause:
                continue  # nothing traced and no minimum asked for: the clause holds
        failure = _clause_failure(cfg, graph, rule, changed_nodes, clause)
        if failure:
            general(failure)
    return out


# bondstone: REQ-DIF-008
def _clause_failure(cfg: Config, graph: Graph, rule: Rule, changed_nodes: list[Node],
                    clause: dict[str, Any]) -> str | None:
    """Why an `exists` or a `changed` clause does not hold, or None when it holds."""
    need = int(clause.get("min", 1))
    if "exists" in clause:
        found = [node for node in graph.nodes if matches(cfg, node, clause["exists"], rule.context_pack)]
        if len(found) < need:
            return f"needs {need} document(s){describe(clause['exists'], 'matching')}"
        return None
    if "changed" in clause:
        good = [node for node in changed_nodes if matches(cfg, node, clause["changed"], rule.context_pack)]
        if len(good) < need:
            return f"needs {need} changed document(s){describe(clause['changed'], 'matching')}"
        return None
    return f"unsupported clause {sorted(clause)} in a diff rule"


# --------------------------------------------------------------------------- traced regions


def _tags_touching(text: str, lines: frozenset[int] | None) -> set[str]:
    """Ids of the tags whose region contains one of `lines`; None means the whole file.

    A change to a tag line itself does not count: adding or removing a tag changes no behaviour."""
    tags = scan_tags(text)
    if lines is None:
        return {ref for _, ref in tags}
    code_lines = lines - {line for line, _ in tags}
    return {ref for ref, start, end in tag_regions(text) if any(start <= line <= end for line in code_lines)}


# bondstone: REQ-DIF-009
def traced_ids(cfg: Config, repo: Repository, changes: ChangeSet, change: Change) -> set[str]:
    """Ids of the tags whose code region one change touched.

    Regions come from the current file for added and changed lines, and from the file at the
    base for removed lines. A new or a deleted file touches every tag in it."""
    old_text = None if change.kind == ADDED else repo.file_at(changes.base, change.old_path or change.path)
    new_text = None
    if change.kind != DELETED:
        try:
            new_text = (cfg.root / change.path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            new_text = None
    if old_text is None or new_text is None:
        return _tags_touching(new_text or old_text or "", None)
    lines = repo.changed_lines(changes.base, change)
    return _tags_touching(new_text, lines.new) | _tags_touching(old_text, lines.old)


def document_of(graph: Graph, node_id: str) -> Node | None:
    """The document a node belongs to: itself, or the document of an item."""
    node = graph.by_id.get(node_id)
    while node is not None and node.parent is not None:
        node = graph.by_id.get(node.parent)
    return node


# bondstone: REQ-DIF-009
def _traced_documents(cfg: Config, graph: Graph, repo: Repository, changes: ChangeSet,
                      triggering: list[Change]) -> dict[str, set[str]]:
    """Documents tagged in the changed regions of the triggering files -> those files.

    A tag on an item counts for the item's document."""
    traced: dict[str, set[str]] = {}
    for change in triggering:
        for ref in traced_ids(cfg, repo, changes, change):
            document = document_of(graph, ref)
            if document is not None and document.id:
                traced.setdefault(document.id, set()).add(change.path)
    return traced


# --------------------------------------------------------------------------- exemptions


def _exempt_trailer(rule: Rule) -> str | None:
    name = (rule.spec.get("exempt") or {}).get("trailer")
    return str(name) if name else None


def _parse_exemption(value: str) -> tuple[list[str] | None, str] | None:
    """(node ids or None for every node, reason) of a trailer value; None when it is malformed."""
    match = _EXEMPTION.match(value.strip())
    if match is None:
        return None
    scope = None if match.group(1) is None else [part.strip() for part in match.group(1).split(",") if part.strip()]
    if scope == []:
        return None
    return scope, match.group(2).strip()


# bondstone: REQ-DIF-012
def _invalid_exemptions(rules: list[Rule], trailers: list[Trailer]) -> list[Diagnostic]:
    """Trailers that name an exemption but do not have the form `none (<reason>)`."""
    names = {name.lower(): name for name in map(_exempt_trailer, rules) if name}
    out = []
    for trailer in trailers:
        name = names.get(trailer.key.lower())
        if name is not None and _parse_exemption(trailer.value) is None:
            out.append(diagnostic(
                "bondstone/exemption-invalid",
                f"commit {trailer.commit[:7]}: trailer '{trailer.key}: {trailer.value}' is not an exemption",
                hint=f"Write `{name}: none (<reason>)`, or `{name}: none [ID, ...] (<reason>)` "
                     "to exempt only some nodes. Amend the commit, or add a commit with a valid trailer."))
    return out


# bondstone: REQ-DIF-011
def _exempt(rule: Rule, diag: Diagnostic, trailers: list[Trailer]) -> Diagnostic:
    """Mark a diagnostic as exempted when a commit in the range carries the rule's trailer.

    A trailer without a node list covers every diagnostic of the rule; with a list, only the
    diagnostics on those nodes. The policy step turns the mark into `bondstone/exemption-used`."""
    name = _exempt_trailer(rule)
    if name is None:
        return diag
    for trailer in trailers:
        if trailer.key.lower() != name.lower():
            continue
        parsed = _parse_exemption(trailer.value)
        if parsed is None:
            continue
        scope, reason = parsed
        if scope is None or diag.node in scope:
            diag.exempted_by = {"commit": trailer.commit, "trailer": trailer.key, "reason": reason}
            return diag
    return diag
