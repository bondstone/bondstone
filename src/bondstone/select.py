"""Selectors and link resolution shared by rules and views."""

from __future__ import annotations

import re
from typing import Any

from .config import Config, as_list, qualify
from .graph import Graph
from .model import PART_OF, LinkDef, Node


# bondstone: REQ-RUL-001, REQ-TRC-007
def matches(cfg: Config, node: Node, selector: dict[str, Any] | None, context: str | None) -> bool:
    """Whether a node matches a selector.

    Keys combine with AND and a list means any of. `context` is the pack whose rule or view
    the selector belongs to: type names are unqualified inside their own pack."""
    if not selector:
        return True
    if "type" in selector:
        if node.type not in {qualify(name, context) for name in as_list(selector["type"])}:
            return False
    if "role" in selector:
        allowed = {t for role in as_list(selector["role"]) for t in cfg.roles.get(role, [])}
        if node.type not in allowed:
            return False
    if "trait" in selector:
        tdef = cfg.types.get(node.type)
        if tdef is None or not all(tdef.has_trait(trait) for trait in as_list(selector["trait"])):
            return False
    if "status" in selector:
        if node.status not in {str(status) for status in as_list(selector["status"])}:
            return False
    if "covered" in selector and node.covered != bool(selector["covered"]):
        return False
    for key, expected in (selector.get("where") or {}).items():
        value = node.fields.get(key)
        if isinstance(expected, list):
            if value not in expected:
                return False
        elif value != expected:
            return False
    return True


def describe(selector: dict[str, Any] | None, word: str = "to") -> str:
    """A selector as it appears in messages: ` to type=adr:Decision status=[...]`."""
    if not selector:
        return ""
    return f" {word} " + " ".join(f"{key}={value}" for key, value in selector.items())


# --------------------------------------------------------------------------- links


def outgoing_links(cfg: Config, node_type: str, name: str) -> list[LinkDef]:
    """Links named `name` (plain or qualified) that may start at a type."""
    link, _ = cfg.resolve_link_key(node_type, name)
    return [link] if link else []


def incoming_links(cfg: Config, node_type: str, name: str) -> list[LinkDef]:
    """Links named `name` (plain or qualified) that may end at a type."""
    return [link for link in cfg.links_to(node_type) if name in (link.qname, link.name)]


def targets(cfg: Config, graph: Graph, node: Node, name: str) -> list[Node]:
    """Existing nodes that `node` points at through its link `name`, in written order."""
    found = []
    for link in outgoing_links(cfg, node.type, name):
        for ref in node.links.get(link.qname, []):
            target = graph.by_id.get(ref.target)
            if target is not None:
                found.append(target)
    return found


def sources(cfg: Config, graph: Graph, node: Node, name: str) -> list[Node]:
    """Nodes that point at `node` through a link `name`."""
    qnames = {link.qname for link in incoming_links(cfg, node.type, name)}
    return graph.sources(node.id, qnames)


def items(graph: Graph, node: Node) -> list[Node]:
    """The items of a document."""
    return graph.sources(node.id, {PART_OF})


# --------------------------------------------------------------------------- ordering


def natural_key(value: Any) -> list[Any]:
    """Sort key that orders `ADR-2` before `ADR-10`."""
    parts = re.split(r"(\d+)", "" if value is None else str(value))
    return [(1, int(part), "") if part.isdigit() else (0, 0, part) for part in parts]
