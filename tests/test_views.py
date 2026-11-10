from conftest import adr, capability, check, standard

from bondstone.config import load_config
from bondstone.graph import build_graph
from bondstone.views import generate, render, stale_views

OST = """
    id: ost
    version: 1.0.0
    types:
      Outcome:
        id: "OUT-{n}"
        path: "docs/discovery/outcomes/{id}-{slug}.md"
        traits: {lifecycle: {statuses: [active, achieved], initial: active}}
      Opportunity:
        id: "OPP-{n}"
        path: "docs/discovery/opportunities/{id}-{slug}.md"
        traits: {lifecycle: {statuses: [open, pursuing], initial: open}}
      Solution:
        id: "SOL-{n}"
        path: "docs/discovery/solutions/{id}-{slug}.md"
    links:
      serves: {from: Opportunity, to: [Outcome, Opportunity]}
      addresses: {from: Solution, to: Opportunity}
    views:
      - id: tree
        title: Opportunity solution tree
        output: docs/generated/tree.md
        render: tree
        select: {type: Outcome}
        levels: [{incoming: serves}, {incoming: addresses}]
      - id: solutions
        title: Solutions and what they address
        output: docs/generated/solutions.md
        render: tree
        select: {type: Solution}
        levels: [{link: addresses}, {link: serves}]
"""


def doc(doc_id, doc_type, title, extra=""):
    return f"---\nid: {doc_id}\ntype: {doc_type}\ntitle: {title}\n{extra}---\n"


def world(project):
    cfg = load_config(project.root)
    assert cfg.errors == [], [d.message for d in cfg.errors]
    return cfg, build_graph(cfg)


def rendered(project, qid):
    cfg, graph = world(project)
    return render(cfg, graph, next(v for v in cfg.views if v.qid == qid))


def test_table_view(project):
    standard(project)
    project.write("docs/adr/ADR-010-j.md", adr("ADR-010", "proposed"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002").replace("title: Decision ADR-002", "title: Pipes | and more"))
    assert rendered(project, "adr/decision-log") == (
        "<!-- bondstone:generated view=adr/decision-log; do not edit, run `bondstone gen` -->\n"
        "# Decision log\n"
        "\n"
        "| Id | Title | Status | Date | Owner |\n"
        "|---|---|---|---|---|\n"
        "| [ADR-002](../adr/ADR-002-b.md) | Pipes \\| and more | accepted | 2026-01-01 | me |\n"
        "| [ADR-010](../adr/ADR-010-j.md) | Decision ADR-010 | proposed | 2026-01-01 | me |\n"
    )


def test_table_of_items_with_description_sort_and_special_columns(project):
    standard(project, views=[
        {"id": "requirements", "title": "Requirements", "description": "Every requirement.",
         "output": "REQUIREMENTS.md", "select": {"type": "capability:Requirement"},
         "columns": ["id", "title", "parent", "status", "type", "path"], "sort": ["status", "title"]},
        {"id": "default-columns", "output": "docs/generated/caps.md", "select": {"role": "living-spec"}},
        {"id": "empty", "output": "docs/generated/empty.md", "select": {"type": "adr:Decision"}},
    ])
    reqs = ("### REQ-AA-001: Zebra\n\nSHALL.\n\n#### Scenario: s\n\n"
            "### REQ-AA-002: Apple pie\n\nStatus: planned\n\nSHALL.\n\n#### Scenario: s\n\n"
            "### REQ-AA-003: Apple\n\nSHALL.\n\n#### Scenario: s\n")
    project.write("docs/capabilities/a.md", capability(requirements=reqs))
    assert rendered(project, "profile/requirements") == (
        "<!-- bondstone:generated view=profile/requirements; do not edit, run `bondstone gen` -->\n"
        "# Requirements\n"
        "\n"
        "Every requirement.\n"
        "\n"
        "| Id | Title | Parent | Status | Type | Path |\n"
        "|---|---|---|---|---|---|\n"
        "| [REQ-AA-003](docs/capabilities/a.md#req-aa-003-apple) | Apple | CAP-a | active | capability:Requirement | docs/capabilities/a.md |\n"
        "| [REQ-AA-001](docs/capabilities/a.md#req-aa-001-zebra) | Zebra | CAP-a | active | capability:Requirement | docs/capabilities/a.md |\n"
        "| [REQ-AA-002](docs/capabilities/a.md#req-aa-002-apple-pie) | Apple pie | CAP-a | planned | capability:Requirement | docs/capabilities/a.md |\n"
    )
    assert rendered(project, "profile/default-columns").splitlines()[3:] == [
        "| Id | Title | Status |", "|---|---|---|", "| [CAP-a](../capabilities/a.md) | Capability CAP-a | active |"]
    assert rendered(project, "profile/empty") == (
        "<!-- bondstone:generated view=profile/empty; do not edit, run `bondstone gen` -->\n"
        "# profile/empty\n\n_No entries._\n")


def ost(project):
    project.pack("ost", OST).profile(packs=["ost@1"])
    project.write("docs/discovery/outcomes/OUT-1-r.md", doc("OUT-1", "ost:Outcome", "Retention", "status: active\n"))
    project.write("docs/discovery/outcomes/OUT-2-s.md", doc("OUT-2", "ost:Outcome", "Signups", "status: achieved\n"))
    project.write("docs/discovery/opportunities/OPP-10-b.md",
                  doc("OPP-10", "ost:Opportunity", "Streaks", "status: open\nserves: OUT-1\n"))
    project.write("docs/discovery/opportunities/OPP-2-a.md",
                  doc("OPP-2", "ost:Opportunity", "Forgetting", "status: pursuing\nserves: OUT-1\n"))
    project.write("docs/discovery/solutions/SOL-1-x.md",
                  doc("SOL-1", "ost:Solution", "Reminders", "addresses: [OPP-2, OPP-10, OPP-2, OPP-404]\n"))
    return project


def test_tree_view_walks_incoming_links_level_by_level(project):
    assert rendered(ost(project), "ost/tree") == (
        "<!-- bondstone:generated view=ost/tree; do not edit, run `bondstone gen` -->\n"
        "# Opportunity solution tree\n"
        "\n"
        "- [OUT-1](../discovery/outcomes/OUT-1-r.md) Retention _(active)_\n"
        "  - [OPP-2](../discovery/opportunities/OPP-2-a.md) Forgetting _(pursuing)_\n"
        "    - [SOL-1](../discovery/solutions/SOL-1-x.md) Reminders\n"
        "  - [OPP-10](../discovery/opportunities/OPP-10-b.md) Streaks _(open)_\n"
        "    - [SOL-1](../discovery/solutions/SOL-1-x.md) Reminders\n"
        "- [OUT-2](../discovery/outcomes/OUT-2-s.md) Signups _(achieved)_\n"
    )


def test_tree_view_walks_outgoing_links_and_skips_duplicates_and_broken_links(project):
    assert rendered(ost(project), "ost/solutions").splitlines()[3:] == [
        "- [SOL-1](../discovery/solutions/SOL-1-x.md) Reminders",
        "  - [OPP-2](../discovery/opportunities/OPP-2-a.md) Forgetting _(pursuing)_",
        "    - [OUT-1](../discovery/outcomes/OUT-1-r.md) Retention _(active)_",
        "  - [OPP-10](../discovery/opportunities/OPP-10-b.md) Streaks _(open)_",
        "    - [OUT-1](../discovery/outcomes/OUT-1-r.md) Retention _(active)_",
    ]


def test_gen_writes_stale_views_and_is_idempotent(project):
    ost(project)
    cfg, graph = world(project)
    assert [view.qid for view, _ in stale_views(cfg, graph)] == ["ost/tree", "ost/solutions"]
    assert generate(cfg, graph) == ["docs/generated/tree.md", "docs/generated/solutions.md"]
    before = {p: project.read(p) for p in ("docs/generated/tree.md", "docs/generated/solutions.md")}
    cfg, graph = world(project)  # generated files are not documents
    assert graph.diagnostics == [] and stale_views(cfg, graph) == []
    assert generate(cfg, graph) == []
    assert {p: project.read(p) for p in before} == before


def stale_paths(project):
    return [d.path for d in check(project) if d.rule == "bondstone/view-stale"]


def test_check_reports_stale_views_with_a_fix(project):
    ost(project)
    stale = [d for d in check(project) if d.rule == "bondstone/view-stale"]
    assert [d.to_dict() for d in stale] == [
        {"rule": "bondstone/view-stale", "severity": "error", "path": "docs/generated/solutions.md",
         "message": "generated view ost/solutions is out of date", "hint": "Run `bondstone gen`.",
         "fix": {"command": ["bondstone", "gen"]}},
        {"rule": "bondstone/view-stale", "severity": "error", "path": "docs/generated/tree.md",
         "message": "generated view ost/tree is out of date", "hint": "Run `bondstone gen`.",
         "fix": {"command": ["bondstone", "gen"]}},
    ]
    generate(*world(project))
    assert stale_paths(project) == []
    # a document change makes the view stale again; so does a hand edit of the view
    project.write("docs/discovery/outcomes/OUT-2-s.md", doc("OUT-2", "ost:Outcome", "More signups", "status: achieved\n"))
    assert stale_paths(project) == ["docs/generated/tree.md"]
    generate(*world(project))
    project.write("docs/generated/solutions.md", project.read("docs/generated/solutions.md") + "edited by hand\n")
    assert stale_paths(project) == ["docs/generated/solutions.md"]
