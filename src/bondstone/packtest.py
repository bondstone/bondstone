"""Run the fixtures of a pack or a bridge: `bondstone pack test`.

A fixture is a small repository in `fixtures/<case>/` of the component, with a profile and an
`expected.yaml` that lists the rule of every error and warning the check must report there."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import load_config
from .graph import build_graph
from .manifest import MANIFEST_NAMES, ManifestError, load_yaml
from .model import ERROR, PROFILE_PATH, WARN, Diagnostic, EnvironmentProblem
from .rules import run_check

EXPECTED = "expected.yaml"
LEVELS = {"errors": ERROR, "warnings": WARN}  # key of expected.yaml -> severity


@dataclass
class CaseResult:
    component: str
    kind: str  # "pack" | "bridge"
    case: str | None  # the fixture's folder name; None when the component has no fixtures
    path: str
    problems: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.problems

    @property
    def name(self) -> str:
        return f"{self.component}/{self.case}" if self.case else self.component

    def to_dict(self) -> dict[str, Any]:
        return {"component": self.component, "kind": self.kind, "case": self.case, "path": self.path,
                "passed": self.passed, "problems": self.problems}


def component_of(directory: Path) -> tuple[str, str]:
    """Kind and id of the pack or bridge in a folder."""
    if not directory.is_dir():
        raise EnvironmentProblem(f"'{directory}' is not a directory")
    for kind, filename in MANIFEST_NAMES.items():
        manifest = directory / filename
        if manifest.is_file():
            try:
                data = load_yaml(manifest)
            except ManifestError as exc:
                raise EnvironmentProblem(f"{manifest}: {exc}") from exc
            cid = data.get("id") if isinstance(data, dict) else None
            return kind, cid if isinstance(cid, str) else directory.name
    names = " or ".join(MANIFEST_NAMES.values())
    raise EnvironmentProblem(f"'{directory}' is not a pack or a bridge: it has no {names}")


def _location(diag: Diagnostic) -> str:
    where = diag.path or "<repository>"
    return f"{where}:{diag.line}" if diag.line else where


def _expected(case: Path) -> tuple[dict[str, Counter], list[str]]:
    """The rules a fixture expects per severity, and what is wrong with its `expected.yaml`."""
    path = case / EXPECTED
    if not path.is_file():
        return {}, [f"no {EXPECTED}: list the expected rules under `errors` and `warnings`"]
    try:
        data = load_yaml(path)
    except ManifestError as exc:
        return {}, [f"{EXPECTED}: {exc}"]
    data = {} if data is None else data
    if not isinstance(data, dict):
        return {}, [f"{EXPECTED}: expected a mapping with `errors` and `warnings`"]
    problems = [f"{EXPECTED}: unknown key '{key}' (allowed: errors, warnings)" for key in data if key not in LEVELS]
    expected: dict[str, Counter] = {}
    for key, level in LEVELS.items():
        rules = data.get(key) or []
        if not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules):
            problems.append(f"{EXPECTED}: `{key}` must be a list of rule ids")
            rules = []
        expected[level] = Counter(rules)
    return expected, problems


# bondstone: REQ-PKT-002
def _run_case(result: CaseResult, case: Path, sources: list[Path], today: dt.date | None) -> CaseResult:
    if not (case / PROFILE_PATH).is_file():
        result.problems.append(f"no {PROFILE_PATH}: a fixture is a small repository with its own profile")
        return result
    expected, problems = _expected(case)
    result.problems += problems
    cfg = load_config(case, extra_sources=sources)
    if cfg.errors:
        result.problems += [f"configuration error at {_location(d)}: {d.message}" for d in cfg.errors]
    if result.problems:
        return result
    diagnostics = run_check(cfg, build_graph(cfg), today=today)
    for level in LEVELS.values():
        found = Counter(d.rule for d in diagnostics if d.severity == level)
        for rule in sorted((expected[level] - found).elements()):
            result.problems.append(f"expected {level} {rule} was not reported")
        unexpected = found - expected[level]
        for diag in diagnostics:
            if diag.severity == level and unexpected[diag.rule] > 0:
                unexpected[diag.rule] -= 1
                result.problems.append(f"unexpected {level} {diag.rule} at {_location(diag)}: {diag.message}")
    return result


# bondstone: REQ-PKT-001
def run_fixtures(directory: Path, today: dt.date | None = None) -> list[CaseResult]:
    """Check every fixture of the pack or bridge in `directory`, in the order of their names.

    The component under test and its neighbours in the same folder are found before anything
    else, so a fixture tests this copy and not one from the library."""
    kind, cid = component_of(directory)
    fixtures = directory / "fixtures"
    cases = sorted(p for p in fixtures.iterdir() if p.is_dir()) if fixtures.is_dir() else []
    if not cases:
        return [CaseResult(cid, kind, None, directory.as_posix(),
                           ["no fixtures: add fixtures/<case>/ with a profile, documents and expected.yaml"])]
    sources = [directory.resolve().parent]
    return [_run_case(CaseResult(cid, kind, case.name, case.as_posix()), case, sources, today) for case in cases]


def to_text(results: list[CaseResult]) -> str:
    lines = []
    for result in results:
        lines.append(f"ok   {result.name}" if result.passed else f"FAIL {result.name} ({result.path})")
        lines += [f"     {problem}" for problem in result.problems]
    failed = sum(not result.passed for result in results)
    if failed:
        lines.append(f"✗ {failed} of {len(results)} fixture(s) failed")
    else:
        lines.append(f"✓ {len(results)} fixture(s) passed")
    return "\n".join(lines) + "\n"


def to_dict(results: list[CaseResult]) -> dict[str, Any]:
    failed = sum(not result.passed for result in results)
    return {"summary": {"passed": len(results) - failed, "failed": failed},
            "fixtures": [result.to_dict() for result in results]}
