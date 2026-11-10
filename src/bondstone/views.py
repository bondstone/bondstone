"""Generated Markdown views: tables and trees."""

from __future__ import annotations

import posixpath
from typing import Any

from .catalogue import diagnostic
from .config import Config, as_list
from .graph import GENERATED_MARK, Graph
from .model import Diagnostic, Node, View
from .select import matches, natural_key, sources, targets

DEFAULT_COLUMNS = ["id", "title", "status"]


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


def _cell(node: Node, column: str, output: str) -> str:
    if column == "id":
        return _link(node, output)
    value = _value(node, column)
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _header(view: View) -> list[str]:
    lines = [f"{GENERATED_MARK} view={view.qid}; do not edit, run `bondstone gen` -->\n"
             f"# {view.spec.get('title', view.qid)}\n"]
    if view.spec.get("description"):
        lines.append(view.spec["description"] + "\n")
    return lines


def _selected(cfg: Config, graph: Graph, view: View) -> list[Node]:
    nodes = [n for n in graph.nodes if n.id and matches(cfg, n, view.spec.get("select"), view.context_pack)]
    keys = as_list(view.spec.get("sort")) or ["id"]
    return sorted(nodes, key=lambda n: ([natural_key(_value(n, key)) for key in keys], natural_key(n.id)))


def render_table(cfg: Config, graph: Graph, view: View) -> str:
    """One row per selected node."""
    columns = view.spec.get("columns") or DEFAULT_COLUMNS
    nodes = _selected(cfg, graph, view)
    lines = _header(view)
    if not nodes:
        lines.append("_No entries._")
        return "\n".join(lines) + "\n"
    lines.append("| " + " | ".join(column.capitalize() for column in columns) + " |")
    lines.append("|" + "---|" * len(columns))
    for node in nodes:
        lines.append("| " + " | ".join(_cell(node, column, view.output) for column in columns) + " |")
    return "\n".join(lines) + "\n"


def _children(cfg: Config, graph: Graph, node: Node, level: dict[str, str]) -> list[Node]:
    if "incoming" in level:
        found = sources(cfg, graph, node, level["incoming"])
    else:
        found = targets(cfg, graph, node, level["link"])
    unique = {child.id: child for child in found}
    return sorted(unique.values(), key=lambda child: natural_key(child.id))


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


RENDERERS = {"table": render_table, "tree": render_tree}


def render(cfg: Config, graph: Graph, view: View) -> str:
    return RENDERERS[view.spec.get("render", "table")](cfg, graph, view)


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


def generate(cfg: Config, graph: Graph) -> list[str]:
    """Write every stale view; returns the paths written."""
    written = []
    for view, content in stale_views(cfg, graph):
        path = cfg.root / view.output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(view.output)
    return written


def check_views(cfg: Config, graph: Graph) -> list[Diagnostic]:
    """`bondstone/view-stale` for every view that `bondstone gen` would rewrite."""
    return [
        diagnostic("bondstone/view-stale", f"generated view {view.qid} is out of date", view.output,
                   hint="Run `bondstone gen`.", fix={"command": ["bondstone", "gen"]})
        for view, _ in stale_views(cfg, graph)
    ]
