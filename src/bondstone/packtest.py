"""`bondstone pack test`: run a pack's or bridge's fixtures."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .checks import run_check
from .loader import load_config, load_yaml
from .model import ERROR, WARN, BondstoneError


@dataclass
class CaseResult:
    name: str
    passed: bool
    detail: str


def run_fixtures(component_dir: Path) -> list[CaseResult]:
    fixtures = component_dir / "fixtures"
    if not fixtures.is_dir():
        raise BondstoneError(f"{component_dir} has no fixtures/ directory")
    results = []
    for case in sorted(p for p in fixtures.iterdir() if p.is_dir()):
        expected_file = case / "expected.yaml"
        expected = load_yaml(expected_file) if expected_file.exists() else {}
        try:
            cfg = load_config(case, extra_sources=[component_dir.parent])
            diags = run_check(cfg)
        except BondstoneError as exc:
            results.append(CaseResult(case.name, False, f"configuration error: {exc}"))
            continue
        got = {
            ERROR: Counter(d.rule for d in diags if d.severity == ERROR),
            WARN: Counter(d.rule for d in diags if d.severity == WARN),
        }
        want = {
            ERROR: Counter(expected.get("errors") or []),
            WARN: Counter(expected.get("warnings") or []),
        }
        problems = []
        for level in (ERROR, WARN):
            missing = want[level] - got[level]
            unexpected = got[level] - want[level]
            if missing:
                problems.append(f"missing {level}s: {sorted(missing.elements())}")
            if unexpected:
                problems.append(f"unexpected {level}s: {sorted(unexpected.elements())}")
        if problems:
            listing = "\n".join("      " + d.format().replace("\n", "\n      ") for d in diags)
            results.append(CaseResult(case.name, False, "; ".join(problems) + "\n" + listing))
        else:
            results.append(CaseResult(case.name, True, ""))
    return results
