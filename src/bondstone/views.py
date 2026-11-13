"""Generated Markdown views: tables, trees and matrices."""

from __future__ import annotations

import posixpath
from typing import Any

from .catalogue import diagnostic
from .config import Config, as_list
from .graph import GENERATED_MARK, Graph
from .model import PART_OF, Diagnostic, Node, View
from .select import matches, natural_key, outgoing_links, sources, targets

DEFAULT_COLUMNS = ["id", "title", "status"]
INCOMING = "<-"  # `<-name` names a link followed backwards, in table columns and matrix paths
MARK = "✓"


def _link(node: Node, output: str) -> str:
    """A Markdown link from the view to a node; items link to their heading."""
    target = posixpath.relpath(node.path, posixpath.dirname(output) or ".")
    anchor = ""
    if node.is_item:
        heading = f"{node.id}: {node.title}".lower().replace(" ", "-")
        anchor = "#" + "".join(c for c in heading if c.isalnum() or c in "-_")
    return f"[{node.id}]({target}{anchor})"


def _value(node: Node, column: str) -> Any:
    if column == "id":
        return node.id
    if column == "type":
        return node.type
    if column == "path":
        return node.path
    if column == "parent":
        return node.parent or ""
    return node.fields.get(column, "")


def is_link_column(cfg: Config, column: str) -> bool:
    """Whether a table column shows linked nodes: `<-name`, or the name of a link."""
    if column.startswith(INCOMING):
        return True
    return any(column in (link.qname, link.name) for link in cfg.links.values() if link.qname != PART_OF)


# bondstone: REQ-VIE-006
def _linked(cfg: Config, graph: Graph, node: Node, column: str, output: str) -> str:
    """The cell of a link column: the linked nodes as Markdown links.

    Outgoing links keep the order in which the document lists them; incoming ones are sorted
    by id. A target that does not exist is shown as plain text."""
    if column.startswith(INCOMING):
        found = {n.id: n for n in sources(cfg, graph, node, column[len(INCOMING):]) if n.id}
        return ", ".join(_link(found[key], output) for key in sorted(found, key=natural_key))
    cells: list[str] = []
    for link in outgoing_links(cfg, node.type, column):
        for ref in node.links.get(link.qname, []):
            target = graph.by_id.get(ref.target)
            cells.append(_link(target, output) if target is not None else _escape(ref.target))
    return ", ".join(dict.fromkeys(cells))


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _cell(cfg: Config, graph: Graph, node: Node, column: str, output: str) -> str:
    if column == "id":
        return _link(node, output)
    if is_link_column(cfg, column):
        return _linked(cfg, graph, node, column, output)
    value = _value(node, column)
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return _escape(value)


def _heading(cfg: Config, column: str) -> str:
    """A column's heading: a link reads as words, with an arrow when it is followed backwards."""
    if not is_link_column(cfg, column):
        return column.capitalize()
    name = column.removeprefix(INCOMING).rpartition(":")[2].replace("_", " ").capitalize()
    return f"← {name}" if column.startswith(INCOMING) else name


# bondstone: REQ-VIE-005
def _header(view: View) -> list[str]:
    lines = [f"{GENERATED_MARK} view={view.qid}; do not edit, run `bondstone gen` -->\n"
             f"# {view.spec.get('title', view.qid)}\n"]
    if view.spec.get("description"):
        lines.append(view.spec["description"] + "\n")
    return lines


def _selected(cfg: Config, graph: Graph, view: View, key: str = "select") -> list[Node]:
    nodes = [n for n in graph.nodes if n.id and matches(cfg, n, view.spec.get(key), view.context_pack)]
    keys = as_list(view.spec.get("sort")) or ["id"]
    return sorted(nodes, key=lambda n: ([natural_key(_value(n, key)) for key in keys], natural_key(n.id)))


# bondstone: REQ-VIE-001
def render_table(cfg: Config, graph: Graph, view: View) -> str:
    """One row per selected node."""
    columns = view.spec.get("columns") or DEFAULT_COLUMNS
    nodes = _selected(cfg, graph, view)
    lines = _header(view)
    if not nodes:
        lines.append("_No entries._")
        return "\n".join(lines) + "\n"
    lines.append("| " + " | ".join(_heading(cfg, column) for column in columns) + " |")
    lines.append("|" + "---|" * len(columns))
    for node in nodes:
        lines.append("| " + " | ".join(_cell(cfg, graph, node, column, view.output) for column in columns) + " |")
    return "\n".join(lines) + "\n"


def _children(cfg: Config, graph: Graph, node: Node, level: dict[str, str]) -> list[Node]:
    if "incoming" in level:
        found = sources(cfg, graph, node, level["incoming"])
    else:
        found = targets(cfg, graph, node, level["link"])
    unique = {child.id: child for child in found}
    return sorted(unique.values(), key=lambda child: natural_key(child.id))


# bondstone: REQ-VIE-002
def render_tree(cfg: Config, graph: Graph, view: View) -> str:
    """The selected nodes as roots, and below each the nodes reached level by level."""
    levels = view.spec.get("levels") or []
    lines = _header(view)
    roots = _selected(cfg, graph, view)
    if not roots:
        lines.append("_No entries._")

    def walk(node: Node, depth: int) -> None:
        status = f" _({node.status})_" if node.status else ""
        lines.append(f"{'  ' * depth}- {_link(node, view.output)} {node.title}{status}")
        if depth < len(levels):
            for child in _children(cfg, graph, node, levels[depth]):
                walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    return "\n".join(lines) + "\n"


def _step(cfg: Config, graph: Graph, node: Node, step: str) -> list[Node]:
    """The nodes one link away from `node`: along the link, or against it for `<-name`."""
    if step.startswith(INCOMING):
        return sources(cfg, graph, node, step[len(INCOMING):])
    return targets(cfg, graph, node, step)


# bondstone: REQ-VIE-007
def render_matrix(cfg: Config, graph: Graph, view: View) -> str:
    """Rows against columns, with a mark where the links under `via` lead from the row to the column.

    `via` is a path: the first link is followed from the row, the next from the nodes that
    reaches, and so on; the column is marked when the last step arrives at it."""
    rows = _selected(cfg, graph, view, "rows")
    cols = _selected(cfg, graph, view, "cols")
    lines = _header(view)
    if not rows or not cols:
        lines.append("_No entries._")
        return "\n".join(lines) + "\n"
    lines.append("| | " + " | ".join(_link(col, view.output) for col in cols) + " |")
    lines.append("|---|" + ":---:|" * len(cols))
    for row in rows:
        reached = {row.id: row}
        for step in view.spec.get("via") or []:
            reached = {n.id: n for node in reached.values() for n in _step(cfg, graph, node, step) if n.id}
        title = f" {_escape(row.title)}" if row.title else ""
        marks = " | ".join(MARK if col.id in reached else "" for col in cols)
        lines.append(f"| {_link(row, view.output)}{title} | {marks} |")
    return "\n".join(lines) + "\n"


RENDERERS = {"table": render_table, "tree": render_tree, "matrix": render_matrix}


def render(cfg: Config, graph: Graph, view: View) -> str:
    return RENDERERS[view.spec.get("render", "table")](cfg, graph, view)


# bondstone: REQ-VIE-003, REQ-VIE-004
def stale_views(cfg: Config, graph: Graph) -> list[tuple[View, str]]:
    """Views whose file is missing or differs from what would be generated, with the new content."""
    stale = []
    for view in cfg.views:
        content = render(cfg, graph, view)
        path = cfg.root / view.output
        try:
            current = path.read_text(encoding="utf-8") if path.is_file() else None
        except UnicodeDecodeError:
            current = None
        if current != content:
            stale.append((view, content))
    return stale


# bondstone: REQ-VIE-003
def generate(cfg: Config, graph: Graph) -> list[str]:
    """Write every stale view; returns the paths written."""
    written = []
    for view, content in stale_views(cfg, graph):
        path = cfg.root / view.output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(view.output)
    return written


# bondstone: REQ-VIE-004
def check_views(cfg: Config, graph: Graph) -> list[Diagnostic]:
    """`bondstone/view-stale` for every view that `bondstone gen` would rewrite."""
    return [
        diagnostic("bondstone/view-stale", f"generated view {view.qid} is out of date", view.output,
                   hint="Run `bondstone gen`.", fix={"command": ["bondstone", "gen"]})
        for view, _ in stale_views(cfg, graph)
    ]
