"""Output formats. Text and JSON render the same diagnostics and the same summary."""

from __future__ import annotations

import json
from typing import Any

from .model import ERROR, INFO, WARN, Diagnostic

JSON_VERSION = 1  # version of the JSON output shape; raised when a key changes meaning or goes away
FORMATS = ("text", "json")


def summarize(diagnostics: list[Diagnostic], nodes: int | None = None) -> dict[str, int]:
    summary = {
        "errors": sum(d.severity == ERROR for d in diagnostics),
        "warnings": sum(d.severity == WARN for d in diagnostics),
        "info": sum(d.severity == INFO for d in diagnostics),
    }
    known = sum(d.known for d in diagnostics)
    if known:
        summary["known"] = known  # counted under `info` too
    if nodes is not None:
        summary["nodes"] = nodes
    return summary


# bondstone: REQ-CLI-005
def to_text(diagnostics: list[Diagnostic], nodes: int | None = None) -> str:
    """One line per diagnostic, `path:line: severity rule: message`, then an indented hint."""
    lines = []
    for diag in diagnostics:
        location = diag.path or "<repository>"
        if diag.line:
            location += f":{diag.line}"
        lines.append(f"{location}: {diag.severity} {diag.rule}: {diag.message}" + (" [known]" if diag.known else ""))
        if diag.hint:
            lines.append(f"    hint: {diag.hint}")
    summary = summarize(diagnostics, nodes)
    total = f"{summary['errors']} error(s), {summary['warnings']} warning(s)"
    if summary["info"]:
        total += f", {summary['info']} info"
    if summary.get("known"):
        total += f" ({summary['known']} known)"
    if nodes is not None:
        total += f", {nodes} nodes"
    lines.append(("✗ " if summary["errors"] else "✓ ") + total)
    return "\n".join(lines) + "\n"


# bondstone: REQ-CLI-006
def to_json(diagnostics: list[Diagnostic], nodes: int | None = None, base: dict[str, Any] | None = None) -> str:
    """`base`, with `check --base`: the ref, the commit compared with and the files that differ."""
    payload: dict[str, Any] = {"version": JSON_VERSION, "summary": summarize(diagnostics, nodes)}
    if base is not None:
        payload["base"] = base
    payload["diagnostics"] = [diag.to_dict() for diag in diagnostics]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render(fmt: str, diagnostics: list[Diagnostic], nodes: int | None = None,
           base: dict[str, Any] | None = None) -> str:
    return to_json(diagnostics, nodes, base) if fmt == "json" else to_text(diagnostics, nodes)
