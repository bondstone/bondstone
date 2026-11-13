"""Add a waiver to the profile: `bondstone waive`.

A waiver is one deliberate exception: a rule, usually one node, a reason and the day it ends.
The command refuses what `check` would report as an invalid waiver, and adds one line to the
profile without touching the rest of it."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

import yaml

from .agent import find_rule
from .config import Config, load_config
from .graph import Graph
from .model import CONFIG_RULE, PROFILE_PATH, Refused

_KEY = re.compile(r"^waivers:[ \t]*(.*)$")
_TOP_LEVEL = re.compile(r"^[^\s#]")


@dataclass
class Waived:
    rule: str
    node: str | None
    reason: str
    expires: str
    path: str = PROFILE_PATH

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def _scalar(value: str) -> str:
    """A string as YAML reads it back unchanged: plain when that is safe, quoted otherwise."""
    try:
        plain = yaml.safe_load(value) == value and not re.search(r"[,\[\]{}#&*!|>'\"%@`]|: |^\s|\s$", value)
    except yaml.YAMLError:
        plain = False
    return value if plain else json.dumps(value, ensure_ascii=False)


def _entry(waiver: Waived) -> str:
    parts = [f"rule: {_scalar(waiver.rule)}"]
    if waiver.node:
        parts.append(f"node: {_scalar(waiver.node)}")
    parts += [f"reason: {json.dumps(waiver.reason, ensure_ascii=False)}", f"expires: {waiver.expires}"]
    return "- {" + ", ".join(parts) + "}"


def add_entry(text: str, entry: str) -> str:
    """The profile's text with one more item under `waivers`; only that block changes."""
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if _KEY.match(line)), None)
    if start is None:
        body = text if text.endswith("\n") or not text else text + "\n"
        return f"{body}\nwaivers:\n  {entry}\n"
    inline = _KEY.match(lines[start]).group(1).split("#")[0].strip()
    if inline not in ("", "[]"):
        raise Refused(f"`waivers` in {PROFILE_PATH} is written on one line; add the waiver by hand: {entry}")
    end = next((index for index in range(start + 1, len(lines)) if _TOP_LEVEL.match(lines[index])), len(lines))
    block = [index for index in range(start + 1, end) if lines[index].strip() and not lines[index].lstrip().startswith("#")]
    indent = re.match(r"\s*", lines[block[0]]).group(0) if block else "  "
    if inline == "[]":
        lines[start] = "waivers:"
    position = (block[-1] if block else start) + 1
    lines.insert(position, f"{indent}{entry}")
    return "\n".join(lines) + "\n"


# bondstone: REQ-PRF-016
def add_waiver(cfg: Config, graph: Graph, rule_id: str, node_id: str | None, reason: str, expires: str,
               today: dt.date | None = None) -> Waived:
    """Write a waiver into the profile; refuses one that `check` would report as invalid.

    Without a node the waiver covers every node, which is what a diagnostic without a node needs."""
    today = today or dt.date.today()
    find_rule(cfg, rule_id)  # refuses an unknown rule, with the closest ids
    if rule_id == CONFIG_RULE:
        raise Refused("configuration errors cannot be waived")
    lock = cfg.locks.get(rule_id)
    if lock is not None:
        raise Refused(f"{rule_id} is locked by {lock.by} and cannot be waived")
    if node_id is not None and node_id not in graph.by_id:
        raise Refused(f"no node with id '{node_id}'")
    if not reason.strip():
        raise Refused("--reason is empty: a waiver says why the exception is acceptable")
    try:
        day = dt.date.fromisoformat(expires)
    except ValueError:
        raise Refused(f"--expires: '{expires}' is not a date such as {today.replace(year=today.year + 1)}") from None
    if day < today:
        raise Refused(f"--expires: {expires} is in the past")
    for waiver in cfg.waivers:
        if waiver.get("rule") == rule_id and waiver.get("node") == node_id:
            raise Refused(f"{rule_id} is already waived for {node_id or 'every node'} until "
                          f"{waiver.get('expires')}; edit that waiver in {PROFILE_PATH}")
    waived = Waived(rule_id, node_id, " ".join(reason.split()), day.isoformat())
    path = cfg.root / PROFILE_PATH
    before = path.read_text(encoding="utf-8")
    path.write_text(add_entry(before, _entry(waived)), encoding="utf-8", newline="\n")
    after = load_config(cfg.root)
    expected = {"rule": rule_id, "reason": waived.reason, "expires": waived.expires, **({"node": node_id} if node_id else {})}
    if after.errors or expected not in after.waivers:
        path.write_text(before, encoding="utf-8", newline="\n")
        raise Refused(f"could not add the waiver to {PROFILE_PATH} without breaking it; add it by hand: {_entry(waived)}")
    return waived
