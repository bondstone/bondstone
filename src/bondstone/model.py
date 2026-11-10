"""Core data structures shared by every other module."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- severities

ERROR = "error"
WARN = "warn"
INFO = "info"
IGNORE = "ignore"
SEVERITIES = (ERROR, WARN, INFO, IGNORE)
_RANK = {IGNORE: 0, INFO: 1, WARN: 2, ERROR: 3}


def rank(severity: str) -> int:
    """Order severities so they can be compared: ignore < info < warn < error."""
    return _RANK[severity]


# --------------------------------------------------------------------------- names

PROFILE_PATH = ".bondstone/profile.yaml"
PART_OF = "bondstone:part_of"  # implicit link from an item to its document
CONFIG_RULE = "bondstone/profile"  # configuration errors; never overridable (exit code 2)
TRAITS = ("lifecycle", "owned", "immutable", "supersedable", "code-traceable", "indexed")


class BondstoneError(Exception):
    """Base class for failures that stop a command."""


class EnvironmentProblem(BondstoneError):
    """The checker could not run here at all (exit code 3)."""


# --------------------------------------------------------------------------- diagnostics


@dataclass
class Diagnostic:
    rule: str
    severity: str
    message: str
    path: str | None = None
    line: int | None = None
    node: str | None = None
    hint: str | None = None
    fix: dict[str, Any] | None = None
    exempted_by: dict[str, str] | None = None  # the commit trailer that exempts a diff-rule violation

    def to_dict(self) -> dict[str, Any]:
        """JSON form: stable key order, absent values left out."""
        ordered = {
            "rule": self.rule,
            "severity": self.severity,
            "path": self.path,
            "line": self.line,
            "node": self.node,
            "message": self.message,
            "hint": self.hint,
            "fix": self.fix,
            "exempted_by": self.exempted_by,
        }
        return {key: value for key, value in ordered.items() if value is not None}


# --------------------------------------------------------------------------- configuration


@dataclass
class Component:
    """A resolved pack or bridge."""

    kind: str  # "pack" | "bridge"
    id: str
    version: str
    dir: Path
    manifest: str  # path of pack.yaml / bridge.yaml, as shown in diagnostics
    data: dict[str, Any]


@dataclass
class ItemsDef:
    """Where a document type keeps its items and what they look like."""

    type: str  # qualified name of the embedded type
    level: int  # heading level of an item
    heading: re.Pattern[str]  # matches the heading text; groups `id` and `title`
    heading_template: str
    section: str | None = None  # items are only read under this heading
    id_template: str | None = None


@dataclass
class TypeDef:
    qname: str  # "adr:Decision"
    owner: str  # pack id
    name: str
    spec: dict[str, Any]
    component_dir: Path
    embedded: bool = False
    id_template: str | None = None
    id_pattern: str | None = None  # explicit override of the derived pattern
    path_template: str | None = None
    path_glob: str | None = None  # derived from the path template
    items: ItemsDef | None = None

    @property
    def traits(self) -> dict[str, dict[str, Any]]:
        return {name: (value or {}) for name, value in (self.spec.get("traits") or {}).items()}

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
    qid: str  # "adr/alternatives-considered"
    owner: str  # component id or "profile"
    spec: dict[str, Any]
    severity: str  # the rule's default; overrides are applied by the policy step
    locked: bool = False
    context_pack: str | None = None  # resolves unqualified type names
    source: str | None = None  # manifest that declares the rule

    @property
    def description(self) -> str:
        return str(self.spec.get("description", ""))

    @property
    def kind(self) -> str:
        if "on_change" in self.spec:
            return "diff"
        if "for_each" in self.spec:
            return "existence"
        return "node"


@dataclass
class View:
    qid: str
    owner: str
    spec: dict[str, Any]
    context_pack: str | None = None

    @property
    def output(self) -> str:
        return str(self.spec["output"])


# --------------------------------------------------------------------------- graph


@dataclass
class LinkRef:
    target: str
    line: int | None


@dataclass
class Heading:
    level: int
    title: str
    line: int


@dataclass
class Node:
    id: str | None
    type: str
    path: str  # repository-relative, posix
    line: int
    fields: dict[str, Any]
    field_lines: dict[str, int]
    body: str
    headings: list[Heading]
    links: dict[str, list[LinkRef]] = field(default_factory=dict)
    parent: str | None = None  # id of the document an item belongs to
    is_item: bool = False
    body_line: int = 1
    covered: bool = False  # tagged in code

    @property
    def status(self) -> str | None:
        value = self.fields.get("status")
        return str(value) if value is not None else None

    @property
    def title(self) -> str:
        return str(self.fields.get("title", ""))

    def heading_titles(self) -> set[str]:
        return {heading.title.strip() for heading in self.headings}


@dataclass
class CodeTag:
    path: str
    line: int
    id: str


@dataclass
class CodeRegion:
    """The block of code a tag annotates, as inclusive line numbers."""

    path: str
    id: str
    start: int
    end: int
