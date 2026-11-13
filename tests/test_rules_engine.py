"""Engine rules: structure, links, traits and code tags."""

from conftest import ADR_BODY, adr, capability, check, standard


def by_rule(project, rule):
    return [d for d in check(project) if d.rule == rule]


def test_valid_documents_are_clean(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    project.write("docs/capabilities/a.md", capability(extra="constrained_by: [ADR-001]\n"))
    assert check(project) == []


# --------------------------------------------------------------------------- ids


def test_id_missing_format_and_duplicate(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    project.write("docs/adr/ADR-001-copy.md", adr("ADR-001"))
    project.write("docs/adr/ADR-3-c.md", adr("ADR-3"))
    project.write("docs/adr/none.md", adr("X").replace("id: X\n", ""))
    found = {(d.rule, d.path, d.line): d for d in check(project) if d.rule.startswith("bondstone/id-")}
    assert sorted(found) == [
        ("bondstone/id-duplicate", "docs/adr/ADR-001-copy.md", 2),
        ("bondstone/id-format", "docs/adr/ADR-3-c.md", 2),
        ("bondstone/id-missing", "docs/adr/none.md", 1),
    ]
    assert found[("bondstone/id-format", "docs/adr/ADR-3-c.md", 2)].message == (
        "id 'ADR-3' does not match the id template 'ADR-{n:03d}'")
    assert found[("bondstone/id-duplicate", "docs/adr/ADR-001-copy.md", 2)].message == (
        "id 'ADR-001' is already used in docs/adr/ADR-001-a.md:1")
    assert found[("bondstone/id-missing", "docs/adr/none.md", 1)].hint == "Add `id:` following the template 'ADR-{n:03d}'."


def test_item_ids_use_the_parent_field(project):
    standard(project)
    reqs = ("### REQ-AA-001: Good\n\nSHALL.\n\n#### Scenario: s\n\n"
            "### REQ-BB-002: Other capability's code\n\nSHALL.\n\n#### Scenario: s\n\n"
            "### REQ-AA-3: Too short\n\nSHALL.\n\n#### Scenario: s\n\n"
            "### REQ-AA-001: Duplicate\n\nSHALL.\n\n#### Scenario: s\n")
    project.write("docs/capabilities/a.md", capability(requirements=reqs))
    found = [(d.rule, d.line, d.node, d.message) for d in check(project) if d.rule.startswith("bondstone/id-")]
    assert found == [
        ("bondstone/id-format", 21, "REQ-BB-002",
         "id 'REQ-BB-002' does not match the id template 'REQ-{code}-{n:03d}' (code: AA)"),
        ("bondstone/id-format", 27, "REQ-AA-3",
         "id 'REQ-AA-3' does not match the id template 'REQ-{code}-{n:03d}' (code: AA)"),
        ("bondstone/id-duplicate", 33, "REQ-AA-001",
         "id 'REQ-AA-001' is already used in docs/capabilities/a.md:15"),
    ]


def test_id_pattern_overrides_the_derived_pattern(project):
    project.pack("p", """
        id: p
        version: 1.0.0
        types:
          Note: {id: "N-{n}", id_pattern: "^N-[a-z]+$", path: "notes/{id}.md"}
    """).profile(packs=["p"])
    project.write("notes/N-abc.md", "---\nid: N-abc\ntype: p:Note\ntitle: A\n---\n")
    project.write("notes/N-12.md", "---\nid: N-12\ntype: p:Note\ntitle: B\n---\n")
    assert [d.message for d in check(project)] == ["id 'N-12' does not match ^N-[a-z]+$"]


def test_the_path_carries_the_id_when_the_path_template_names_it(project):
    project.pack("p", """
        id: p
        version: 1.0.0
        types:
          Note: {id: "N-{n}", path: "notes/{id}-{slug}.md"}
          Feature: {id: "{n:03d}-{slug}", path: "specs/{id}/spec.md"}
          Topic: {id: "T-{slug}", path: "topics/{slug}.md"}
    """).profile(packs=["p"])
    project.write("notes/N-1-first.md", "---\nid: N-1\ntype: p:Note\n---\n")
    project.write("notes/N-2.md", "---\nid: N-2\ntype: p:Note\n---\n")
    project.write("notes/N-30-third.md", "---\nid: N-3\ntype: p:Note\n---\n")
    project.write("specs/001-login/spec.md", "---\nid: 001-login\ntype: p:Feature\n---\n")
    project.write("specs/002-logout/spec.md", "---\nid: 002-sign-out\ntype: p:Feature\n---\n")
    project.write("topics/anything.md", "---\nid: T-other\ntype: p:Topic\n---\n")  # no {id} in the path
    found = [(d.rule, d.path, d.line, d.message) for d in check(project)]
    assert found == [
        ("bondstone/id-path", "notes/N-2.md", 2, "id 'N-2' does not match the path; expected notes/N-2-{slug}.md"),
        ("bondstone/id-path", "notes/N-30-third.md", 2,
         "id 'N-3' does not match the path; expected notes/N-3-{slug}.md"),
        ("bondstone/id-path", "specs/002-logout/spec.md", 2,
         "id '002-sign-out' does not match the path; expected specs/002-sign-out/spec.md"),
    ]


# --------------------------------------------------------------------------- fields and sections


def test_field_missing_unknown_and_invalid(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md",
                  "---\nid: ADR-001\ntype: adr:Decision\ntitle: Ab\nstatus: approved\ndate: yesterday\n"
                  "colour: red\nsupersede: ADR-000\ndeciders: me\n---\n" + ADR_BODY)
    found = [(d.rule, d.line, d.message) for d in check(project)]
    assert found == [
        ("bondstone/field-missing", 1, "missing required field 'owner'"),
        ("bondstone/field-invalid", 4, "field 'title': 'Ab' is too short"),
        ("bondstone/field-invalid", 5,
         "field 'status': 'approved' is not one of ['proposed', 'accepted', 'rejected', 'deprecated', 'superseded']"),
        ("bondstone/field-invalid", 6, "field 'date': 'yesterday' is not a 'date'"),
        ("bondstone/field-unknown", 7, "unknown key(s) colour, supersede for adr:Decision"),
        ("bondstone/field-invalid", 9, "field 'deciders': 'me' is not of type 'array'"),
    ]
    unknown = by_rule(project, "bondstone/field-unknown")[0]
    assert unknown.hint == "Fields: date, deciders, owner, status, title. Links: supersedes."


def test_item_status_must_be_a_lifecycle_status(project):
    standard(project)
    reqs = "### REQ-AA-001: Thing\n\nStatus: someday\n\nSHALL.\n\n#### Scenario: s\n"
    project.write("docs/capabilities/a.md", capability(requirements=reqs))
    assert [(d.rule, d.line, d.node, d.message) for d in check(project)] == [
        ("bondstone/field-invalid", 17, "REQ-AA-001", "status 'someday' is not one of planned, active, removed")]


def test_section_missing(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", body="## Context\n\n### Decision\n\n## Alternatives\n"))
    found = by_rule(project, "bondstone/section-missing")
    assert [(d.message, d.hint) for d in found] == [
        ("adr:Decision requires a 'Consequences' section", "Add a heading '## Consequences'.")]


def test_todo_left_is_a_warning_in_the_initial_status_and_ignores_code(project):
    standard(project)
    body = ADR_BODY + "\nUse `<!-- todo: ... -->` markers.\n\n```md\n<!-- todo: x -->\n```\n"
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", body=body))
    assert by_rule(project, "bondstone/todo-left") == []
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", body=body + "\n<!-- TODO: y -->\n"))
    [diag] = by_rule(project, "bondstone/todo-left")
    assert (diag.severity, diag.line, diag.node) == ("error", 32, "ADR-001")
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed", body=body + "\n<!-- todo: y -->\n"))
    assert [(d.rule, d.severity) for d in check(project)] == [("bondstone/todo-left", "warn")]


# --------------------------------------------------------------------------- links


def test_link_broken_type_self_and_max(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "superseded"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="supersedes: [ADR-001, ADR-009]\n"))
    project.write("docs/adr/ADR-003-c.md", adr("ADR-003", "superseded", extra="supersedes: ADR-003\n"))
    project.write("docs/capabilities/a.md", capability(extra="constrained_by: [CAP-a, ADR-002, ADR-003]\ndepends_on: [REQ-AA-001]\n"))
    found = [(d.rule, d.path, d.line, d.message) for d in check(project)
             if d.rule.startswith("bondstone/link-")]
    assert found == [
        ("bondstone/link-broken", "docs/adr/ADR-002-b.md", 8, "supersedes -> 'ADR-009': no such document"),
        ("bondstone/link-max", "docs/adr/ADR-002-b.md", 8, "at most 1 'supersedes' link(s) allowed; has 2"),
        ("bondstone/link-self", "docs/adr/ADR-003-c.md", 8, "supersedes points to itself"),
        ("bondstone/link-type", "docs/capabilities/a.md", 8,
         "constrained_by -> CAP-a is a capability:Capability; expected adr:Decision"),
        ("bondstone/link-type", "docs/capabilities/a.md", 9,
         "depends_on -> REQ-AA-001 is a capability:Requirement; expected capability:Capability"),
    ]


def test_link_min(project):
    project.pack("ost", """
        id: ost
        version: 1.0.0
        types:
          Outcome: {id: "OUT-{n}", path: "docs/outcomes/{id}.md"}
          Opportunity: {id: "OPP-{n}", path: "docs/opportunities/{id}.md"}
        links:
          serves: {from: Opportunity, to: [Outcome, Opportunity], min: 1, max: 1}
    """).profile(packs=["ost"])
    project.write("docs/opportunities/OPP-1.md", "---\nid: OPP-1\ntype: ost:Opportunity\ntitle: Need\n---\n")
    [diag] = check(project)
    assert (diag.rule, diag.line, diag.node) == ("bondstone/link-min", 1, "OPP-1")
    assert diag.message == "needs at least 1 'serves' link(s) to ost:Outcome, ost:Opportunity; has 0"
    assert diag.hint == "Add `serves: [<id>]` to the frontmatter."


# --------------------------------------------------------------------------- supersedable


def test_supersede_status_multiple_orphan_and_cycle(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="supersedes: ADR-001\n"))
    project.write("docs/adr/ADR-003-c.md", adr("ADR-003", extra="supersedes: ADR-001\n"))
    project.write("docs/adr/ADR-004-d.md", adr("ADR-004", "superseded"))
    project.write("docs/adr/ADR-005-e.md", adr("ADR-005", "superseded", extra="supersedes: ADR-006\n"))
    project.write("docs/adr/ADR-006-f.md", adr("ADR-006", "superseded", extra="supersedes: ADR-005\n"))
    found = [(d.rule, d.severity, d.node, d.path, d.line) for d in check(project)
             if d.rule.startswith("bondstone/supersede-")]
    assert found == [
        ("bondstone/supersede-multiple", "error", "ADR-001", "docs/adr/ADR-001-a.md", 1),
        ("bondstone/supersede-status", "error", "ADR-001", "docs/adr/ADR-001-a.md", 5),
        ("bondstone/supersede-status", "error", "ADR-001", "docs/adr/ADR-001-a.md", 5),
        ("bondstone/supersede-orphan", "warn", "ADR-004", "docs/adr/ADR-004-d.md", 5),
        ("bondstone/supersede-cycle", "error", "ADR-005", "docs/adr/ADR-005-e.md", 1),
        ("bondstone/supersede-cycle", "error", "ADR-006", "docs/adr/ADR-006-f.md", 1),
    ]
    status = by_rule(project, "bondstone/supersede-status")[0]
    assert status.message == "ADR-002 supersedes ADR-001, but ADR-001 has status 'accepted'"
    assert status.hint == "Run `bondstone status ADR-001 superseded`."
    assert status.fix == {"command": ["bondstone", "status", "ADR-001", "superseded"]}


def test_supersede_status_has_no_fix_command_when_the_lifecycle_forbids_the_step(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="supersedes: ADR-001\n"))
    status = by_rule(project, "bondstone/supersede-status")[0]
    assert status.fix is None
    assert status.hint == ("Set `status: superseded` in docs/adr/ADR-001-a.md; "
                           "its lifecycle does not allow that step from 'proposed'.")


def test_valid_supersession(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "superseded"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "superseded", extra="supersedes: ADR-001\n"))
    project.write("docs/adr/ADR-003-c.md", adr("ADR-003", extra="supersedes: ADR-002\n"))
    assert [d.rule for d in check(project)] == ["adr-capability/accepted-decision-is-applied"]


# --------------------------------------------------------------------------- code tags and coverage (D9)

REQS = ("### REQ-AA-001: Active and tagged\n\nSHALL.\n\n#### Scenario: s\n\n"
        "### REQ-AA-002: Active, not tagged\n\nSHALL.\n\n#### Scenario: s\n\n"
        "### REQ-AA-003: Planned, not tagged\n\nStatus: planned\n\nSHALL.\n\n#### Scenario: s\n\n"
        "### REQ-AA-004: Planned and tagged\n\nStatus: planned\n\nSHALL.\n\n#### Scenario: s\n\n"
        "### REQ-AA-005: Removed, tag still there\n\nStatus: removed\n\nSHALL.\n\n#### Scenario: s\n\n"
        "### REQ-AA-006: Removed, tag gone\n\nStatus: removed\n\nSHALL.\n\n#### Scenario: s\n")


def test_coverage_depends_on_status(project):
    standard(project, code={"include": ["src/*.py"]})
    project.write("docs/capabilities/a.md", capability(requirements=REQS))
    project.write("src/a.py", "# bondstone: REQ-AA-001\nx = 1\n# bondstone: REQ-AA-004, REQ-AA-005\ny = 2\n")
    found = [(d.rule, d.severity, d.path, d.line, d.node) for d in check(project)]
    assert found == [
        ("bondstone/code-coverage", "warn", "docs/capabilities/a.md", 21, "REQ-AA-002"),
        ("bondstone/tag-retired", "warn", "src/a.py", 3, "REQ-AA-005"),
    ]
    coverage, retired = check(project)
    assert coverage.message == "REQ-AA-002 is not referenced from code"
    assert coverage.hint == "Add a `bondstone: REQ-AA-002` comment where it is implemented."
    assert retired.message == "code is tagged with REQ-AA-005, which has status 'removed'"


def test_coverage_severity_comes_from_the_trait_and_without_when_every_status_counts(project):
    project.pack("p", """
        id: p
        version: 1.0.0
        types:
          Command:
            id: "CLI-{slug}"
            path: "docs/cli/{slug}.md"
            traits: {code-traceable: {coverage: error}}
          Quiet:
            id: "Q-{n}"
            path: "docs/quiet/{id}.md"
            traits: {code-traceable: {coverage: ignore}}
    """).profile(packs=["p"], code={"include": ["src/*.py"]})
    project.write("docs/cli/check.md", "---\nid: CLI-check\ntype: p:Command\ntitle: check\n---\n")
    project.write("docs/quiet/Q-1.md", "---\nid: Q-1\ntype: p:Quiet\ntitle: quiet\n---\n")
    assert [(d.rule, d.severity, d.node) for d in check(project)] == [("bondstone/code-coverage", "error", "CLI-check")]
    project.write("src/cli.py", "# bondstone: CLI-check\n")
    assert check(project) == []


def test_unknown_and_untraceable_tags_are_errors_whatever_the_status(project):
    standard(project, code={"include": ["src/*.py"]})
    project.write("docs/capabilities/a.md", capability())
    project.write("src/a.py", "# bondstone: REQ-AA-001\n# bondstone: REQ-ZZ-009\n# bondstone: CAP-a\n")
    assert [(d.rule, d.severity, d.line, d.message) for d in check(project)] == [
        ("bondstone/code-ref-unknown", "error", 2, "code references unknown id 'REQ-ZZ-009'"),
        ("bondstone/code-ref-not-traceable", "error", 3,
         "CAP-a is capability:Capability, a type that is not code-traceable"),
    ]


def test_without_code_globs_nothing_is_reported_about_coverage(project):
    standard(project)
    project.write("docs/capabilities/a.md", capability())
    assert check(project) == []
