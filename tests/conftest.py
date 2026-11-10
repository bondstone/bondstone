from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "habit-tracker"
EXAMPLE_PACKS = EXAMPLE / ".bondstone" / "packs"


class Project:
    """A throwaway repository to run bondstone against."""

    def __init__(self, root: Path):
        self.root = root

    def profile(self, **data) -> "Project":
        data = {"bondstone": 1, **data}
        return self.write(".bondstone/profile.yaml", yaml.safe_dump(data, sort_keys=False))

    def pack(self, pack_id: str, text: str, folder: str = ".bondstone/packs") -> "Project":
        return self.write(f"{folder}/{pack_id}/pack.yaml", text)

    def bridge(self, bridge_id: str, text: str, folder: str = ".bondstone/packs") -> "Project":
        return self.write(f"{folder}/{bridge_id}/bridge.yaml", text)

    def write(self, path: str, text: str) -> "Project":
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")
        return self

    def read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Project:
    return Project(tmp_path)


# --------------------------------------------------------------------------- packs for tests

ADR_PACK = """
    id: adr
    version: 1.0.0
    types:
      Decision:
        id: "ADR-{n:03d}"
        path: "docs/adr/{id}-{slug}.md"
        fields:
          title: {type: string, minLength: 3}
          date: {type: string, format: date}
          deciders: {type: array, items: {type: string}}
        required: [title, date]
        sections: [Context, Decision, Consequences]
        traits:
          lifecycle:
            statuses: [proposed, accepted, rejected, deprecated, superseded]
            initial: proposed
            transitions:
              proposed: [accepted, rejected]
              accepted: [deprecated, superseded]
          owned: {}
          supersedable: {link: supersedes}
          immutable: {when: [accepted, rejected, deprecated, superseded], allow: [status]}
          indexed: {}
    links:
      supersedes: {from: Decision, to: Decision, max: 1}
    rules:
      - id: alternatives-considered
        description: Accepted decisions record the alternatives that were considered.
        severity: warn
        when: {type: Decision, status: accepted}
        require: [{contains: "(?im)^#{2,3}\\\\s+(Alternatives|Options)"}]
        hint: Add a "## Alternatives considered" section.
    views:
      - id: decision-log
        title: Decision log
        output: docs/generated/decisions.md
        select: {type: Decision}
        columns: [id, title, status, date, owner]
"""

CAPABILITY_PACK = """
    id: capability
    version: 1.0.0
    types:
      Capability:
        id: "CAP-{slug}"
        path: "docs/capabilities/{slug}.md"
        fields:
          title: {type: string, minLength: 3}
          code: {type: string, pattern: "^[A-Z][A-Z0-9]{1,9}$"}
        required: [title, code]
        sections: [Purpose, Requirements]
        items:
          type: Requirement
          section: Requirements
          heading: "### {id}: {title}"
          id: "REQ-{code}-{n:03d}"
        traits:
          lifecycle: {statuses: [draft, active, deprecated], initial: draft}
          owned: {}
      Requirement:
        embedded: true
        traits:
          lifecycle: {statuses: [planned, active, removed], default: active}
          code-traceable: {coverage: warn, when: [active], retired: [removed]}
    links:
      depends_on: {from: Capability, to: Capability}
    rules:
      - id: requirement-has-scenario
        description: Every requirement has at least one scenario.
        when: {type: Requirement}
        require: [{contains: "(?m)^####\\\\s+Scenario:"}]
"""

ADR_CAPABILITY_BRIDGE = """
    id: adr-capability
    version: 1.0.0
    requires: {adr: "^1", capability: "^1"}
    links:
      constrained_by: {from: capability:Capability, to: adr:Decision}
    roles:
      decision: [adr:Decision]
      living-spec: [capability:Capability]
    rules:
      - id: constrained-by-live-decision
        description: Capabilities are constrained only by proposed or accepted decisions.
        when: {type: capability:Capability}
        require: [{link: constrained_by, all: true, to: {type: adr:Decision, status: [proposed, accepted]}}]
        hint: Point to the decision that superseded it.
      - id: accepted-decision-is-applied
        description: An accepted decision constrains at least one capability.
        severity: warn
        when: {type: adr:Decision, status: accepted}
        require: [{incoming: constrained_by, min: 1}]
"""

ADR_BODY = """
## Context

c

## Decision

d

## Alternatives considered

a

## Consequences

x
"""


def adr(doc_id: str, status: str = "accepted", extra: str = "", body: str = ADR_BODY) -> str:
    """An adr:Decision document that is valid unless `extra` or `body` break it."""
    return (f"---\nid: {doc_id}\ntype: adr:Decision\ntitle: Decision {doc_id}\nstatus: {status}\n"
            f"owner: me\ndate: 2026-01-01\n{extra}---\n{body}")


def capability(doc_id: str = "CAP-a", code: str = "AA", extra: str = "", requirements: str | None = None) -> str:
    """A capability:Capability document with one covered-by-nothing requirement."""
    if requirements is None:
        requirements = f"### REQ-{code}-001: Thing\n\nThe system SHALL do the thing.\n\n#### Scenario: ok\n\n- Then fine\n"
    return (f"---\nid: {doc_id}\ntype: capability:Capability\ntitle: Capability {doc_id}\nstatus: active\n"
            f"owner: me\ncode: {code}\n{extra}---\n## Purpose\n\np\n\n## Requirements\n\n{requirements}")


def standard(project: Project, **profile) -> Project:
    """A project with the adr and capability packs and their bridge; views are not checked."""
    project.pack("adr", ADR_PACK).pack("capability", CAPABILITY_PACK).bridge("adr-capability", ADR_CAPABILITY_BRIDGE)
    profile.setdefault("packs", ["adr@1", "capability@1"])
    profile.setdefault("bridges", ["adr-capability@1"])
    profile["overrides"] = {"bondstone/view-stale": "ignore", **profile.get("overrides", {})}
    return project.profile(**profile)


def check(project: Project, today=None):
    """Run a full check; fails the test on a configuration error."""
    from bondstone.config import load_config
    from bondstone.graph import build_graph
    from bondstone.rules import run_check

    cfg = load_config(project.root)
    assert cfg.errors == [], [d.message for d in cfg.errors]
    return run_check(cfg, build_graph(cfg), today=today)


def rule_ids(project: Project, severity: str | None = None, today=None) -> list[str]:
    return sorted(d.rule for d in check(project, today) if severity is None or d.severity == severity)
