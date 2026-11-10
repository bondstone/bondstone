"""Rules: engine rules, node rules, existence rules and stale views, and the policy applied to them.

With a base commit, the checks that need history run too: lifecycles, immutability and diff
rules, with the exemptions that commit trailers declare."""

from __future__ import annotations

import datetime as dt

from ..config import Config
from ..git import Repository
from ..graph import Graph
from ..model import ERROR, WARN, Diagnostic
from ..views import check_views
from .diff import check_changes
from .engine import check_engine
from .node import check_rules
from .policy import apply_policy

__all__ = ["apply_policy", "fails", "run_check"]


# bondstone: REQ-CLI-001
def run_check(cfg: Config, graph: Graph, today: dt.date | None = None, *, repo: Repository | None = None,
              base: str | None = None, exemptions: bool = True) -> list[Diagnostic]:
    """Every diagnostic for a repository, after overrides and waivers.

    Expects a configuration without errors. `today` decides whether waivers have expired.
    With `repo` and `base`, the changes since that commit are checked as well; `exemptions`
    says whether commit trailers may exempt diff-rule violations."""
    errors = cfg.errors
    diagnostics = [d for d in cfg.problems if d not in errors]
    diagnostics += graph.diagnostics
    diagnostics += check_engine(cfg, graph)
    diagnostics += check_rules(cfg, graph)
    if repo is not None and base is not None:
        diagnostics += check_changes(cfg, graph, repo, base, exemptions)
    diagnostics += check_views(cfg, graph)
    return apply_policy(cfg, diagnostics, today)


# bondstone: REQ-CLI-007
def fails(diagnostics: list[Diagnostic], fail_on: str = ERROR) -> bool:
    """Whether a run fails: on errors, and on warnings too with `--fail-on warn`."""
    levels = {ERROR} if fail_on == ERROR else {ERROR, WARN}
    return any(d.severity in levels for d in diagnostics)
