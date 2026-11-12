"""What agents and people ask before they act: which rules are active, and what one rule means.

Every answer uses effective severities, after the profile's overrides, because that is what
`check` will apply."""

from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass
from typing import Any

import yaml

from .catalogue import ENGINE_RULES, EngineRule
from .config import Config
from .model import Refused, Rule


@dataclass
class RuleInfo:
    """One active rule as `bondstone rules` lists it."""

    id: str
    kind: str  # node | diff | existence | engine
    severity: str  # effective
    default: str
    set_by: str  # "default" | "profile": where the effective severity comes from
    locked: bool
    description: str
    declared_in: str | None  # manifest of a declared rule; None for engine rules
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def _info(cfg: Config, rule: Rule | EngineRule) -> RuleInfo:
    if isinstance(rule, Rule):
        rule_id, kind, default, locked = rule.qid, rule.kind, rule.severity, rule.locked
        description, declared_in, hint = rule.description, rule.source, rule.spec.get("hint")
    else:
        rule_id, kind, default, locked = rule.id, "engine", rule.severity, not rule.overridable
        description, declared_in, hint = rule.fires, None, None
    return RuleInfo(rule_id, kind, cfg.severity(rule_id, default), default,
                    "profile" if rule_id in cfg.overrides else "default", locked, description, declared_in, hint)


# bondstone: REQ-AGT-001
def list_rules(cfg: Config) -> list[RuleInfo]:
    """Every rule that can report in this repository: declared rules first, then engine rules."""
    return [_info(cfg, rule) for rule in [*cfg.rules, *ENGINE_RULES]]


def rules_text(rules: list[RuleInfo]) -> str:
    lines = []
    for rule in rules:
        notes = []
        if rule.set_by == "profile":
            notes.append(f"default: {rule.default}")
        if rule.locked:
            notes.append("locked")
        suffix = f" [{'; '.join(notes)}]" if notes else ""
        lines.append(f"{rule.severity:<6} {rule.id}: {rule.description}{suffix}")
    return "\n".join(lines) + "\n"


def _find(cfg: Config, rule_id: str) -> Rule | EngineRule:
    known: dict[str, Rule | EngineRule] = {rule.qid: rule for rule in cfg.rules}
    known.update({rule.id: rule for rule in ENGINE_RULES})
    if rule_id in known:
        return known[rule_id]
    close = difflib.get_close_matches(rule_id, list(known), n=3, cutoff=0.5)
    suffix = [name for name in known if name.split("/", 1)[-1] == rule_id]
    suggestions = list(dict.fromkeys(suffix + close))
    hint = f"; did you mean {', '.join(suggestions)}?" if suggestions else "; `bondstone rules` lists them"
    raise Refused(f"unknown rule '{rule_id}'{hint}")


def _severity_line(info: RuleInfo) -> str:
    if info.set_by == "profile":
        return f"Severity: {info.severity} (set by the profile; default: {info.default})"
    return f"Severity: {info.severity} (default)"


# bondstone: REQ-AGT-002
def explain(cfg: Config, rule_id: str) -> dict[str, Any]:
    """Everything about one rule, declared or engine: what it asks, why, and how to satisfy it."""
    rule = _find(cfg, rule_id)
    info = _info(cfg, rule)
    out = info.to_dict()
    if isinstance(rule, Rule):
        out["spec"] = {key: value for key, value in rule.spec.items()
                       if key not in ("id", "description", "severity", "locked", "hint")}
    else:
        out.update({"fires": rule.fires, "why": rule.why, "fix": rule.fix})
        if rule.note:
            out["note"] = rule.note
        out.pop("description", None)
    return out


def explain_text(cfg: Config, rule_id: str) -> str:
    data = explain(cfg, rule_id)
    info = _info(cfg, _find(cfg, rule_id))
    if info.kind == "engine":
        lines = [f"{info.id} (engine rule)", _severity_line(info), "",
                 f"Fires when: {data['fires']}", f"Why: {data['why']}", f"Fix: {data['fix']}"]
        if data.get("note"):
            lines.append(f"Note: {data['note']}")
        if info.locked:
            lines.append("This rule cannot be overridden or waived.")
        return "\n".join(lines) + "\n"
    lines = [f"{info.id} ({info.kind} rule, declared in {info.declared_in})",
             _severity_line(info) + ("; locked: it can be raised but not lowered or waived" if info.locked else "")]
    if info.description:
        lines += ["", info.description]
    if info.hint:
        lines.append(f"Hint: {info.hint}")
    lines += ["", yaml.safe_dump(data["spec"], sort_keys=False, allow_unicode=True, width=100).rstrip()]
    return "\n".join(lines) + "\n"
