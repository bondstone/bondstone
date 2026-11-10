"""Build the document graph from the repository."""

from __future__ import annotations

import glob
import re
from dataclasses import dataclass, field
from pathlib import Path

from .loader import Config, as_list, qualify
from .model import ERROR, PART_OF, Diagnostic, LinkRef, Node
from .parser import ParsedDoc, parse_document

GENERATED_MARK = "<!-- bondstone:generated"
_TAG_ID = r"[A-Z](?:[\w-]*\w)?(?![\w-]|\.\w)"  # complete id: no trailing hyphen, not followed by more id characters
CODE_TAG_RE = re.compile(rf"\bbondstone:[ \t]+({_TAG_ID}(?:[ \t]*,[ \t]*{_TAG_ID})*)")
RESERVED = {"id", "type"}


@dataclass
class Graph:
    nodes: list[Node] = field(default_factory=list)
    by_id: dict[str, Node] = field(default_factory=dict)
    incoming: dict[str, list[tuple[str, Node]]] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    code_refs: list[tuple[str, int, str]] = field(default_factory=list)  # (path, line, id)

    def add(self, node: Node) -> None:
        self.nodes.append(node)

    def index(self) -> None:
        self.by_id = {}
        for node in self.nodes:
            if node.id and node.id not in self.by_id:
                self.by_id[node.id] = node
        self.incoming = {}
        for node in self.nodes:
            for link_qname, refs in node.links.items():
                for ref in refs:
                    self.incoming.setdefault(ref.target, []).append((link_qname, node))


def glob_files(root: Path, pattern: str) -> list[Path]:
    return [Path(p) for p in glob.glob(str(root / pattern), recursive=True) if Path(p).is_file()]


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def view_outputs(cfg: Config) -> set[str]:
    return {v.spec["output"] for v in cfg.views if v.spec.get("output")}


# bondstone: REQ-GRA-001, REQ-VIE-004
def build_graph(cfg: Config) -> Graph:
    graph = Graph()
    root = cfg.root
    excluded = view_outputs(cfg)

    path_types: dict[str, list[str]] = {}
    for qname, tdef in cfg.types.items():
        for pattern in as_list(tdef.spec.get("paths")):
            for file in glob_files(root, pattern):
                path_types.setdefault(rel(root, file), []).append(qname)
    scanned: set[str] = set()
    for pattern in as_list(cfg.profile.get("scan")):
        for file in glob_files(root, pattern):
            scanned.add(rel(root, file))

    for path in sorted(set(path_types) | scanned):
        if path in excluded:
            continue
        text = (root / path).read_text(encoding="utf-8")
        if text.lstrip().startswith(GENERATED_MARK):
            continue
        doc = parse_document(text)
        candidates = path_types.get(path, [])
        if doc.error:
            # bondstone: ENG-003
            graph.diagnostics.append(Diagnostic("bondstone/parse-error", ERROR, doc.error, path, 1))
            continue
        if doc.frontmatter is None:
            if candidates:
                graph.diagnostics.append(
                    # bondstone: ENG-004
                    Diagnostic("bondstone/frontmatter-missing", ERROR,
                               f"expected a {candidates[0]} document with YAML frontmatter", path, 1,
                               hint="Start the file with a '---' frontmatter block; `bondstone new` scaffolds one.")
                )
            continue
        explicit = doc.frontmatter.get("type")
        if explicit:
            qname = str(explicit)
            if qname not in cfg.types:
                graph.diagnostics.append(
                    # bondstone: ENG-005
                    Diagnostic("bondstone/unknown-type", ERROR,
                               f"unknown type '{qname}' (known: {', '.join(sorted(cfg.types))})",
                               path, doc.field_lines.get("type", 1))
                )
                continue
            if candidates and qname not in candidates:
                graph.diagnostics.append(
                    # bondstone: ENG-006
                    Diagnostic("bondstone/type-mismatch", ERROR,
                               f"declared type {qname} but path matches {', '.join(candidates)}",
                               path, doc.field_lines.get("type", 1))
                )
                continue
        elif len(candidates) == 1:
            qname = candidates[0]
        elif len(candidates) > 1:
            graph.diagnostics.append(
                # bondstone: ENG-007
                Diagnostic("bondstone/type-ambiguous", ERROR,
                           f"path matches several types ({', '.join(candidates)}); add `type:`", path, 1)
            )
            continue
        else:
            continue  # scanned file without a declared type: not a bondstone document
        _add_document(cfg, graph, path, qname, doc)

    graph.index()
    _scan_code(cfg, graph)
    return graph


# bondstone: REQ-TRC-001
def scan_tags(text: str) -> list[tuple[int, str]]:
    """(line, id) for every bondstone tag (comma-separated ids) in a text."""
    found = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in CODE_TAG_RE.finditer(line):
            found.extend((lineno, ref.strip()) for ref in m.group(1).split(","))
    return found


def code_files(cfg: Config) -> list[str]:
    settings = cfg.code_settings()
    excluded = {rel(cfg.root, p) for pat in as_list(settings.get("exclude")) for p in glob_files(cfg.root, pat)}
    files: list[str] = []
    for pattern in as_list(settings.get("include")):
        for file in sorted(glob_files(cfg.root, pattern)):
            path = rel(cfg.root, file)
            if path not in excluded and path not in files:
                files.append(path)
    return files


# bondstone: REQ-TRC-001, REQ-RUL-007
def _scan_code(cfg: Config, graph: Graph) -> None:
    for path in code_files(cfg):
        try:
            text = (cfg.root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, ref in scan_tags(text):
            graph.code_refs.append((path, lineno, ref))
            node = graph.by_id.get(ref)
            if node is not None:
                node.covered = True


# bondstone: REQ-GRA-004
def _add_document(cfg: Config, graph: Graph, path: str, qname: str, doc: ParsedDoc) -> None:
    fm = doc.frontmatter or {}
    node = Node(
        id=str(fm["id"]) if fm.get("id") is not None else None,
        type=qname,
        path=path,
        line=1,
        fields={},
        field_lines=doc.field_lines,
        body=doc.body,
        headings=doc.headings,
        raw_keys=dict(fm),
        body_line=doc.body_line,
    )
    for key, value in fm.items():
        if key in RESERVED:
            continue
        link, error = cfg.resolve_link_key(qname, key)
        if error:
            graph.diagnostics.append(
                # bondstone: ENG-008
                Diagnostic("bondstone/link-ambiguous", ERROR, error, path, doc.field_lines.get(key), node.id)
            )
            continue
        if link:
            refs = [LinkRef(str(t), doc.field_lines.get(key)) for t in as_list(value) if t is not None]
            node.links.setdefault(link.qname, []).extend(refs)
        else:
            node.fields[key] = value
    graph.add(node)
    _add_items(cfg, graph, node, doc)


# bondstone: REQ-GRA-003
def _add_items(cfg: Config, graph: Graph, parent: Node, doc: ParsedDoc) -> None:
    tdef = cfg.types[parent.type]
    spec = tdef.spec.get("items")
    if not spec:
        return
    item_type = qualify(spec["type"], tdef.owner)
    level = int(spec.get("heading_level", 3))
    pattern = re.compile(spec.get("pattern", r"^(?P<id>[A-Z][A-Z0-9-]*\d)\s*:\s*(?P<title>.+)$"))
    body_lines = doc.body.splitlines()
    headings = doc.headings
    for idx, (hlevel, title, line) in enumerate(headings):
        if hlevel != level:
            continue
        m = pattern.match(title)
        if not m:
            if spec.get("strict", True) and _inside_section(headings, idx, spec.get("section")):
                graph.diagnostics.append(
                    # bondstone: ENG-009
                    Diagnostic("bondstone/item-heading", ERROR,
                               f"level-{level} heading '{title}' does not match item pattern {pattern.pattern}",
                               parent.path, line, parent.id)
                )
            continue
        end_line = next(
            (h[2] for h in headings[idx + 1 :] if h[0] <= level), doc.body_line + len(body_lines)
        )
        start = line - doc.body_line + 1
        stop = end_line - doc.body_line
        item_body = "\n".join(body_lines[start:stop])
        item_headings = [h for h in headings if line < h[2] < end_line]
        groups = m.groupdict()
        item = Node(
            id=groups.get("id"),
            type=item_type,
            path=parent.path,
            line=line,
            fields={"title": (groups.get("title") or "").strip()},
            field_lines={},
            body=item_body,
            headings=item_headings,
            parent=parent.id,
        )
        if parent.id:
            item.links[PART_OF] = [LinkRef(parent.id, line)]
        graph.add(item)


def _inside_section(headings: list[tuple[int, str, int]], idx: int, section: str | None) -> bool:
    if not section:
        return True
    level = headings[idx][0]
    for h in reversed(headings[:idx]):
        if h[0] < level:
            return h[1].strip() == section
    return False
