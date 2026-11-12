"""Export the graph: as JSON for other tools, and as a Mermaid diagram for people.

The JSON shape is described by `schemas/graph.schema.json` and versioned. Nodes and edges are
separate lists, so the exports of several repositories can be put together."""

from __future__ import annotations

import json
import re
from typing import Any

from .config import Config
from .graph import Graph
from .model import PART_OF, Node, Refused

GRAPH_VERSION = 1


def _selected(cfg: Config, graph: Graph, types: list[str] | None) -> list[Node]:
    """Nodes that have an id, limited to some types when asked."""
    nodes = [node for node in graph.nodes if node.id]
    if not types:
        return nodes
    wanted = set()
    for name in types:
        found = [qname for qname in cfg.types if name in (qname, qname.split(":", 1)[1])]
        if not found:
            raise Refused(f"unknown type '{name}' (known: {', '.join(sorted(cfg.types))})")
        wanted.update(found)
    return [node for node in nodes if node.type in wanted]


def _edges(nodes: list[Node]) -> list[tuple[str, str, str]]:
    return [(str(node.id), ref.target, link) for node in nodes
            for link, refs in node.links.items() if link != PART_OF for ref in refs]


# bondstone: REQ-AGT-007
def graph_json(cfg: Config, graph: Graph, types: list[str] | None = None) -> dict[str, Any]:
    """The graph as plain data. With `types`, only those nodes and the edges between them."""
    nodes = _selected(cfg, graph, types)
    ids = {node.id for node in nodes}
    out_nodes = []
    for node in nodes:
        entry: dict[str, Any] = {"id": node.id, "type": node.type, "path": node.path, "line": node.line,
                                 "title": node.title}
        if node.status is not None:
            entry["status"] = node.status
        if node.parent is not None:
            entry["parent"] = node.parent
        entry["covered"] = node.covered
        entry["fields"] = {key: value for key, value in node.fields.items() if key not in ("title", "status")}
        out_nodes.append(entry)
    edges = [{"from": source, "to": target, "link": link} for source, target, link in _edges(nodes)
             if not types or target in ids]
    return {
        "version": GRAPH_VERSION,
        "components": [{"kind": c.kind, "id": c.id, "version": c.version} for c in cfg.components],
        "roles": cfg.roles,
        "nodes": out_nodes,
        "edges": edges,
        "code": [{"id": region.id, "path": region.path, "start": region.start, "end": region.end}
                 for region in graph.code_regions if region.id in ids],
    }


def to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n"


def _mermaid_id(node_id: str, taken: dict[str, str]) -> str:
    name = re.sub(r"\W", "_", node_id)
    while name in taken.values():
        name += "_"
    taken[node_id] = name
    return name


def _label(text: str) -> str:
    return text.replace('"', "#quot;").replace("\n", " ")


# bondstone: REQ-AGT-007
def graph_mermaid(cfg: Config, graph: Graph, types: list[str] | None = None) -> str:
    """The graph as a Mermaid flowchart, grouped by type.

    Without `types` it shows documents and leaves items out, because a diagram with every
    requirement is too large to read."""
    nodes = _selected(cfg, graph, types)
    if not types:
        nodes = [node for node in nodes if not node.is_item]
    names: dict[str, str] = {}
    lines = ["flowchart LR"]
    for qname in dict.fromkeys(node.type for node in nodes):
        group = re.sub(r"\W", "_", qname)
        lines.append(f'  subgraph {group}["{_label(qname)}"]')
        for node in nodes:
            if node.type == qname:
                title = f"<br/>{_label(node.title)}" if node.title else ""
                lines.append(f'    {_mermaid_id(str(node.id), names)}["{_label(str(node.id))}{title}"]')
        lines.append("  end")
    for source, target, link in _edges(nodes):
        if target in names:
            name = cfg.links[link].name if link in cfg.links else link
            lines.append(f"  {names[source]} -->|{_label(name)}| {names[target]}")
    for node in nodes:
        if node.parent in names:
            lines.append(f"  {names[str(node.id)]} -.-> {names[node.parent]}")
    return "\n".join(lines) + "\n"
