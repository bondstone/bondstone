"""Counts about a repository's documentation: `bondstone report`.

`check` says what is wrong now. The report says where the repository stands: how many nodes
of each type and status, how much is traced to code, which waivers are running out, how many
known violations remain, and with a base commit how often changes were exempted."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .config import Config, as_list
from .git import Repository
from .graph import Graph
from .model import IGNORE
from .rules import run_check

EXPIRING_DAYS = 30  # a waiver that ends within this many days is "expiring"


@dataclass
class Report:
    nodes: dict[str, dict[str, int]]  # type -> status ("" when the type has none) -> count
    coverage: dict[str, dict[str, int]]  # code-traceable type -> needing_code, covered
    waivers: list[dict[str, Any]]
    known: dict[str, Any]
    exemptions: dict[str, Any] | None = None  # with a base commit

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "nodes": {"total": sum(sum(by.values()) for by in self.nodes.values()),
                      "by_type": {name: {"total": sum(by.values()),
                                         "by_status": {status: count for status, count in by.items() if status}}
                                  for name, by in self.nodes.items()}},
            "coverage": self.coverage,
            "waivers": self.waivers,
            "known": self.known,
        }
        if self.exemptions is not None:
            out["exemptions"] = self.exemptions
        return out


def _sorted(counter: Counter) -> dict[str, int]:
    """Counts with the largest first, ties in alphabetical order."""
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


# bondstone: REQ-CLI-008
def build_report(cfg: Config, graph: Graph, today: dt.date | None = None, *, repo: Repository | None = None,
                 base: str | None = None) -> Report:
    today = today or dt.date.today()
    nodes: dict[str, Counter] = {}
    for node in graph.nodes:
        nodes.setdefault(node.type, Counter())[node.status or ""] += 1

    coverage: dict[str, dict[str, int]] = {}
    for qname, tdef in cfg.types.items():
        tracing = tdef.traits.get("code-traceable")
        if tracing is None or tracing.get("coverage") == IGNORE:
            continue
        wanted = {str(status) for status in as_list(tracing["when"])} if tracing.get("when") is not None else None
        needing = [node for node in graph.nodes if node.type == qname and (wanted is None or node.status in wanted)]
        coverage[qname] = {"needing_code": len(needing), "covered": sum(node.covered for node in needing)}

    diagnostics = run_check(cfg, graph, today=today, repo=repo, base=base)
    return Report(
        nodes={name: dict(sorted(by.items())) for name, by in sorted(nodes.items())},
        coverage=dict(sorted(coverage.items())),
        waivers=_waivers(cfg, diagnostics, today),
        known=_known(cfg, graph),
        exemptions=_exemptions(repo, base, diagnostics) if repo is not None and base is not None else None,
    )


def _waivers(cfg: Config, diagnostics: list[Any], today: dt.date) -> list[dict[str, Any]]:
    """Every waiver of the profile with its state: active, expiring, expired, unused or invalid."""
    about = {"bondstone/waiver-unused": "unused", "bondstone/waiver-invalid": "invalid"}
    out = []
    for waiver in cfg.waivers:
        subject = f"{waiver.get('rule')} ({waiver.get('node') or 'all nodes'})"
        state = "active"
        try:
            expires = dt.date.fromisoformat(str(waiver.get("expires")))
        except ValueError:
            expires = None
        for diag in diagnostics:
            if diag.rule in about and subject in diag.message:
                state = about[diag.rule]
        if expires is None or not waiver.get("rule") or not waiver.get("reason"):
            state = "invalid"
        elif expires < today:
            state = "expired"
        elif state == "active" and (expires - today).days <= EXPIRING_DAYS:
            state = "expiring"
        out.append({key: value for key, value in {
            "rule": waiver.get("rule"), "node": waiver.get("node"), "reason": waiver.get("reason"),
            "expires": waiver.get("expires"), "state": state}.items() if value is not None})
    return out


def _known(cfg: Config, graph: Graph) -> dict[str, Any]:
    """The entries of `known.json` per rule and per type of the node they are about."""
    by_rule: Counter = Counter()
    by_type: Counter = Counter()
    for entry in cfg.known.entries:
        by_rule[entry.rule] += 1
        node = graph.by_id.get(entry.node) if entry.node else None
        by_type[node.type if node is not None else ("(files)" if entry.path else "(unknown)")] += 1
    out: dict[str, Any] = {"total": len(cfg.known.entries), "by_rule": _sorted(by_rule), "by_type": _sorted(by_type)}
    if cfg.known.created:
        out["created"] = cfg.known.created
    return out


def _exemptions(repo: Repository, base: str, diagnostics: list[Any]) -> dict[str, Any]:
    """How often commit trailers exempted a violation since the base, per rule and per author."""
    by_rule: Counter = Counter()
    by_author: Counter = Counter()
    total = 0
    for diag in diagnostics:
        if diag.rule != "bondstone/exemption-used" or not diag.exempted_by:
            continue
        total += 1
        by_rule[diag.exempted_by.get("rule", "?")] += 1
        by_author[repo.author(diag.exempted_by["commit"]) or "?"] += 1
    return {"base": base, "total": total, "by_rule": _sorted(by_rule), "by_author": _sorted(by_author)}


def to_text(report: Report) -> str:
    data = report.to_dict()
    lines = [f"Nodes: {data['nodes']['total']}"]
    for name, by in data["nodes"]["by_type"].items():
        statuses = ", ".join(f"{count} {status}" for status, count in by["by_status"].items())
        lines.append(f"  {name}: {by['total']}" + (f" ({statuses})" if statuses else ""))
    lines += ["", "Traced to code:"]
    for name, counts in report.coverage.items():
        share = f"{100 * counts['covered'] // counts['needing_code']}%" if counts["needing_code"] else "-"
        lines.append(f"  {name}: {counts['covered']} of {counts['needing_code']} that need code ({share})")
    if not report.coverage:
        lines.append("  no type is code-traceable")
    states = Counter(waiver["state"] for waiver in report.waivers)
    summary = ", ".join(f"{count} {state}" for state, count in sorted(states.items()))
    lines += ["", f"Waivers: {len(report.waivers)}" + (f" ({summary})" if summary else "")]
    for waiver in report.waivers:
        lines.append(f"  {waiver['state']}: {waiver.get('rule', '?')} on {waiver.get('node') or 'all nodes'}, "
                     f"until {waiver.get('expires', '?')}")
    lines += ["", f"Known violations: {report.known['total']}"
              + (f" (recorded {report.known['created']})" if report.known.get("created") else "")]
    for title, key in (("by rule", "by_rule"), ("by type", "by_type")):
        if report.known[key]:
            lines.append(f"  {title}:")
            lines += [f"    {count:>4}  {name}" for name, count in report.known[key].items()]
    if report.exemptions is not None:
        lines += ["", f"Exemptions used since {report.exemptions['base']}: {report.exemptions['total']}"]
        for title, key in (("by rule", "by_rule"), ("by author", "by_author")):
            if report.exemptions[key]:
                lines.append(f"  {title}:")
                lines += [f"    {count:>4}  {name}" for name, count in report.exemptions[key].items()]
    return "\n".join(lines) + "\n"
