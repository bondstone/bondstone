"""Minimal, formatting-preserving edits to YAML frontmatter."""

from __future__ import annotations

import re

import yaml


def _frontmatter_bounds(lines: list[str]) -> tuple[int, int]:
    if not lines or lines[0].strip() != "---":
        raise ValueError("document has no frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() in ("---", "...")), None)
    if end is None:
        raise ValueError("frontmatter is not closed")
    return 1, end


# bondstone: REQ-SCF-004
def to_block_style(text: str) -> str:
    """Rewrite a flow-style frontmatter mapping (`{id: ..., status: ...}`) in block style.

    Block-style frontmatter is returned unchanged, so line-based edits keep its formatting."""
    lines = text.split("\n")
    start, end = _frontmatter_bounds(lines)
    if not any(lines[i].lstrip().startswith("{") for i in range(start, end)):
        return text
    data = yaml.safe_load("\n".join(lines[start:end])) or {}
    dumped = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False).rstrip("\n")
    return "\n".join([*lines[:start], dumped, *lines[end:]])


def _key_span(lines: list[str], key: str) -> tuple[int, int] | None:
    start, end = _frontmatter_bounds(lines)
    key_re = re.compile(rf"^{re.escape(key)}\s*:")
    for i in range(start, end):
        if key_re.match(lines[i]):
            j = i + 1
            while j < end and (lines[j].startswith((" ", "\t", "-")) or not lines[j].strip()):
                j += 1
            return i, j
    return None


# bondstone: REQ-SCF-004
def set_scalar(text: str, key: str, value: str) -> str:
    lines = to_block_style(text).split("\n")
    span = _key_span(lines, key)
    if span is None:
        _, end = _frontmatter_bounds(lines)
        lines.insert(end, f"{key}: {value}")
    else:
        i, j = span
        lines[i:j] = [f"{key}: {value}"]
    return "\n".join(lines)


# bondstone: REQ-SCF-004
def replace_id(text: str, key: str, old: str, new: str) -> tuple[str, bool]:
    """Replace the id `old` with `new` inside the value of frontmatter `key`."""
    lines = to_block_style(text).split("\n")
    span = _key_span(lines, key)
    if span is None:
        return text, False
    i, j = span
    pattern = re.compile(rf"(?<![\w-]){re.escape(old)}(?![\w-])")
    changed = False
    for k in range(i, j):
        head, sep, value = lines[k].partition(":") if k == i else ("", "", lines[k])
        replaced = pattern.sub(new, value)
        if replaced != value:
            changed = True
            lines[k] = f"{head}{sep}{replaced}" if k == i else replaced
    return "\n".join(lines), changed
