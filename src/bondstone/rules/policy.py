"""Apply the profile's policy to raw diagnostics: overrides, waivers and ordering."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import Any

from ..catalogue import diagnostic, engine_rule
from ..config import Config
from ..model import CONFIG_RULE, IGNORE, PROFILE_PATH, Diagnostic


def apply_policy(cfg: Config, diagnostics: list[Diagnostic], today: dt.date | None = None) -> list[Diagnostic]:
    """Effective severities, then waivers; what remains is sorted by location.

    A rule overridden to `ignore` reports nothing. A waiver removes the diagnostics of one
    rule (for one node, when it names one) until it expires. Waivers that are incomplete,
    expired or unused are reported themselves."""
    today = today or dt.date.today()
    waivers, about_waivers = _active_waivers(cfg, today)
    kept: list[Diagnostic] = []
    for diag in diagnostics:
        diag = replace(diag, severity=cfg.severity(diag.rule, diag.severity))
        if diag.severity == IGNORE:
            continue
        waived = False
        for waiver in waivers:
            if waiver["rule"] == diag.rule and waiver.get("node") in (None, diag.node):
                waiver["used"] = waived = True
        if not waived:
            kept.append(diag)
    for waiver in waivers:
        if not waiver["used"]:
            about_waivers.append(diagnostic(
                "bondstone/waiver-unused", f"waiver for {_subject(waiver)} matches nothing", PROFILE_PATH))
    for diag in about_waivers:
        diag = replace(diag, severity=cfg.severity(diag.rule, diag.severity))
        if diag.severity != IGNORE:
            kept.append(diag)
    kept.sort(key=lambda d: (d.path or "", d.line or 0, d.rule, d.message))
    return kept


def _subject(waiver: dict[str, Any]) -> str:
    return f"{waiver['rule']} ({waiver.get('node') or 'all nodes'})"


def _active_waivers(cfg: Config, today: dt.date) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    active: list[dict[str, Any]] = []
    problems: list[Diagnostic] = []

    def invalid(message: str) -> None:
        problems.append(diagnostic("bondstone/waiver-invalid", message, PROFILE_PATH))

    for index, waiver in enumerate(cfg.waivers, 1):
        missing = [key for key in ("rule", "reason", "expires") if not waiver.get(key)]
        if missing:
            name = waiver.get("rule") or f"#{index}"
            invalid(f"waiver for {name} has no {', '.join(repr(key) for key in missing)}")
            continue
        rule_id = waiver["rule"]
        try:
            expires = dt.date.fromisoformat(waiver["expires"])
        except ValueError:
            invalid(f"waiver for {_subject(waiver)}: 'expires' must be a date such as 2027-06-30")
            continue
        declared = cfg.rule(rule_id)
        engine = engine_rule(rule_id)
        if declared is None and engine is None:
            invalid(f"waiver names an unknown rule '{rule_id}'")
        elif rule_id == CONFIG_RULE:
            invalid("configuration errors cannot be waived")
        elif declared is not None and declared.locked:
            invalid(f"waiver for {_subject(waiver)}: the rule is locked and cannot be waived")
        elif expires < today:
            problems.append(diagnostic(
                "bondstone/waiver-expired", f"waiver for {_subject(waiver)} expired on {waiver['expires']}",
                PROFILE_PATH))
        else:
            active.append({**waiver, "used": False})
    return active, problems
