"""Node rules, their clauses, and existence rules."""

from conftest import adr, capability, check, standard


def violations(project, rule):
    return [(d.node or d.path, d.message) for d in check(project) if d.rule == rule]


def rule(rule_id, when, *require, **extra):
    return {"id": rule_id, "description": f"Rule {rule_id}.", "when": when, "require": list(require), **extra}


def test_rule_diagnostic_carries_location_severity_hint_and_fix(project):
    standard(project, rules=[rule("has-result", {"type": "adr:Decision"}, {"section": "Result"}, severity="warn",
                                  hint="Add a Result section to {id}.",
                                  fix={"command": ["bondstone", "status", "{id}", "proposed"]})])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    [diag] = [d for d in check(project) if d.rule == "profile/has-result"]
    assert diag.to_dict() == {
        "rule": "profile/has-result", "severity": "warn", "path": "docs/adr/ADR-001-a.md", "line": 1,
        "node": "ADR-001", "message": "Rule has-result. (missing section 'Result')",
        "hint": "Add a Result section to ADR-001.",
        "fix": {"command": ["bondstone", "status", "ADR-001", "proposed"]},
    }


def test_rule_without_description_uses_its_id(project):
    standard(project, rules=[{"id": "bare", "when": {"type": "adr:Decision"}, "require": [{"field": "deciders"}]}])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    assert violations(project, "profile/bare") == [("ADR-001", "profile/bare (field 'deciders' is empty)")]


def test_link_clauses(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "superseded"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="supersedes: ADR-001\n"))
    project.write("docs/capabilities/a.md", capability(extra="constrained_by: [ADR-001, ADR-002]\n"))
    project.write("docs/capabilities/b.md", capability("CAP-b", "BB"))
    # `all`: every target must match; no links at all is fine
    assert violations(project, "adr-capability/constrained-by-live-decision") == [
        ("CAP-a", "Capabilities are constrained only by proposed or accepted decisions. "
                  "('constrained_by' targets not allowed: ADR-001)")]

    standard(project, rules=[
        rule("two-live", {"role": "living-spec"},
             {"link": "constrained_by", "to": {"status": "accepted"}, "min": 2}),
        rule("any-link", {"type": "capability:Capability"}, {"link": "constrained_by"}),
    ])
    assert violations(project, "profile/two-live") == [
        ("CAP-a", "Rule two-live. (needs 2 'constrained_by' link(s) to status=accepted, has 1)"),
        ("CAP-b", "Rule two-live. (needs 2 'constrained_by' link(s) to status=accepted, has 0)"),
    ]
    assert violations(project, "profile/any-link") == [
        ("CAP-b", "Rule any-link. (needs 1 'constrained_by' link(s), has 0)")]


def test_incoming_clause(project):
    standard(project, rules=[rule("applied-by-active", {"type": "adr:Decision", "status": "accepted"},
                                  {"incoming": "constrained_by", "from": {"status": "draft"}, "min": 1})])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002"))
    project.write("docs/capabilities/a.md", capability(extra="constrained_by: [ADR-001]\n"))
    assert violations(project, "adr-capability/accepted-decision-is-applied") == [
        ("ADR-002", "An accepted decision constrains at least one capability. "
                    "(needs 1 incoming 'constrained_by' link(s), has 0)")]
    assert violations(project, "profile/applied-by-active") == [
        ("ADR-001", "Rule applied-by-active. (needs 1 incoming 'constrained_by' link(s) from status=draft, has 0)"),
        ("ADR-002", "Rule applied-by-active. (needs 1 incoming 'constrained_by' link(s) from status=draft, has 0)"),
    ]


def test_field_section_and_contains_clauses(project):
    standard(project, rules=[
        rule("has-deciders", {"type": "adr:Decision"}, {"field": "deciders"}),
        rule("has-outcome", {"type": "adr:Decision"}, {"section": "Outcome"}),
        rule("mentions-cost", {"type": "adr:Decision"}, {"contains": "(?i)\\bcost\\b"}),
    ])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", extra="deciders: [me]\n") + "\n## Outcome\n\nCost is low.\n")
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="deciders: []\n"))
    project.write("docs/adr/ADR-003-c.md", adr("ADR-003"))
    assert violations(project, "profile/has-deciders") == [
        ("ADR-002", "Rule has-deciders. (field 'deciders' is empty)"),
        ("ADR-003", "Rule has-deciders. (field 'deciders' is empty)")]
    assert [node for node, _ in violations(project, "profile/has-outcome")] == ["ADR-002", "ADR-003"]
    assert violations(project, "profile/mentions-cost")[0] == (
        "ADR-002", "Rule mentions-cost. (body must match /(?i)\\bcost\\b/)")


def test_rules_apply_to_items_with_their_own_body(project):
    standard(project)
    reqs = ("### REQ-AA-001: With scenario\n\nSHALL.\n\n#### Scenario: s\n\n- ok\n\n"
            "### REQ-AA-002: Without\n\nSHALL.\n")
    project.write("docs/capabilities/a.md", capability(requirements=reqs))
    [diag] = [d for d in check(project) if d.rule == "capability/requirement-has-scenario"]
    assert (diag.node, diag.line, diag.path) == ("REQ-AA-002", 23, "docs/capabilities/a.md")


def test_items_clause(project):
    standard(project, rules=[rule("has-two-requirements", {"type": "capability:Capability", "status": "active"},
                                  {"items": {"type": "capability:Requirement", "min": 2}}),
                             rule("has-requirements", {"type": "capability:Capability"},
                                  {"items": {"type": "capability:Requirement"}})])
    project.write("docs/capabilities/a.md", capability())
    project.write("docs/capabilities/b.md", capability("CAP-b", "BB", requirements="None yet.\n"))
    assert violations(project, "profile/has-two-requirements") == [
        ("CAP-a", "Rule has-two-requirements. (needs 2 capability:Requirement item(s), has 1)"),
        ("CAP-b", "Rule has-two-requirements. (needs 2 capability:Requirement item(s), has 0)")]
    assert [node for node, _ in violations(project, "profile/has-requirements")] == ["CAP-b"]


def test_covered_clause_and_selector(project):
    reqs = ("### REQ-AA-001: Tagged\n\nSHALL.\n\n#### Scenario: s\n\n"
            "### REQ-AA-002: Untagged\n\nSHALL.\n\n#### Scenario: s\n")
    standard(project, code={"include": ["src/*.py"]}, overrides={"bondstone/code-coverage": "ignore"}, rules=[
        rule("active-is-implemented", {"type": "capability:Requirement", "status": "active"}, {"covered": True}),
        rule("uncovered-has-plan", {"type": "capability:Requirement", "covered": False}, {"section": "Plan"}),
        rule("spec-is-not-tagged", {"type": "capability:Requirement", "where": {"title": "Tagged"}}, {"covered": False}),
    ])
    project.write("docs/capabilities/a.md", capability(requirements=reqs))
    project.write("src/a.py", "# bondstone: REQ-AA-001\n")
    assert violations(project, "profile/active-is-implemented") == [
        ("REQ-AA-002", "Rule active-is-implemented. (is not tagged in code)")]
    assert [node for node, _ in violations(project, "profile/uncovered-has-plan")] == ["REQ-AA-002"]
    assert violations(project, "profile/spec-is-not-tagged") == [
        ("REQ-AA-001", "Rule spec-is-not-tagged. (is tagged in code)")]


def test_any_clause(project):
    standard(project, rules=[rule("result-or-outcome", {"type": "adr:Decision"},
                                  {"any": [{"section": "Result"}, {"section": "Outcome"}]})])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed") + "\n## Outcome\n\no\n")
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed"))
    assert violations(project, "profile/result-or-outcome") == [
        ("ADR-002", "Rule result-or-outcome. (needs one of: missing section 'Result'; or missing section 'Outcome')")]


def test_roles_from_bridges_and_the_profile(project):
    standard(project, roles={"spec": ["capability:Capability"], "living-spec": ["adr:Decision"]},
             rules=[rule("specs-have-deciders", {"role": "spec"}, {"field": "deciders"}),
                    rule("living-have-purpose", {"role": "living-spec"}, {"section": "Purpose"})])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    project.write("docs/capabilities/a.md", capability())
    assert [node for node, _ in violations(project, "profile/specs-have-deciders")] == ["CAP-a"]
    assert [node for node, _ in violations(project, "profile/living-have-purpose")] == ["ADR-001"]


def test_diff_rules_are_not_evaluated_without_a_base(project):
    standard(project, rules=[{"id": "code-needs-spec", "on_change": {"paths": ["src/**"]},
                              "require": [{"changed": {"role": "living-spec"}, "traced": True, "min": 1}]}])
    project.write("src/a.py", "x = 1\n")
    assert check(project) == []


DOCS_PACK = """
    id: docs
    version: 1.0.0
    types:
      Readme:
        id: "R-{slug}"
        path: "lib/{slug}/README.md"
        fields:
          name: {type: string}
          version: {type: string}
    rules:
      - id: version-matches
        description: The README states the manifest's version.
        when: {type: Readme}
        require:
          - file_field: {path: "{dir}/manifest.yaml", key: meta.version, equals: version}
          - file_field: {path: "{dir}/manifest.yaml", key: kind, value: pack}
      - id: manifest-has-readme
        description: Every manifest has a README document.
        for_each: {glob: "lib/*/manifest.yaml", document: "{dir}/README.md", type: Readme}
        hint: Add a README.md next to the manifest.
"""


def readme(name, version):
    return f"---\nid: R-{name}\ntype: docs:Readme\ntitle: {name.upper()}\nname: {name}\nversion: {version}\n---\n"


def test_file_field_clause_and_existence_rule(project):
    project.pack("docs", DOCS_PACK).profile(packs=["docs@1"])
    project.write("lib/a/manifest.yaml", "kind: pack\nmeta: {version: 1.2.0}\n")
    project.write("lib/a/README.md", readme("a", "1.2.0"))
    project.write("lib/b/manifest.yaml", "kind: bridge\nmeta: {version: 2.0.0}\n")
    project.write("lib/b/README.md", readme("b", "1.0.0"))
    project.write("lib/c/manifest.yaml", "kind: pack\nmeta: {version: 1.0.0}\n")
    project.write("lib/d/README.md", readme("d", "1.0.0"))
    project.write("lib/e/manifest.yaml", "kind: [broken\n")
    project.write("lib/e/README.md", readme("e", "1.0.0"))
    project.write("lib/f/manifest.yaml", "kind: pack\n")
    project.write("lib/f/README.md", readme("f", "1.0.0"))
    assert violations(project, "docs/version-matches") == [
        ("R-b", "The README states the manifest's version. "
                "(lib/b/manifest.yaml kind is 'bridge', the expected value is 'pack')"),
        ("R-b", "The README states the manifest's version. "
                "(lib/b/manifest.yaml meta.version is '2.0.0', field 'version' is '1.0.0')"),
        ("R-d", "The README states the manifest's version. (lib/d/manifest.yaml does not exist)"),
        ("R-d", "The README states the manifest's version. (lib/d/manifest.yaml does not exist)"),
        ("R-e", "The README states the manifest's version. (lib/e/manifest.yaml is not valid YAML or JSON (ParserError))"),
        ("R-e", "The README states the manifest's version. (lib/e/manifest.yaml is not valid YAML or JSON (ParserError))"),
        ("R-f", "The README states the manifest's version. (lib/f/manifest.yaml has no 'meta.version')"),
    ]
    [missing] = [d for d in check(project) if d.rule == "docs/manifest-has-readme"]
    assert (missing.path, missing.line, missing.node) == ("lib/c/manifest.yaml", None, None)
    assert missing.message == ("Every manifest has a README document. "
                               "(lib/c/manifest.yaml has no docs:Readme at lib/c/README.md)")
    assert missing.hint == "Add a README.md next to the manifest."
