"""Core data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ERROR = "error"
WARN = "warn"
OFF = "off"
SEVERITIES = (ERROR, WARN, OFF)

PART_OF = "bondstone:part_of"


class BondstoneError(Exception):
    """Configuration problem that prevents checking at all."""


@dataclass
class Diagnostic:
    rule: str
    severity: str
    message: str
    path: str | None = None
    line: int | None = None
    node: str | None = None
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def format(self) -> str:
        loc = self.path or "<profile>"
        if self.line:
            loc += f":{self.line}"
        text = f"{loc}: {self.severity} {self.rule}: {self.message}"
        if self.hint:
            text += f"\n    hint: {self.hint}"
        return text


@dataclass
class Component:
    """A loaded pack or bridge."""

    kind: str  # "pack" | "bridge"
    id: str
    version: str
    dir: Path
    data: dict[str, Any]


@dataclass
class TypeDef:
    qname: str  # "adr:Decision"
    owner: str  # pack id
    name: str
    spec: dict[str, Any]
    component_dir: Path

    @property
    def traits(self) -> dict[str, dict[str, Any]]:
        raw = self.spec.get("traits") or {}
        if isinstance(raw, list):
            return {t: {} for t in raw}
        return {k: (v or {}) for k, v in raw.items()}

    def has_trait(self, name: str) -> bool:
        return name in self.traits


@dataclass
class LinkDef:
    qname: str  # "adr:supersedes"
    owner: str
    name: str
    from_types: list[str]
    to_types: list[str]
    min: int = 0
    max: int | None = None
    description: str = ""


@dataclass
class Rule:
    qid: str
    owner: str
    spec: dict[str, Any]
    severity: str
    locked: bool = False
    context_pack: str | None = None  # for resolving unqualified type names

    @property
    def description(self) -> str:
        return self.spec.get("description", "")


@dataclass
class View:
    qid: str
    owner: str
    spec: dict[str, Any]
    context_pack: str | None = None


@dataclass
class LinkRef:
    target: str
    line: int | None


@dataclass
class Node:
    id: str | None
    type: str
    path: str  # repo-relative, posix
    line: int
    fields: dict[str, Any]
    field_lines: dict[str, int]
    body: str
    headings: list[tuple[int, str, int]]  # (level, title, line)
    links: dict[str, list[LinkRef]] = field(default_factory=dict)
    raw_keys: dict[str, Any] = field(default_factory=dict)
    parent: str | None = None
    body_line: int = 1

    @property
    def status(self) -> str | None:
        value = self.fields.get("status")
        return str(value) if value is not None else None

    @property
    def title(self) -> str:
        return str(self.fields.get("title", ""))

    def heading_titles(self) -> set[str]:
        return {h[1].strip() for h in self.headings}
