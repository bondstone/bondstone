"""Selectors and link-name resolution shared by rules and views."""

from __future__ import annotations

import re
from typing import Any

from .loader import Config, as_list, qualify
from .model import LinkDef, Node

KNOWN_TRAITS = {"lifecycle", "owned", "supersedable", "immutable", "code-traceable", "indexed"}
SELECTOR_KEYS = {"type", "role", "trait", "status", "where"}


def matches(cfg: Config, node: Node, selector: dict[str, Any] | None, context: str | None) -> bool:
    if not selector:
        return True
    if "type" in selector:
        types = {qualify(t, context) for t in as_list(selector["type"])}
        if node.type not in types:
            return False
    if "role" in selector:
        allowed: set[str] = set()
        for role in as_list(selector["role"]):
            allowed.update(cfg.roles.get(role, []))
        if node.type not in allowed:
            return False
    if "trait" in selector:
        tdef = cfg.types.get(node.type)
        if not tdef or not all(tdef.has_trait(t) for t in as_list(selector["trait"])):
            return False
    if "status" in selector:
        if node.status not in {str(s) for s in as_list(selector["status"])}:
            return False
    for key, expected in (selector.get("where") or {}).items():
        value = node.fields.get(key)
        if isinstance(expected, list):
            if value not in expected:
                return False
        elif value != expected:
            return False
    return True


def outgoing_links(cfg: Config, node_type: str, name: str) -> list[LinkDef]:
    link, _ = cfg.resolve_link_key(node_type, name)
    return [link] if link else []


def incoming_links(cfg: Config, node_type: str, name: str) -> list[LinkDef]:
    if ":" in name:
        return [l for l in cfg.links_to(node_type) if l.qname == name]
    return [l for l in cfg.links_to(node_type) if l.name == name]


def link_exists(cfg: Config, name: str) -> bool:
    return any(l.qname == name or l.name == name for l in cfg.links.values())


def validate_selector(cfg: Config, selector: Any, context: str | None, where: str) -> list[str]:
    problems: list[str] = []
    if selector is None:
        return problems
    if not isinstance(selector, dict):
        return [f"{where}: selector must be a mapping"]
    for key in selector:
        if key not in SELECTOR_KEYS:
            problems.append(f"{where}: unknown selector key '{key}'")
    for t in as_list(selector.get("type")):
        q = qualify(t, context)
        if q not in cfg.types:
            problems.append(f"{where}: unknown type '{q}'")
    for role in as_list(selector.get("role")):
        if role not in cfg.roles:
            problems.append(f"{where}: role '{role}' is not assigned by any bridge or the profile")
    for trait in as_list(selector.get("trait")):
        if trait not in KNOWN_TRAITS:
            problems.append(f"{where}: unknown trait '{trait}'")
    return problems


def natural_key(value: str | None) -> list[Any]:
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", value or "")]
