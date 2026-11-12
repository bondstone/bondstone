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


# ----------------------------------------------------------------------- link columns and matrices

HEADER = "<!-- bondstone:generated view=profile/{id}; do not edit, run `bondstone gen` -->\n# {title}\n\n"


def linked(project, **profile):
    """Three decisions and three capabilities; CAP-a is constrained by two decisions, CAP-c by none."""
    standard(project, **profile)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="supersedes: ADR-001\n"))
    project.write("docs/adr/ADR-010-j.md", adr("ADR-010", "proposed"))
    project.write("docs/capabilities/a.md", capability("CAP-a", "AA", extra="constrained_by: [ADR-010, ADR-002]\n"))
    project.write("docs/capabilities/b.md", capability("CAP-b", "BB", extra="constrained_by: [ADR-002]\ndepends_on: [CAP-a]\n"))
    project.write("docs/capabilities/c.md", capability("CAP-c", "CC", extra="depends_on: [CAP-b]\n"))
    return project


def test_table_columns_show_outgoing_and_incoming_links_as_linked_ids(project):
    view = {"id": "usage", "title": "Decisions", "output": "docs/generated/usage.md",
            "select": {"type": "adr:Decision"}, "columns": ["id", "status", "<-constrained_by", "supersedes"]}
    linked(project, views=[view])
    assert rendered(project, "profile/usage") == HEADER.format(id="usage", title="Decisions") + (
        "| Id | Status | ← Constrained by | Supersedes |\n"
        "|---|---|---|---|\n"
        "| [ADR-001](../adr/ADR-001-a.md) | accepted |  |  |\n"
        "| [ADR-002](../adr/ADR-002-b.md) | accepted | [CAP-a](../capabilities/a.md), [CAP-b](../capabilities/b.md) "
        "| [ADR-001](../adr/ADR-001-a.md) |\n"
        "| [ADR-010](../adr/ADR-010-j.md) | proposed | [CAP-a](../capabilities/a.md) |  |\n"
    )


def test_an_outgoing_link_column_keeps_the_written_order_and_shows_broken_targets_as_text(project):
    view = {"id": "caps", "title": "Capabilities", "output": "caps.md", "select": {"type": "capability:Capability"},
            "columns": ["id", "adr-capability:constrained_by", "<-capability:depends_on"]}
    linked(project, views=[view])
    project.edit("docs/capabilities/b.md", "constrained_by: [ADR-002]", "constrained_by: [ADR-002, ADR-404, ADR-002]")
    assert rendered(project, "profile/caps") == HEADER.format(id="caps", title="Capabilities") + (
        "| Id | Constrained by | ← Depends on |\n"
        "|---|---|---|\n"
        "| [CAP-a](docs/capabilities/a.md) | [ADR-010](docs/adr/ADR-010-j.md), [ADR-002](docs/adr/ADR-002-b.md) "
        "| [CAP-b](docs/capabilities/b.md) |\n"
        "| [CAP-b](docs/capabilities/b.md) | [ADR-002](docs/adr/ADR-002-b.md), ADR-404 | [CAP-c](docs/capabilities/c.md) |\n"
        "| [CAP-c](docs/capabilities/c.md) |  |  |\n"
    )


def test_a_link_column_of_a_type_that_cannot_have_the_link_is_empty(project):
    view = {"id": "all", "title": "All", "output": "all.md", "select": {"type": ["adr:Decision", "capability:Capability"]},
            "columns": ["id", "depends_on"], "sort": "type"}
    linked(project, views=[view])
    lines = rendered(project, "profile/all").splitlines()
    assert lines[3] == "| Id | Depends on |"
    assert lines[5] == "| [ADR-001](docs/adr/ADR-001-a.md) |  |"
    assert lines[-1] == "| [CAP-c](docs/capabilities/c.md) | [CAP-b](docs/capabilities/b.md) |"


MATRIX = {"id": "applied", "title": "Applied", "output": "docs/generated/applied.md", "render": "matrix",
          "rows": {"type": "capability:Capability"}, "cols": {"type": "adr:Decision"}, "via": ["constrained_by"]}


def test_matrix_marks_where_a_link_connects_a_row_and_a_column(project):
    linked(project, views=[MATRIX])
    assert rendered(project, "profile/applied") == HEADER.format(id="applied", title="Applied") + (
        "| | [ADR-001](../adr/ADR-001-a.md) | [ADR-002](../adr/ADR-002-b.md) | [ADR-010](../adr/ADR-010-j.md) |\n"
        "|---|:---:|:---:|:---:|\n"
        "| [CAP-a](../capabilities/a.md) Capability CAP-a |  | ✓ | ✓ |\n"
        "| [CAP-b](../capabilities/b.md) Capability CAP-b |  | ✓ |  |\n"
        "| [CAP-c](../capabilities/c.md) Capability CAP-c |  |  |  |\n"
    )


def test_matrix_follows_a_path_of_links_forwards_and_backwards(project):
    """Decisions against the capabilities that depend on a capability they constrain."""
    path = {**MATRIX, "rows": {"type": "adr:Decision", "status": "accepted"}, "cols": {"type": "capability:Capability"},
            "via": ["<-constrained_by", "<-depends_on"]}
    linked(project, views=[path])
    assert rendered(project, "profile/applied").splitlines()[3:] == [
        "| | [CAP-a](../capabilities/a.md) | [CAP-b](../capabilities/b.md) | [CAP-c](../capabilities/c.md) |",
        "|---|:---:|:---:|:---:|",
        "| [ADR-001](../adr/ADR-001-a.md) Decision ADR-001 |  |  |  |",
        "| [ADR-002](../adr/ADR-002-b.md) Decision ADR-002 |  | ✓ | ✓ |",  # CAP-a -> CAP-b, CAP-b -> CAP-c
    ]
    back = {**MATRIX, "rows": {"type": "adr:Decision"}, "cols": {"type": "adr:Decision"}, "via": ["supersedes"]}
    linked(project, views=[back])
    assert rendered(project, "profile/applied").splitlines()[6] == (
        "| [ADR-002](../adr/ADR-002-b.md) Decision ADR-002 | ✓ |  |  |")


def test_matrix_without_rows_or_columns(project):
    linked(project, views=[{**MATRIX, "cols": {"type": "adr:Decision", "status": "rejected"}}])
    assert rendered(project, "profile/applied") == HEADER.format(id="applied", title="Applied") + "_No entries._\n"


def test_a_matrix_is_generated_and_goes_stale_like_any_view(project):
    linked(project, views=[MATRIX], overrides={"bondstone/view-stale": "error"})
    cfg, graph = world(project)
    assert "docs/generated/applied.md" in generate(cfg, graph)
    assert [d.rule for d in check(project) if d.rule == "bondstone/view-stale"] == []
    project.edit("docs/capabilities/c.md", "depends_on: [CAP-b]", "depends_on: [CAP-b]\nconstrained_by: [ADR-001]")
    assert [(d.rule, d.path) for d in check(project) if d.rule == "bondstone/view-stale"] == [
        ("bondstone/view-stale", "docs/generated/applied.md")]


def test_matrix_and_link_columns_are_validated(project):
    def messages(view):
        standard(project, views=[view])
        return [d.message for d in load_config(project.root).errors]

    assert messages({**MATRIX, "via": ["nope", "<-missing"], "rows": {"type": "adr:Nope"}}) == [
        "profile/applied: unknown type 'adr:Nope'",
        "profile/applied: unknown link 'nope'", "profile/applied: unknown link 'missing'"]
    assert messages({key: value for key, value in MATRIX.items() if key not in ("cols", "via")}) == [
        "profile/applied: a matrix needs `rows`, `cols` and `via`"]
    assert messages({**MATRIX, "render": "table"}) == [
        "profile/applied: `rows`, `cols`, `via` only apply to `render: matrix`"]
    assert messages({"id": "t", "output": "t.md", "via": ["supersedes"]}) == [
        "profile/t: `via` only applies to `render: matrix`"]
    assert messages({"id": "t", "output": "t.md", "columns": ["id", "<-nope", "anything"]}) == [
        "profile/t: unknown link 'nope'"]
    assert messages({**MATRIX, "via": []}) == ["views[0].via: [] should be non-empty"]
