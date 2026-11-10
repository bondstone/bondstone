"""Generated Markdown views."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .graph import GENERATED_MARK, Graph
from .loader import Config, as_list
from .model import Node, View
from .select import incoming_links, matches, natural_key, outgoing_links


def _link(node: Node, output: str) -> str:
    target = os.path.relpath(node.path, os.path.dirname(output) or ".").replace(os.sep, "/")
    anchor = ""
    if node.parent:
        anchor = "#" + "".join(c for c in f"{node.id}: {node.title}".lower().replace(" ", "-")
                               if c.isalnum() or c in "-_")
    return f"[{node.id}]({target}{anchor})"


def _cell(node: Node, column: str, output: str) -> str:
    if column == "id":
        return _link(node, output)
    if column == "type":
        return node.type
    if column == "path":
        return node.path
    if column == "parent":
        return node.parent or ""
    value = node.fields.get(column, "")
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _header(view: View) -> str:
    title = view.spec.get("title", view.qid)
    return f"{GENERATED_MARK} view={view.qid}; do not edit, run `bondstone gen` -->\n# {title}\n"


# bondstone: REQ-VIE-001
def render_table(cfg: Config, graph: Graph, view: View) -> str:
    spec = view.spec
    output = spec["output"]
    columns = as_list(spec.get("columns")) or ["id", "title", "status"]
    nodes = [n for n in graph.nodes if n.id and matches(cfg, n, spec.get("select"), view.context_pack)]
    nodes.sort(key=lambda n: natural_key(n.id))
    lines = [_header(view)]
    if spec.get("description"):
        lines.append(spec["description"] + "\n")
    if not nodes:
        lines.append("_No entries._")
        return "\n".join(lines) + "\n"
    lines.append("| " + " | ".join(c.capitalize() for c in columns) + " |")
    lines.append("|" + "---|" * len(columns))
    for node in nodes:
        lines.append("| " + " | ".join(_cell(node, c, output) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def _children(cfg: Config, graph: Graph, node: Node, step: dict[str, Any]) -> list[Node]:
    result: list[Node] = []
    if "incoming" in step:
        qnames = {l.qname for l in incoming_links(cfg, node.type, step["incoming"])}
        result = [src for lq, src in graph.incoming.get(node.id or "", []) if lq in qnames]
    elif "link" in step:
        for link in outgoing_links(cfg, node.type, step["link"]):
            for ref in node.links.get(link.qname, []):
                target = graph.by_id.get(ref.target)
                if target:
                    result.append(target)
    seen: set[str] = set()
    unique = []
    for n in sorted(result, key=lambda n: natural_key(n.id)):
        if n.id not in seen:
            seen.add(n.id or "")
            unique.append(n)
    return unique


# bondstone: REQ-VIE-002
def render_tree(cfg: Config, graph: Graph, view: View) -> str:
    spec = view.spec
    output = spec["output"]
    levels = as_list(spec.get("levels"))
    roots = [n for n in graph.nodes if n.id and matches(cfg, n, spec.get("select"), view.context_pack)]
    roots.sort(key=lambda n: natural_key(n.id))
    lines = [_header(view)]
    if spec.get("description"):
        lines.append(spec["description"] + "\n")
    if not roots:
        lines.append("_No entries._")

    def walk(node: Node, depth: int) -> None:
        status = f" _({node.status})_" if node.status else ""
        lines.append(f"{'  ' * depth}- {_link(node, output)} {node.title}{status}")
        if depth < len(levels):
            for child in _children(cfg, graph, node, levels[depth]):
                walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    return "\n".join(lines) + "\n"


RENDERERS = {"table": render_table, "tree": render_tree}


def render(cfg: Config, graph: Graph, view: View) -> str:
    renderer = RENDERERS.get(view.spec.get("render", "table"))
    if renderer is None:
        raise ValueError(f"view {view.qid}: unknown renderer '{view.spec.get('render')}'")
    return renderer(cfg, graph, view)


# bondstone: REQ-VIE-004
def generate(cfg: Config, graph: Graph) -> list[str]:
    written = []
    for view in cfg.views:
        output = view.spec.get("output")
        if not output:
            continue
        content = render(cfg, graph, view)
        path: Path = cfg.root / output
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(output)
    return written
