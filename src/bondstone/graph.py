"""Read documents and code into one graph: nodes, links, incoming index, code tags and regions."""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field

from .catalogue import diagnostic
from .config import RESERVED_KEYS, Config, as_list
from .model import PART_OF, CodeRegion, CodeTag, Diagnostic, LinkRef, Node
from .parse import ParsedDoc, find_items, parse_document

GENERATED_MARK = "<!-- bondstone:generated"

# An id in a tag starts with a capital letter, does not end with a hyphen and is complete:
# `REQ-...` and `<id>` in prose are not tags.
_TAG_ID = r"[A-Z](?:[\w-]*\w)?(?![\w-]|\.\w)"
TAG_RE = re.compile(rf"\bbondstone:[ \t]+({_TAG_ID}(?:[ \t]*,[ \t]*{_TAG_ID})*)")


@dataclass
class Graph:
    nodes: list[Node] = field(default_factory=list)
    by_id: dict[str, Node] = field(default_factory=dict)
    incoming: dict[str, list[tuple[str, Node]]] = field(default_factory=dict)  # target id -> (link, source)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    code_tags: list[CodeTag] = field(default_factory=list)
    code_regions: list[CodeRegion] = field(default_factory=list)

    def index(self) -> None:
        """Rebuild the id lookup and the incoming-link index from the nodes."""
        self.by_id = {}
        for node in self.nodes:
            if node.id and node.id not in self.by_id:
                self.by_id[node.id] = node
        self.incoming = {}
        for node in self.nodes:
            for link_qname, refs in node.links.items():
                for ref in refs:
                    self.incoming.setdefault(ref.target, []).append((link_qname, node))

    def sources(self, node_id: str | None, link_qnames: set[str]) -> list[Node]:
        """Nodes that link to `node_id` through one of the given links."""
        return [source for link, source in self.incoming.get(node_id or "", []) if link in link_qnames]

    def items_of(self, node: Node) -> list[Node]:
        return [n for n in self.nodes if n.is_item and n.path == node.path]


def glob_files(root: os.PathLike[str] | str, pattern: str) -> list[str]:
    """Files matching a glob, as sorted repository-relative paths with forward slashes."""
    found = glob.glob(pattern, root_dir=root, recursive=True)
    return sorted(path.replace(os.sep, "/") for path in found if os.path.isfile(os.path.join(root, path)))


# --------------------------------------------------------------------------- documents


def build_graph(cfg: Config) -> Graph:
    graph = Graph()
    typed: dict[str, list[str]] = {}  # path -> types whose path matches
    for qname, tdef in cfg.types.items():
        if tdef.path_glob:
            for path in glob_files(cfg.root, tdef.path_glob):
                typed.setdefault(path, []).append(qname)
    managed = {path for pattern in cfg.docs for path in glob_files(cfg.root, pattern)}
    generated = {view.output for view in cfg.views}

    for path in sorted(set(typed) | managed):
        if path in generated:
            continue
        try:
            text = (cfg.root / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            graph.diagnostics.append(diagnostic("bondstone/parse-error", "file is not valid UTF-8", path, 1))
            continue
        if text.lstrip().startswith(GENERATED_MARK):
            continue
        doc = parse_document(text)
        if doc.error:
            graph.diagnostics.append(diagnostic("bondstone/parse-error", doc.error, path, doc.error_line))
            continue
        qname = _document_type(cfg, graph, path, doc, typed.get(path, []))
        if qname is not None:
            _add_document(cfg, graph, path, qname, doc)

    graph.index()
    _scan_code(cfg, graph)
    return graph


def _document_type(cfg: Config, graph: Graph, path: str, doc: ParsedDoc, candidates: list[str]) -> str | None:
    """The type to load a document as, or None when it cannot be loaded.

    Every document declares its `type`, and the type's path must match where the file is."""

    def report(rule: str, message: str, line: int = 1, hint: str | None = None) -> None:
        graph.diagnostics.append(diagnostic(rule, message, path, line, hint=hint))

    if doc.frontmatter is None:
        if candidates:
            report("bondstone/frontmatter-missing",
                   f"expected a {candidates[0]} document with YAML frontmatter",
                   hint=f"Start the file with a '---' block that has `id` and `type: {candidates[0]}`.")
        else:
            report("bondstone/untyped-document", "file is under `docs` but at no type's path",
                   hint="Move it to a type's path, or narrow `docs` in the profile.")
        return None
    declared = doc.frontmatter.get("type")
    type_line = doc.field_lines.get("type", 1)
    if declared is None:
        if not candidates:
            report("bondstone/untyped-document", "file is under `docs` but at no type's path",
                   hint="Move it to a type's path, or narrow `docs` in the profile.")
            return None
        if len(candidates) > 1:
            report("bondstone/type-ambiguous",
                   f"path matches several types ({', '.join(candidates)}); add `type`")
            return None
        report("bondstone/type-missing", "document has no `type`",
               hint=f"Add `type: {candidates[0]}` to the frontmatter.")
        return candidates[0]  # still checked as the type its path implies
    declared = str(declared)
    tdef = cfg.types.get(declared)
    if tdef is None:
        suggestions = sorted(q for q in cfg.types if q.split(":", 1)[1] == declared and not cfg.types[q].embedded)
        hint = (f"Use the qualified name `{suggestions[0]}`." if len(suggestions) == 1 else
                f"Known types: {', '.join(sorted(q for q, t in cfg.types.items() if not t.embedded)) or 'none'}.")
        report("bondstone/unknown-type", f"unknown type '{declared}'", type_line, hint)
        return None
    if tdef.embedded:
        report("bondstone/type-mismatch",
               f"{declared} is an embedded type: its nodes are items inside other documents", type_line)
        return None
    if declared not in candidates:
        elsewhere = f"; this path matches {', '.join(candidates)}" if candidates else ""
        report("bondstone/type-mismatch",
               f"declared type {declared}, but {declared} documents live at {tdef.path_glob}{elsewhere}",
               type_line, "Move the file, or correct `type`.")
        return None
    return declared


def _add_document(cfg: Config, graph: Graph, path: str, qname: str, doc: ParsedDoc) -> None:
    frontmatter = doc.frontmatter or {}
    node = Node(
        id=str(frontmatter["id"]) if frontmatter.get("id") is not None else None,
        type=qname, path=path, line=1, fields={}, field_lines=doc.field_lines,
        body=doc.body, headings=doc.headings, body_line=doc.body_line,
    )
    for key, value in frontmatter.items():
        if key in RESERVED_KEYS:
            continue
        link, error = cfg.resolve_link_key(qname, key)
        if error:
            graph.diagnostics.append(diagnostic("bondstone/link-ambiguous", error, path,
                                                doc.field_lines.get(key), node.id))
        elif link:
            refs = [LinkRef(str(target), doc.field_lines.get(key)) for target in as_list(value)
                    if target is not None]
            node.links.setdefault(link.qname, []).extend(refs)
        else:
            node.fields[key] = value
    graph.nodes.append(node)
    _add_items(cfg, graph, node, doc)


def _add_items(cfg: Config, graph: Graph, parent: Node, doc: ParsedDoc) -> None:
    items = cfg.types[parent.type].items
    if items is None:
        return
    lifecycle = cfg.types[items.type].traits.get("lifecycle")
    scan = find_items(doc, items.level, items.heading, items.section)
    for heading in scan.malformed:
        graph.diagnostics.append(diagnostic(
            "bondstone/item-heading",
            f"level-{items.level} heading '{heading.title}' is not an item; "
            f"expected '{items.heading_template}'",
            parent.path, heading.line, parent.id))
    for parsed in scan.items:
        item = Node(
            id=parsed.id, type=items.type, path=parent.path, line=parsed.line,
            fields={"title": parsed.title}, field_lines={}, body=parsed.body, headings=parsed.headings,
            parent=parent.id, is_item=True, body_line=parsed.body_line,
        )
        if lifecycle is not None:
            # D9: an item without a `Status:` line takes the type's default status
            item.fields["status"] = parsed.status if parsed.status is not None else lifecycle.get("default")
            if parsed.status_line:
                item.field_lines["status"] = parsed.status_line
        if parent.id:
            item.links[PART_OF] = [LinkRef(parent.id, parsed.line)]
        graph.nodes.append(item)


# --------------------------------------------------------------------------- code


def scan_tags(text: str) -> list[tuple[int, str]]:
    """(line, id) for every `bondstone: ID` tag in a text; one tag may list several ids."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in TAG_RE.finditer(line):
            found.extend((number, ref.strip()) for ref in match.group(1).split(","))
    return found


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def tag_regions(text: str) -> list[tuple[str, int, int]]:
    """(id, first line, last line) of the code each tag annotates.

    Tags on consecutive lines form one block and share a region. The region starts at the
    block and covers the code below it. It ends before the next tag block at the same or a
    lower indentation, or before the first line that follows a blank line and is indented no
    deeper than the first code line. Tags deeper inside the code nest: they get their own
    region and do not end the outer one."""
    lines = text.splitlines()
    tags = scan_tags(text)
    tag_lines = sorted({line for line, _ in tags})
    block_of: dict[int, int] = {}  # tag line -> first line of its block
    for line in tag_lines:
        block_of[line] = block_of.get(line - 1, line)
    block_end = {start: max(l for l in tag_lines if block_of[l] == start) for start in set(block_of.values())}

    def blank(number: int) -> bool:
        return not lines[number - 1].strip()

    regions = []
    for line, ref in tags:
        start = block_of[line]
        first = block_end[start] + 1
        anchor = next((n for n in range(first, len(lines) + 1) if not blank(n) and n not in block_of), None)
        end = len(lines)
        if anchor is not None:
            level = _indent(lines[anchor - 1])
            for number in range(first, len(lines) + 1):
                if blank(number) or _indent(lines[number - 1]) > level:
                    continue
                next_block = number in block_end
                after_gap = number > anchor and blank(number - 1) and number not in block_of
                if next_block or after_gap:
                    end = number - 1
                    break
        while end > start and blank(end):
            end -= 1
        regions.append((ref, start, end))
    return regions


def code_files(cfg: Config) -> list[str]:
    excluded = {path for pattern in cfg.code_exclude for path in glob_files(cfg.root, pattern)}
    files: list[str] = []
    for pattern in cfg.code_include:
        for path in glob_files(cfg.root, pattern):
            if path not in excluded and path not in files:
                files.append(path)
    return files


def _scan_code(cfg: Config, graph: Graph) -> None:
    for path in code_files(cfg):
        try:
            text = (cfg.root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # not text: nothing to tag
        for line, ref in scan_tags(text):
            graph.code_tags.append(CodeTag(path, line, ref))
            node = graph.by_id.get(ref)
            if node is not None:
                node.covered = True
        for ref, start, end in tag_regions(text):
            graph.code_regions.append(CodeRegion(path, ref, start, end))
