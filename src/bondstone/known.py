"""Known violations: the problems a repository had when it adopted a rule (`.bondstone/known.json`).

`bondstone baseline --known` records every current violation as a fingerprint of the rule, the
node and a key that names the problem. A violation that matches an entry is reported as info,
so only new violations fail. Entries are never added by anything else, and an entry that
matches nothing is reported until it is pruned: the file can only shrink."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .manifest import validate
from .model import Diagnostic

KNOWN_PATH = ".bondstone/known.json"
FORMAT = 1


# bondstone: REQ-KNV-002
@dataclass(frozen=True, order=True)
class Entry:
    """The fingerprint of one violation. It has no line number, so edits elsewhere do not break it."""

    rule: str
    node: str = ""  # the node's id; empty for a violation that is about a file
    path: str = ""  # the file, when there is no node
    key: str = ""  # the specific problem: the missing section, the broken link's target

    def to_dict(self) -> dict[str, str]:
        ordered = {"rule": self.rule, "node": self.node, "path": self.path, "key": self.key}
        return {name: value for name, value in ordered.items() if value}

    def __str__(self) -> str:
        subject = self.node or self.path or "the repository"
        return f"{self.rule} on {subject}" + (f" ({self.key})" if self.key else "")


# bondstone: REQ-KNV-002
def fingerprint(diag: Diagnostic) -> Entry:
    """What identifies a diagnostic across edits: its rule, its node or else its file, and its key."""
    if diag.node:
        return Entry(diag.rule, node=diag.node, key=diag.key or "")
    return Entry(diag.rule, path=diag.path or "", key=diag.key or "")


@dataclass
class Known:
    """The contents of `known.json`."""

    entries: list[Entry] = field(default_factory=list)
    created: str | None = None
    lines: dict[Entry, int] = field(default_factory=dict)  # where each entry is written, when it is on one line

    def __bool__(self) -> bool:
        return bool(self.entries)


def _line(entry: Entry) -> str:
    return json.dumps(entry.to_dict(), ensure_ascii=False)


# bondstone: REQ-KNV-008
def parse(text: str) -> tuple[Known, list[str]]:
    """Read the file's text; returns what it holds and what is wrong with it."""
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        return Known(), [f"invalid JSON: {exc.msg} (line {exc.lineno})"]
    problems = validate("known", data)
    if problems:
        return Known(), problems
    known = Known(created=data.get("created"))
    for index, item in enumerate(data["entries"]):
        if ("node" in item) == ("path" in item):
            problems.append(f"entries[{index}]: expected exactly one of `node` and `path`")
            continue
        entry = Entry(item["rule"], item.get("node", ""), item.get("path", ""), item.get("key", ""))
        if entry not in known.lines:
            known.entries.append(entry)
            known.lines[entry] = 0
    if problems:
        return Known(), problems
    written = {line.strip().rstrip(","): number for number, line in enumerate(text.splitlines(), 1)}
    known.lines = {entry: written[_line(entry)] for entry in known.entries if _line(entry) in written}
    return known, []


def load(root: Path) -> tuple[Known, list[str]]:
    """The known violations of a repository; empty when it has no `known.json`."""
    path = root / KNOWN_PATH
    if not path.is_file():
        return Known(), []
    try:
        return parse(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return Known(), ["file is not valid UTF-8"]


# bondstone: REQ-KNV-001
def render(entries: list[Entry], created: str) -> str:
    """The file's text: sorted, one entry per line, so that a diff shows exactly what left."""
    lines = ["{", f'  "bondstone": {FORMAT},', f'  "created": {json.dumps(created)},']
    ordered = sorted(set(entries))
    if ordered:
        lines.append('  "entries": [')
        lines += [f"    {_line(entry)}{',' if index < len(ordered) - 1 else ''}"
                  for index, entry in enumerate(ordered)]
        lines.append("  ]")
    else:
        lines.append('  "entries": []')
    lines.append("}")
    return "\n".join(lines) + "\n"


def write(root: Path, entries: list[Entry], created: str) -> None:
    (root / KNOWN_PATH).write_text(render(entries, created), encoding="utf-8")
