"""Markdown + YAML frontmatter parsing."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
KEY_RE = re.compile(r"^([^\s#:][^:]*?)\s*:")


@dataclass
class ParsedDoc:
    frontmatter: dict[str, Any] | None
    field_lines: dict[str, int]
    body: str
    body_line: int  # 1-based line where body starts
    headings: list[tuple[int, str, int]] = field(default_factory=list)
    error: str | None = None


def normalize(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def parse_document(text: str) -> ParsedDoc:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ParsedDoc(None, {}, text, 1, find_headings(lines, 1))
    end = next((i for i in range(1, len(lines)) if lines[i].strip() in ("---", "...")), None)
    if end is None:
        return ParsedDoc(None, {}, text, 1, [], error="frontmatter is not closed with '---'")
    fm_text = "\n".join(lines[1:end])
    try:
        data = yaml.safe_load(fm_text) if fm_text.strip() else {}
    except yaml.YAMLError as exc:
        return ParsedDoc(None, {}, text, 1, [], error=f"invalid frontmatter YAML: {exc}")
    if not isinstance(data, dict):
        return ParsedDoc(None, {}, text, 1, [], error="frontmatter must be a mapping")
    field_lines: dict[str, int] = {}
    for i in range(1, end):
        m = KEY_RE.match(lines[i])
        if m:
            field_lines.setdefault(m.group(1).strip().strip("'\""), i + 1)
    body_lines = lines[end + 1 :]
    body_line = end + 2
    return ParsedDoc(
        normalize(data),
        field_lines,
        "\n".join(body_lines),
        body_line,
        find_headings(body_lines, body_line),
    )


def find_headings(lines: list[str], first_line: int) -> list[tuple[int, str, int]]:
    headings = []
    in_fence = False
    for offset, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            headings.append((len(m.group(1)), m.group(2).strip(), first_line + offset))
    return headings


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "untitled"
