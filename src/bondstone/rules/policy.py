"""Apply the profile's policy to raw diagnostics: overrides, waivers, known violations and ordering."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import Any

from ..catalogue import default_severity, diagnostic, engine_rule
from ..config import Config
from ..known import KNOWN_PATH, Entry, fingerprint
from ..model import CONFIG_RULE, IGNORE, INFO, PROFILE_PATH, Diagnostic


# bondstone: REQ-PRF-007, REQ-PRF-008
def apply_policy(cfg: Config, diagnostics: list[Diagnostic], today: dt.date | None = None) -> list[Diagnostic]:
    """Effective severities, then waivers, then known violations; what remains is sorted by location.

    A rule overridden to `ignore` reports nothing. A waiver removes the diagnostics of one
    rule (for one node, when it names one) until it expires. Waivers that are incomplete,
    expired or unused are reported themselves. A violation that a commit trailer exempts is
    kept, as `bondstone/exemption-used`. A violation recorded in `known.json` is kept as info,
    and an entry of that file that matches nothing is reported as `bondstone/known-stale`."""
    today = today or dt.date.today()
    waivers, about_waivers = _active_waivers(cfg, today)
    recorded = set(cfg.known.entries)
    unmatched = set(recorded)
    kept: list[Diagnostic] = []
    for diag in diagnostics:
        diag = replace(diag, severity=cfg.severity(diag.rule, diag.severity))
        if diag.severity == IGNORE:
            continue
        waived = False
        for waiver in waivers:
            if waiver["rule"] == diag.rule and waiver.get("node") in (None, diag.node):
                waiver["used"] = waived = True
        if waived:
            continue
        if diag.exempted_by:
            diag = _exempted(cfg, diag)
            if diag is None:
                continue
        # bondstone: REQ-KNV-003
        elif cfg.known and cfg.accepts_known(diag.rule):
            entry = fingerprint(diag)
            if entry in recorded:
                unmatched.discard(entry)
                diag = replace(diag, severity=INFO, known=True)
        kept.append(diag)
    for waiver in waivers:
        if not waiver["used"]:
            about_waivers.append(diagnostic(
                "bondstone/waiver-unused", f"waiver for {_subject(waiver)} matches nothing", PROFILE_PATH))
    for diag in about_waivers + _stale(cfg, unmatched):
        diag = replace(diag, severity=cfg.severity(diag.rule, diag.severity))
        if diag.severity != IGNORE:
            kept.append(diag)
    kept.sort(key=lambda d: (d.path or "", d.line or 0, d.rule, d.message))
    return kept


# bondstone: REQ-DIF-011
def _exempted(cfg: Config, diag: Diagnostic) -> Diagnostic | None:
    """An exempted violation, reported as `bondstone/exemption-used` so that nothing is hidden."""
    rule = "bondstone/exemption-used"
    severity = cfg.severity(rule, default_severity(rule))
    if severity == IGNORE:
        return None
    by = diag.exempted_by or {}
    subject = f"{diag.rule} on {diag.node}" if diag.node else diag.rule
    message = (f"{subject} exempted by commit {by.get('commit', '')[:7]} "
               f"({by.get('trailer')}: {by.get('reason')}): {diag.message}")
    return replace(diag, rule=rule, severity=severity, message=message, hint=None, fix=None)


# bondstone: REQ-KNV-004
def _stale(cfg: Config, unmatched: set[Entry]) -> list[Diagnostic]:
    """`bondstone/known-stale` for every entry of `known.json` that no violation matched."""
    out = []
    for entry in sorted(unmatched):
        if cfg.rule(entry.rule) is None and engine_rule(entry.rule) is None:
            why = "the rule does not exist"
        elif not cfg.accepts_known(entry.rule):
            why = "the rule does not accept known violations"
        else:
            why = "the violation no longer occurs"
        out.append(diagnostic(
            "bondstone/known-stale", f"known violation {entry}: {why}", KNOWN_PATH,
            cfg.known.lines.get(entry) or None, entry.node or None,
            hint="Run `bondstone baseline --known --prune`."))
    return out


def _subject(waiver: dict[str, Any]) -> str:
    return f"{waiver['rule']} ({waiver.get('node') or 'all nodes'})"


# bondstone: REQ-PRF-008
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
        elif rule_id in cfg.locks:
            invalid(f"waiver for {_subject(waiver)}: the rule is locked and cannot be waived")
        elif expires < today:
            problems.append(diagnostic(
                "bondstone/waiver-expired", f"waiver for {_subject(waiver)} expired on {waiver['expires']}",
                PROFILE_PATH))
        else:
            active.append({**waiver, "used": False})
    return active, problems
