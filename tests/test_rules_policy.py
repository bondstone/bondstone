"""Overrides, locked rules, waivers and the order of results."""

import datetime as dt

from conftest import adr, capability, check, standard

from bondstone.config import load_config
from bondstone.model import Diagnostic
from bondstone.rules import fails

TODAY = dt.date(2026, 11, 10)
NO_ALTERNATIVES = "## Context\n\n## Decision\n\n## Consequences\n"


def summary(project, today=TODAY):
    return [(d.rule, d.severity, d.node) for d in check(project, today)]


def test_overrides_raise_lower_and_ignore(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", extra="colour: red\n", body=NO_ALTERNATIVES))
    assert summary(project) == [
        ("adr-capability/accepted-decision-is-applied", "warn", "ADR-001"),
        ("adr/alternatives-considered", "warn", "ADR-001"),
        ("bondstone/field-unknown", "error", "ADR-001"),
    ]
    standard(project, overrides={"adr/alternatives-considered": "error", "bondstone/field-unknown": "info",
                                 "adr-capability/accepted-decision-is-applied": "ignore"})
    assert summary(project) == [
        ("adr/alternatives-considered", "error", "ADR-001"),
        ("bondstone/field-unknown", "info", "ADR-001"),
    ]


def test_trait_and_status_dependent_severities_are_overridden_too(project):
    standard(project, code={"include": ["src/*.py"]},
             overrides={"bondstone/code-coverage": "error", "bondstone/todo-left": "info"})
    project.write("docs/capabilities/a.md", capability().replace("\np\n", "\n<!-- todo: purpose -->\n"))
    assert summary(project) == [
        ("bondstone/todo-left", "info", "CAP-a"),
        ("bondstone/code-coverage", "error", "REQ-AA-001"),
    ]


def test_fail_on(project):
    def diag(severity):
        return Diagnostic("x/y", severity, "m")

    assert not fails([])
    assert not fails([diag("warn"), diag("info")])
    assert fails([diag("warn"), diag("info")], "warn")
    assert not fails([diag("info")], "warn")
    assert fails([diag("error")]) and fails([diag("error")], "warn")


def waiver(rule, node=None, reason="legacy", expires="2027-06-30"):
    entry = {"rule": rule, "node": node, "reason": reason, "expires": expires}
    return {key: value for key, value in entry.items() if value is not None}


def test_waivers_remove_matching_diagnostics_until_they_expire(project):
    standard(project, waivers=[waiver("bondstone/field-unknown", "ADR-001"),
                               waiver("adr/alternatives-considered")])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed", extra="colour: red\n"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed", extra="colour: red\n"))
    project.write("docs/adr/ADR-003-c.md", adr("ADR-003", extra="deciders: [me]\n", body=NO_ALTERNATIVES))
    assert summary(project) == [
        ("bondstone/field-unknown", "error", "ADR-002"),  # the waiver names ADR-001 only
        ("adr-capability/accepted-decision-is-applied", "warn", "ADR-003"),
    ]
    # the day after the expiry date the waiver no longer applies and is reported itself
    assert summary(project, dt.date(2027, 6, 30)) == summary(project)
    late = check(project, dt.date(2027, 7, 1))
    assert [(d.rule, d.severity, d.path) for d in late if d.rule.startswith("bondstone/waiver")] == [
        ("bondstone/waiver-expired", "error", ".bondstone/profile.yaml")] * 2
    assert [d.message for d in late if d.rule.startswith("bondstone/waiver")] == [
        "waiver for adr/alternatives-considered (all nodes) expired on 2027-06-30",
        "waiver for bondstone/field-unknown (ADR-001) expired on 2027-06-30",
    ]
    assert ("bondstone/field-unknown", "error", "ADR-001") in [(d.rule, d.severity, d.node) for d in late]


def test_unused_and_invalid_waivers(project):
    standard(project, waivers=[
        waiver("bondstone/id-format"),
        {"rule": "bondstone/section-missing", "expires": "2027-06-30"},
        {"rule": "bondstone/link-broken", "reason": "x"},
        {"reason": "no rule", "expires": "2027-06-30"},
        waiver("bondstone/link-min", expires="next year"),
        waiver("adr/nope"),
        waiver("bondstone/profile"),
    ])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    found = [(d.rule, d.severity, d.message) for d in check(project, TODAY)]
    assert found == [
        ("bondstone/waiver-invalid", "error", "configuration errors cannot be waived"),
        ("bondstone/waiver-invalid", "error", "waiver for #4 has no 'rule'"),
        ("bondstone/waiver-invalid", "error", "waiver for bondstone/link-broken has no 'expires'"),
        ("bondstone/waiver-invalid", "error",
         "waiver for bondstone/link-min (all nodes): 'expires' must be a date such as 2027-06-30"),
        ("bondstone/waiver-invalid", "error", "waiver for bondstone/section-missing has no 'reason'"),
        ("bondstone/waiver-invalid", "error", "waiver names an unknown rule 'adr/nope'"),
        ("bondstone/waiver-unused", "warn", "waiver for bondstone/id-format (all nodes) matches nothing"),
    ]


def test_waiver_diagnostics_can_be_overridden(project):
    standard(project, waivers=[waiver("bondstone/id-format")], overrides={"bondstone/waiver-unused": "ignore"})
    assert check(project, TODAY) == []


def test_an_ignored_rule_does_not_use_up_a_waiver(project):
    standard(project, waivers=[waiver("bondstone/field-unknown")], overrides={"bondstone/field-unknown": "ignore"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed", extra="colour: red\n"))
    assert summary(project) == [("bondstone/waiver-unused", "warn", None)]


STRICT = """
    id: strict
    version: 1.0.0
    types:
      Note: {id: "N-{n}", path: "notes/{id}.md"}
    rules:
      - id: has-summary
        severity: warn
        locked: true
        when: {type: Note}
        require: [{section: Summary}]
"""


def test_locked_rules_can_be_raised_but_not_lowered_or_waived(project):
    project.pack("strict", STRICT)
    project.write("notes/N-1.md", "---\nid: N-1\ntype: strict:Note\ntitle: A note\n---\n# Body\n")

    project.profile(packs=["strict@1"], overrides={"strict/has-summary": "ignore"})
    assert [d.message for d in load_config(project.root).errors] == [
        "overrides.strict/has-summary: the rule is locked; its severity (warn) can be raised but not lowered"]

    project.profile(packs=["strict@1"], overrides={"strict/has-summary": "error"},
                    waivers=[waiver("strict/has-summary", "N-1")])
    assert [(d.rule, d.severity, d.message) for d in check(project, TODAY)] == [
        ("bondstone/waiver-invalid", "error",
         "waiver for strict/has-summary (N-1): the rule is locked and cannot be waived"),
        ("strict/has-summary", "error", "strict/has-summary (missing section 'Summary')"),
    ]


def test_configuration_warnings_go_through_the_policy(project):
    standard(project, bridges=[])
    assert summary(project) == [("bondstone/unbridged-packs", "warn", None)]
    standard(project, bridges=[], overrides={"bondstone/unbridged-packs": "ignore"})
    assert summary(project) == []


def test_results_are_sorted_by_path_line_and_rule(project):
    standard(project)
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed", extra="colour: red\nsupersedes: ADR-009\n"))
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed", extra="colour: red\n", body="## Context\n"))
    assert [(d.path, d.line, d.rule) for d in check(project, TODAY)] == [
        ("docs/adr/ADR-001-a.md", 1, "bondstone/section-missing"),
        ("docs/adr/ADR-001-a.md", 1, "bondstone/section-missing"),
        ("docs/adr/ADR-001-a.md", 8, "bondstone/field-unknown"),
        ("docs/adr/ADR-002-b.md", 8, "bondstone/field-unknown"),
        ("docs/adr/ADR-002-b.md", 9, "bondstone/link-broken"),
    ]


def test_running_twice_gives_the_same_result(project):
    standard(project, overrides={"bondstone/field-unknown": "warn"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed", extra="colour: red\n"))
    assert summary(project) == summary(project) == [("bondstone/field-unknown", "warn", "ADR-001")]
