"""SARIF 2.1.0 output for `check`, the format that code-scanning tools read.

One run with one result per diagnostic. A known violation and an exempted one are results
with a suppression, so a viewer shows them as accepted and not as open problems."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from . import __version__
from .catalogue import engine_rule
from .config import Config
from .known import KNOWN_PATH, fingerprint
from .model import ERROR, WARN, Diagnostic

SARIF_VERSION = "2.1.0"
SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
INFORMATION_URI = "https://github.com/bondstone/bondstone"
_LEVELS = {ERROR: "error", WARN: "warning"}  # anything else is a note


def _level(severity: str) -> str:
    return _LEVELS.get(severity, "note")


def _rule(cfg: Config, rule_id: str) -> dict[str, Any]:
    """What a viewer shows about a rule: what it checks and how to satisfy it."""
    engine = engine_rule(rule_id)
    if engine is not None:
        short, full, help_text = engine.fires, f"{engine.fires} {engine.why}", engine.fix
        default = engine.severity
    else:
        declared = cfg.rule(rule_id)
        short = (declared.description if declared else "") or rule_id
        full = short
        help_text = str(declared.spec.get("hint") or short) if declared else short
        default = declared.severity if declared else ERROR
    return {
        "id": rule_id,
        "shortDescription": {"text": short},
        "fullDescription": {"text": full},
        "help": {"text": help_text},
        "defaultConfiguration": {"level": _level(cfg.severity(rule_id, default))},
    }


def _suppressions(diag: Diagnostic) -> list[dict[str, str]]:
    if diag.known:
        return [{"kind": "external", "justification": f"recorded as a known violation in {KNOWN_PATH}"}]
    if diag.exempted_by:
        by = diag.exempted_by
        return [{"kind": "external",
                 "justification": f"{by.get('trailer')}: {by.get('reason')} (commit {by.get('commit', '')[:7]})"}]
    return []


def _result(diag: Diagnostic, index: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ruleId": diag.rule,
        "ruleIndex": index,
        "level": _level(diag.severity),
        "message": {"text": diag.message + (f"\n\n{diag.hint}" if diag.hint else "")},
    }
    if diag.path:
        location: dict[str, Any] = {"artifactLocation": {"uri": diag.path, "uriBaseId": "%SRCROOT%"}}
        if diag.line:
            location["region"] = {"startLine": diag.line}
        result["locations"] = [{"physicalLocation": location}]
    entry = fingerprint(diag)
    identity = "\0".join((entry.rule, entry.node, entry.path, entry.key))
    # the same rule, node and key as a known violation: stable when lines move
    result["partialFingerprints"] = {"bondstone/v1": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]}
    suppressions = _suppressions(diag)
    if suppressions:
        result["suppressions"] = suppressions
    properties = {key: value for key, value in (("node", diag.node), ("fix", (diag.fix or {}).get("command")))
                  if value}
    if properties:
        result["properties"] = properties
    return result


# bondstone: REQ-CLI-010
def to_sarif(cfg: Config, diagnostics: list[Diagnostic], successful: bool = True) -> str:
    """The diagnostics as one SARIF run. `successful` is false when the configuration stopped the check."""
    rule_ids = list(dict.fromkeys(diag.rule for diag in diagnostics))
    index = {rule_id: position for position, rule_id in enumerate(rule_ids)}
    log = {
        "$schema": SCHEMA,
        "version": SARIF_VERSION,
        "runs": [{
            "tool": {"driver": {
                "name": "bondstone",
                "version": __version__,
                "informationUri": INFORMATION_URI,
                "rules": [_rule(cfg, rule_id) for rule_id in rule_ids],
            }},
            "invocations": [{"executionSuccessful": successful}],
            "results": [_result(diag, index[diag.rule]) for diag in diagnostics],
        }],
    }
    return json.dumps(log, indent=2, ensure_ascii=False) + "\n"
