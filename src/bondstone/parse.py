"""Markdown with YAML frontmatter: documents, headings and items, with line numbers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from .manifest import normalize
from .model import Heading

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
KEY_RE = re.compile(r"^([^\s#:\-\[{].*?)\s*:(?:\s|$)")  # a key may contain a colon: `adr:supersedes`
STATUS_RE = re.compile(r"^Status:[ \t]*(.*?)[ \t]*$")
INLINE_CODE_RE = re.compile(r"(`+)(?!`).+?(?<!`)\1(?!`)")
BOM = "﻿"


@dataclass
class ParsedDoc:
    frontmatter: dict[str, Any] | None  # None when the file has no frontmatter block
    field_lines: dict[str, int]  # top-level frontmatter key -> line
    body: str
    body_line: int  # line of the first body line
    headings: list[Heading] = field(default_factory=list)
    error: str | None = None
    error_line: int = 1


@dataclass
class ParsedItem:
    id: str
    title: str
    line: int  # line of the heading
    end_line: int  # last line that belongs to the item
    body: str
    body_line: int
    headings: list[Heading]  # headings inside the item
    status: str | None = None  # from a `Status:` line under the heading
    status_line: int | None = None


@dataclass
class ItemScan:
    items: list[ParsedItem] = field(default_factory=list)
    malformed: list[Heading] = field(default_factory=list)  # item-level headings that are not items


# --------------------------------------------------------------------------- documents


# bondstone: REQ-GRA-001
def parse_document(text: str) -> ParsedDoc:
    """Split a document into frontmatter and body.

    The frontmatter is a YAML mapping between a first line `---` and the next `---` or `...`
    line. Problems are reported in `error`, never raised."""
    lines = text.removeprefix(BOM).splitlines()
    if not lines or lines[0].rstrip() != "---":
        return ParsedDoc(None, {}, "\n".join(lines), 1, find_headings(lines, 1))
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() in ("---", "...")), None)
    if end is None:
        return ParsedDoc(None, {}, "", 1, error="frontmatter is not closed with '---'")
    source = "\n".join(lines[1:end])
    try:
        data = yaml.safe_load(source) if source.strip() else {}
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        problem = getattr(exc, "problem", None) or "cannot be parsed"
        return ParsedDoc(None, {}, "", 1, error=f"invalid frontmatter YAML: {problem}",
                         error_line=mark.line + 2 if mark else 1)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return ParsedDoc(None, {}, "", 1, error="frontmatter must be a mapping of keys to values", error_line=2)
    field_lines: dict[str, int] = {}
    for index in range(1, end):
        match = KEY_RE.match(lines[index])
        if match:
            field_lines.setdefault(match.group(1).strip().strip("'\""), index + 1)
    body_lines = lines[end + 1:]
    body_line = end + 2
    return ParsedDoc(normalize(data), field_lines, "\n".join(body_lines), body_line,
                     find_headings(body_lines, body_line))


# --------------------------------------------------------------------------- headings and code


def _code_flags(lines: list[str]) -> list[bool]:
    """For every line, whether it belongs to a fenced code block (fence lines included)."""
    flags: list[bool] = []
    fence: str | None = None  # the opening fence while inside a block
    for line in lines:
        match = FENCE_RE.match(line)
        if fence is None:
            if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
                fence = match.group(1)
                flags.append(True)
            else:
                flags.append(False)
            continue
        flags.append(True)
        if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) \
                and not match.group(2).strip():
            fence = None
    return flags


# bondstone: REQ-GRA-001
def find_headings(lines: list[str], first_line: int) -> list[Heading]:
    """ATX headings (`## Title`) outside fenced code blocks."""
    headings = []
    for offset, (line, in_code) in enumerate(zip(lines, _code_flags(lines))):
        if in_code:
            continue
        match = HEADING_RE.match(line)
        if match and match.group(2).strip("# \t"):
            headings.append(Heading(len(match.group(1)), match.group(2).strip(), first_line + offset))
    return headings


def mask_code(text: str) -> str:
    """Blank out fenced code blocks and inline code spans, keeping offsets and line breaks."""
    lines = text.split("\n")
    masked = [" " * len(line) if in_code else line for line, in_code in zip(lines, _code_flags(lines))]
    return INLINE_CODE_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), "\n".join(masked))


# --------------------------------------------------------------------------- items


def _inside_section(headings: list[Heading], index: int, section: str | None) -> bool:
    """Whether the heading at `index` sits directly under the section named `section`."""
    if section is None:
        return True
    level = headings[index].level
    for heading in reversed(headings[:index]):
        if heading.level < level:
            return heading.title.strip() == section
    return False


# bondstone: REQ-GRA-005, REQ-TRC-006
def find_items(doc: ParsedDoc, level: int, pattern: re.Pattern[str], section: str | None) -> ItemScan:
    """The items of a document: headings at `level` under `section` whose text matches `pattern`.

    An item runs to the next heading of its level or above. A `Status:` line as the first
    text under the heading sets the item's status."""
    scan = ItemScan()
    body_lines = doc.body.split("\n") if doc.body else []
    last_line = doc.body_line + len(body_lines) - 1
    headings = doc.headings
    for index, heading in enumerate(headings):
        if heading.level != level or not _inside_section(headings, index, section):
            continue
        match = pattern.match(heading.title)
        if not match:
            scan.malformed.append(heading)
            continue
        following = next((h.line for h in headings[index + 1:] if h.level <= level), None)
        end_line = following - 1 if following is not None else last_line
        start = heading.line - doc.body_line + 1  # index of the first line after the heading
        lines = body_lines[start:end_line - doc.body_line + 1]
        groups = match.groupdict()
        item = ParsedItem(
            id=groups["id"], title=(groups.get("title") or "").strip(), line=heading.line,
            end_line=end_line, body="\n".join(lines), body_line=heading.line + 1,
            headings=[h for h in headings if heading.line < h.line <= end_line],
        )
        for offset, line in enumerate(lines):
            if line.strip():
                status = STATUS_RE.match(line)
                if status:
                    item.status, item.status_line = status.group(1), heading.line + 1 + offset
                break
        scan.items.append(item)
    return scan
