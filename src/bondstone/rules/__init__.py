"""Rules: engine rules, node rules and existence rules, and the policy applied to their results.

Diff rules, immutability and lifecycle transitions compare with a base commit and need the git
layer; they are declared and validated but not evaluated yet."""

from __future__ import annotations

import datetime as dt

from ..config import Config
from ..graph import Graph
from ..model import ERROR, WARN, Diagnostic
from .engine import check_engine
from .node import check_rules
from .policy import apply_policy

__all__ = ["apply_policy", "fails", "run_check"]


def run_check(cfg: Config, graph: Graph, today: dt.date | None = None) -> list[Diagnostic]:
    """Every diagnostic for a repository, after overrides and waivers.

    Expects a configuration without errors. `today` decides whether waivers have expired."""
    errors = cfg.errors
    diagnostics = [d for d in cfg.problems if d not in errors]
    diagnostics += graph.diagnostics
    diagnostics += check_engine(cfg, graph)
    diagnostics += check_rules(cfg, graph)
    return apply_policy(cfg, diagnostics, today)


def fails(diagnostics: list[Diagnostic], fail_on: str = ERROR) -> bool:
    """Whether a run fails: on errors, and on warnings too with `--fail-on warn`."""
    levels = {ERROR} if fail_on == ERROR else {ERROR, WARN}
    return any(d.severity in levels for d in diagnostics)
