"""Known violations: `.bondstone/known.json` (D6)."""

import datetime as dt
import json

import pytest
from conftest import ADR_BODY, Project, adr, capability, check, standard

from bondstone import resolve as resolver
from bondstone.baseline import record_known
from bondstone.cli import main
from bondstone.config import load_config
from bondstone.known import KNOWN_PATH, Entry, fingerprint, parse, render
from bondstone.model import Diagnostic

TODAY = dt.date(2026, 11, 13)
NO_CONSEQUENCES = ADR_BODY.replace("## Consequences\n\nx\n", "")
MISSING = Entry("bondstone/section-missing", node="ADR-001", key="Consequences")


@pytest.fixture(autouse=True)
def no_installed_packages(monkeypatch):
    monkeypatch.setattr(resolver, "entry_points", lambda group: [])


@pytest.fixture
def old(project) -> Project:
    """A repository that adopts bondstone with one decision that lacks a section."""
    standard(project, docs=["docs/**/*.md"])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", body=NO_CONSEQUENCES))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002"))
    project.write("docs/capabilities/a.md", capability(extra="constrained_by: [ADR-001, ADR-002]\n"))
    return project


def record(project: Project, prune: bool = False):
    return record_known(load_config(project.root), prune, TODAY)


def found(project: Project, **options) -> list[tuple[str, str, str | None]]:
    return [(d.rule, d.severity, d.node) for d in check(project, TODAY, **options)]


def run(capsys, project: Project, *argv: str) -> tuple[int, str]:
    code = main(["--root", str(project.root), *argv])
    return code, capsys.readouterr().out


# --------------------------------------------------------------------------- the file


def test_recording_writes_one_sorted_entry_per_line(old):
    old.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="colour: red\n"))
    result = record(old)
    assert (result.entries, result.added, result.removed) == (2, 2, 0)
    assert old.read(KNOWN_PATH) == (
        '{\n  "bondstone": 1,\n  "created": "2026-11-13",\n  "entries": [\n'
        '    {"rule": "bondstone/field-unknown", "node": "ADR-002", "key": "colour"},\n'
        '    {"rule": "bondstone/section-missing", "node": "ADR-001", "key": "Consequences"}\n'
        '  ]\n}\n')


def test_the_file_reads_back_with_the_line_of_every_entry(old):
    record(old)
    known, problems = parse(old.read(KNOWN_PATH))
    assert problems == []
    assert (known.entries, known.created, known.lines) == ([MISSING], "2026-11-13", {MISSING: 5})


def test_a_repository_without_violations_gets_no_file(project):
    standard(project, docs=["docs/**/*.md"])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", status="proposed"))
    assert record(project).entries == 0
    assert not (project.root / KNOWN_PATH).exists()


def test_recording_again_keeps_the_date_and_the_entries_that_still_match(old):
    record(old)
    old.edit(KNOWN_PATH, "2026-11-13", "2026-01-01")
    old.write("docs/adr/ADR-002-b.md", adr("ADR-002", body=NO_CONSEQUENCES))
    result = record(old)
    assert (result.entries, result.added) == (2, 1)
    assert '"created": "2026-01-01"' in old.read(KNOWN_PATH)


@pytest.mark.parametrize("text, message", [
    ("{", "invalid JSON"),
    ('{"bondstone": 1}', "missing required key 'entries'"),
    ('{"bondstone": 2, "entries": []}', "expected the format version 1"),
    ('{"bondstone": 1, "entries": [], "note": "x"}', "unknown key 'note'"),
    ('{"bondstone": 1, "entries": [{"rule": "a/b"}]}', "exactly one of `node` and `path`"),
    ('{"bondstone": 1, "entries": [{"rule": "a/b", "node": "X", "path": "y"}]}', "exactly one of `node` and `path`"),
    ('{"bondstone": 1, "entries": [{"node": "X"}]}', "missing required key 'rule'"),
])
def test_a_malformed_file_is_a_configuration_error(old, text, message):
    old.write(KNOWN_PATH, text)
    errors = load_config(old.root).errors
    assert [d.path for d in errors] == [KNOWN_PATH]
    assert message in errors[0].message


def test_check_stops_on_a_malformed_file(old, capsys):
    old.write(KNOWN_PATH, "[]")
    code, out = run(capsys, old, "check")
    assert code == 2 and KNOWN_PATH in out


# --------------------------------------------------------------------------- fingerprints


def test_a_fingerprint_is_the_rule_the_node_and_the_key():
    diag = Diagnostic("adr/x", "error", "m", "docs/a.md", 7, "ADR-001", key="Context")
    assert fingerprint(diag) == Entry("adr/x", node="ADR-001", key="Context")
    assert str(fingerprint(diag)) == "adr/x on ADR-001 (Context)"


def test_a_violation_without_a_node_is_recorded_by_its_file(old):
    old.write("docs/notes.md", "# Notes\n")
    record(old)
    assert {"rule": "bondstone/untyped-document", "path": "docs/notes.md"} in json.loads(old.read(KNOWN_PATH))["entries"]
    assert ("bondstone/untyped-document", "info", None) in found(old)


def test_declared_rules_are_keyed_by_what_the_clause_asks_for(project):
    standard(project, docs=["docs/**/*.md"], rules=[
        {"id": "has-date", "when": {"type": "adr:Decision"},
         "require": [{"section": "Options"}, {"field": "deciders"},
                     {"any": [{"link": "supersedes"}, {"incoming": "constrained_by"}]}]},
    ])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", status="proposed"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", status="rejected"))
    project.write("docs/capabilities/a.md", capability(
        extra="constrained_by: [ADR-002]\n", requirements="### REQ-AA-001: Thing\n\nNo scenario.\n"))
    keys = {(d.rule, d.node): d.key for d in check(project, TODAY) if d.rule != "profile/has-date"}
    assert keys[("capability/requirement-has-scenario", "REQ-AA-001")] == r"(?m)^####\s+Scenario:"
    assert keys[("adr-capability/constrained-by-live-decision", "CAP-a")] == "ADR-002"
    own = sorted(d.key for d in check(project, TODAY) if d.rule == "profile/has-date" and d.node == "ADR-001")
    assert own == ["Options", "deciders", "supersedes | <-constrained_by"]


# --------------------------------------------------------------------------- matching


def test_a_known_violation_is_info_and_does_not_fail(old, capsys):
    assert ("bondstone/section-missing", "error", "ADR-001") in found(old)
    record(old)
    assert found(old) == [("bondstone/section-missing", "info", "ADR-001")]
    code, out = run(capsys, old, "check")
    assert code == 0
    assert "info bondstone/section-missing: adr:Decision requires a 'Consequences' section [known]" in out
    assert "✓ 0 error(s), 0 warning(s), 1 info (1 known)" in out


def test_json_marks_a_known_violation(old, capsys):
    record(old)
    code, out = run(capsys, old, "check", "--format", "json")
    payload = json.loads(out)
    assert code == 0
    assert payload["summary"] == {"errors": 0, "warnings": 0, "info": 1, "known": 1, "nodes": 4}
    assert payload["diagnostics"][0]["known"] is True
    assert "key" not in payload["diagnostics"][0]


def test_only_a_known_violation_carries_the_mark(old, capsys):
    code, out = run(capsys, old, "check", "--format", "json")
    payload = json.loads(out)
    assert code == 1
    assert "known" not in payload["summary"] and "known" not in payload["diagnostics"][0]


def test_edits_elsewhere_in_the_document_do_not_break_the_match(old):
    record(old)
    old.edit("docs/adr/ADR-001-a.md", "## Context\n", "## Background\n\nMore text.\n\n## Context\n")
    assert found(old) == [("bondstone/section-missing", "info", "ADR-001")]


def test_a_new_problem_in_a_document_with_a_known_one_fails(old):
    record(old)
    old.edit("docs/adr/ADR-001-a.md", "date: 2026-01-01\n", "date: 2026-01-01\nsupersedes: ADR-009\n")
    assert sorted(found(old)) == [("bondstone/link-broken", "error", "ADR-001"),
                                  ("bondstone/section-missing", "info", "ADR-001")]


def test_the_same_problem_in_another_document_fails(old):
    record(old)
    old.write("docs/adr/ADR-002-b.md", adr("ADR-002", body=NO_CONSEQUENCES))
    assert ("bondstone/section-missing", "error", "ADR-002") in found(old)


def test_a_waiver_is_applied_before_known_violations(old):
    record(old)
    standard(old, docs=["docs/**/*.md"], waivers=[
        {"rule": "bondstone/section-missing", "node": "ADR-001", "reason": "r", "expires": "2027-01-01"}])
    assert found(old) == [("bondstone/known-stale", "warn", "ADR-001")]


# --------------------------------------------------------------------------- the file only shrinks


def test_a_fixed_violation_leaves_a_stale_entry(old):
    record(old)
    old.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    stale, = check(old, TODAY)
    assert (stale.rule, stale.severity, stale.path, stale.line) == ("bondstone/known-stale", "warn", KNOWN_PATH, 5)
    assert stale.message == ("known violation bondstone/section-missing on ADR-001 (Consequences): "
                             "the violation no longer occurs")
    assert "baseline --known --prune" in stale.hint


def test_an_entry_for_a_rule_that_is_gone_is_stale(old):
    old.write(KNOWN_PATH, render([MISSING, Entry("adr/removed-rule", node="ADR-001")], "2026-11-13"))
    stale = [d.message for d in check(old, TODAY) if d.rule == "bondstone/known-stale"]
    assert stale == ["known violation adr/removed-rule on ADR-001: the rule does not exist"]


def test_prune_removes_what_is_fixed_and_never_adds(old):
    old.write("docs/adr/ADR-002-b.md", adr("ADR-002", body=NO_CONSEQUENCES))
    record(old)
    old.write("docs/adr/ADR-002-b.md", adr("ADR-002"))  # fixed
    old.write("docs/notes.md", "# Notes\n")  # new
    result = record(old, prune=True)
    assert (result.entries, result.added, result.removed) == (1, 0, 1)
    assert parse(old.read(KNOWN_PATH))[0].entries == [MISSING]
    assert ("bondstone/untyped-document", "error", None) in found(old)


def test_pruning_the_last_entry_deletes_the_file(old, capsys):
    record(old)
    old.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    code, out = run(capsys, old, "baseline", "--known", "--prune")
    assert code == 0
    assert "removed 1 known violation(s) that no longer occur; 0 remain" in out
    assert f"deleted {KNOWN_PATH}" in out
    assert not (old.root / KNOWN_PATH).exists()
    assert found(old) == []


# --------------------------------------------------------------------------- growth


@pytest.fixture
def adopted(old) -> tuple[Project, str]:
    """The repository with its known violations committed."""
    old.init()
    old.commit("documents and a profile")
    record(old)
    return old, old.commit("record the known violations")


def grew(project: Project, base: str) -> list[str]:
    return [d.message for d in check(project, TODAY, base=base) if d.rule == "bondstone/known-grew"]


def test_entries_added_since_the_base_are_an_error(adopted):
    project, base = adopted
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", status="proposed", body=NO_CONSEQUENCES))
    assert ("bondstone/section-missing", "error", "ADR-002") in found(project, base=base)
    record(project)  # an attempt to hide it
    diagnostics = check(project, TODAY, base=base)
    growth, = [d for d in diagnostics if d.rule == "bondstone/known-grew"]
    assert (growth.severity, growth.path, growth.line) == ("error", KNOWN_PATH, 6)
    assert growth.message == (f"1 known violation(s) added since {base[:7]}: "
                              "bondstone/section-missing on ADR-002 (Consequences)")


def test_a_new_file_in_a_repository_that_already_had_a_profile_is_growth(adopted):
    project, _ = adopted
    first = project.git("rev-list", "--max-parents=0", "HEAD")
    assert len(grew(project, first)) == 1


def test_the_change_that_adds_the_profile_is_not_growth(project):
    project.init()
    project.write("README.md", "# A repository\n")
    before = project.commit("before bondstone")
    standard(project, docs=["docs/**/*.md"])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", status="proposed", body=NO_CONSEQUENCES))
    record(project)
    project.commit("adopt bondstone")
    assert found(project, base=before) == [("bondstone/section-missing", "info", "ADR-001")]


def test_removing_entries_is_not_growth(adopted):
    project, base = adopted
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", status="proposed"))
    record(project, prune=True)
    assert grew(project, base) == []


def test_a_deliberate_reset_is_a_visible_override(adopted):
    project, base = adopted
    project.write("docs/notes.md", "# Notes\n")
    record(project)
    standard(project, docs=["docs/**/*.md"], overrides={"bondstone/known-grew": "warn"})
    assert ("bondstone/known-grew", "warn", None) in found(project, base=base)


def test_many_new_entries_are_one_diagnostic(adopted):
    project, base = adopted
    for number in range(3, 10):
        project.write(f"docs/adr/ADR-00{number}-x.md", adr(f"ADR-00{number}", status="proposed", body=NO_CONSEQUENCES))
    record(project)
    message, = grew(project, base)
    assert message.startswith("7 known violation(s) added since") and message.endswith("; and 2 more")


# --------------------------------------------------------------------------- rules that must hold


def test_a_rule_can_refuse_known_violations(old):
    standard(old, docs=["docs/**/*.md"], rules=[
        {"id": "has-options", "allow_known": False, "when": {"type": "adr:Decision"},
         "require": [{"section": "Options"}]}])
    result = record(old)
    assert (result.entries, result.refused) == (1, 2)
    assert [d.severity for d in check(old, TODAY) if d.rule == "profile/has-options"] == ["error", "error"]


def test_an_entry_for_such_a_rule_is_stale(old):
    standard(old, docs=["docs/**/*.md"], rules=[
        {"id": "has-options", "allow_known": False, "when": {"type": "adr:Decision"},
         "require": [{"section": "Options"}]}])
    old.write(KNOWN_PATH, render([Entry("profile/has-options", node="ADR-001", key="Options")], "2026-11-13"))
    by_rule = {d.rule: d for d in check(old, TODAY) if d.node == "ADR-001"}
    assert by_rule["profile/has-options"].severity == "error"
    assert by_rule["bondstone/known-stale"].message.endswith("the rule does not accept known violations")


def preset(project: Project, lock: str) -> Project:
    project.write(".bondstone/packs/org/preset.yaml", f"id: org\nversion: 1.0.0\nlock: {lock}\n")
    return standard(project, docs=["docs/**/*.md"], extends=["org@1"])


def test_a_locked_rule_honours_known_violations_by_default(old):
    preset(old, "[bondstone/section-missing]")
    record(old)
    assert found(old) == [("bondstone/section-missing", "info", "ADR-001")]


def test_a_preset_can_lock_a_rule_without_known_violations(old):
    preset(old, "[{rule: bondstone/section-missing, allow_known: false}]")
    cfg = load_config(old.root)
    assert cfg.errors == []
    assert cfg.locks["bondstone/section-missing"].by == "org" and cfg.no_known == {"bondstone/section-missing": "org"}
    assert record(old).refused == 1
    assert found(old) == [("bondstone/section-missing", "error", "ADR-001")]


def test_a_lock_entry_must_name_a_known_rule(old):
    preset(old, "[{rule: adr/nope, allow_known: false}]")
    assert ["lock: adr/nope: unknown rule" in d.message for d in load_config(old.root).errors] == [True]


def test_checks_of_a_change_are_never_recorded(old):
    cfg = load_config(old.root)
    for rule in ("bondstone/immutable", "bondstone/status-transition", "bondstone/waiver-expired",
                 "bondstone/known-stale", "bondstone/known-grew", "bondstone/view-stale", "bondstone/profile"):
        assert not cfg.accepts_known(rule), rule
    assert cfg.accepts_known("bondstone/link-broken") and cfg.accepts_known("adr/alternatives-considered")
    assert not cfg.accepts_known("adr/no-such-rule")


def test_a_diff_rule_is_never_recorded(old):
    standard(old, docs=["docs/**/*.md"], rules=[
        {"id": "code-needs-docs", "on_change": {"paths": ["src/**"]}, "require": [{"changed": {"type": "adr:Decision"}}]}])
    assert not load_config(old.root).accepts_known("profile/code-needs-docs")


# --------------------------------------------------------------------------- the command


def test_the_command_reports_what_it_recorded(old, capsys):
    code, out = run(capsys, old, "baseline", "--known")
    assert (code, out) == (0, f"recorded 1 known violation(s) in {KNOWN_PATH} (1 new)\n")
    code, out = run(capsys, old, "baseline", "--known")
    assert (code, out) == (0, f"recorded 1 known violation(s) in {KNOWN_PATH} (0 new)\n")


def test_the_command_says_when_there_is_nothing_to_record(project, capsys):
    standard(project, docs=["docs/**/*.md"])
    assert run(capsys, project, "baseline", "--known") == (0, "no violations to record\n")


def test_prune_needs_known_and_known_takes_no_commit(old, capsys):
    assert main(["--root", str(old.root), "baseline", "--prune"]) == 1
    assert "--prune only applies" in capsys.readouterr().err
    assert main(["--root", str(old.root), "baseline", "HEAD", "--known"]) == 1
    assert "takes no REF" in capsys.readouterr().err
