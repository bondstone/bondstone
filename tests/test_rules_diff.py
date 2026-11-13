"""Checks that compare with a base commit: lifecycles, immutability, diff rules, exemptions.

Every test builds a throwaway git repository, as the design asks for diff tests."""

import json

import pytest
from conftest import ADR_BODY, CAPABILITY_PACK, Project, adr, capability, check, standard

from bondstone.format import to_json
from bondstone.model import EnvironmentProblem
from bondstone.rules import fails
from bondstone.rules.diff import _parse_exemption, glob_to_regex

HISTORY_RULES = {
    "bondstone/status-initial", "bondstone/status-transition", "bondstone/immutable",
    "bondstone/baseline-missing", "bondstone/exemption-used", "bondstone/exemption-invalid",
    "profile/code-updates-spec",
}

DIFF_RULE = {
    "id": "code-updates-spec",
    "description": "Code changes update a living spec.",
    "on_change": {"paths": ["src/**"]},
    "require": [{"changed": {"role": "living-spec"}, "min": 1}],
}
TRACED_RULE = {**DIFF_RULE, "require": [{"changed": {"role": "living-spec"}, "traced": True}],
               "exempt": {"trailer": "Spec-Impact"}}

CODE = """\
# bondstone: REQ-AA-001
def first():
    return 1


# bondstone: REQ-BB-001
def second():
    return 2
"""


def history(project: Project, base: str = "HEAD", **options):
    """The diagnostics that need a base commit, as (rule, node) pairs."""
    return [(d.rule, d.node) for d in check(project, base=base, **options) if d.rule in HISTORY_RULES]


def one(project: Project, rule: str, base: str = "HEAD", **options):
    found = [d for d in check(project, base=base, **options) if d.rule == rule]
    assert len(found) == 1, [(d.rule, d.message) for d in check(project, base=base, **options)]
    return found[0]


@pytest.fixture
def repo(project) -> Project:
    """A committed repository with a proposed and an accepted decision and two capabilities."""
    standard(project.init(), code={"include": ["src/**/*.py"]})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "accepted"))
    project.write("docs/capabilities/a.md", capability("CAP-a", "AA"))
    project.write("docs/capabilities/b.md", capability("CAP-b", "BB"))
    project.write("src/code.py", CODE)
    project.commit("first")
    return project


def with_rule(project: Project, rule: dict) -> Project:
    """Add a repository diff rule to the profile and commit it, so it is not itself a change."""
    standard(project, code={"include": ["src/**/*.py"]}, rules=[rule])
    project.commit("add the diff rule")
    return project


# --------------------------------------------------------------------------- lifecycle


def test_nothing_is_reported_without_changes(repo):
    assert history(repo) == []


def test_a_new_document_must_start_in_the_initial_status(repo):
    repo.write("docs/adr/ADR-003-c.md", adr("ADR-003", "accepted"))
    repo.write("docs/adr/ADR-004-d.md", adr("ADR-004", "proposed"))
    assert history(repo) == [("bondstone/status-initial", "ADR-003")]
    diag = one(repo, "bondstone/status-initial")
    assert diag.message == "new adr:Decision starts as 'accepted'; it must start as 'proposed'"
    assert (diag.path, diag.line, diag.severity) == ("docs/adr/ADR-003-c.md", 5, "error")
    assert "bondstone baseline" in diag.hint


def test_a_committed_new_document_is_checked_like_an_uncommitted_one(repo):
    base = repo.git("rev-parse", "HEAD")
    repo.write("docs/adr/ADR-003-c.md", adr("ADR-003", "accepted")).commit("add")
    assert history(repo, base) == [("bondstone/status-initial", "ADR-003")]
    assert history(repo, "HEAD") == []


def test_an_allowed_status_change_passes(repo):
    repo.edit("docs/adr/ADR-001-a.md", "status: proposed", "status: accepted")
    assert history(repo) == []


def test_a_status_change_the_lifecycle_does_not_allow(repo):
    repo.edit("docs/adr/ADR-002-b.md", "status: accepted", "status: proposed")
    diag = one(repo, "bondstone/status-transition")
    assert diag.message == "status change accepted -> proposed is not allowed (allowed: deprecated, superseded)"
    assert (diag.path, diag.line, diag.node) == ("docs/adr/ADR-002-b.md", 5, "ADR-002")


def test_a_status_without_outgoing_transitions_is_final(repo):
    repo.edit("docs/adr/ADR-002-b.md", "status: accepted", "status: rejected").commit("reject")
    repo.edit("docs/adr/ADR-002-b.md", "status: rejected", "status: proposed")
    assert one(repo, "bondstone/status-transition").message == (
        "status change rejected -> proposed is not allowed (allowed: none)")


def test_a_lifecycle_without_transitions_allows_any_change(repo):
    # the capability pack of the tests declares statuses and `initial` only
    repo.edit("docs/capabilities/a.md", "status: active", "status: draft")
    assert history(repo) == []


def test_a_lifecycle_without_initial_lets_new_nodes_start_anywhere(repo):
    repo.pack("capability", CAPABILITY_PACK.replace(", initial: draft", ""))
    repo.write("docs/capabilities/c.md", capability("CAP-c", "CC"))
    assert history(repo) == []


def test_changes_made_on_the_base_branch_after_the_fork_are_not_this_branch(repo):
    repo.git("checkout", "--quiet", "-b", "feature")
    repo.write("notes.txt", "n\n").commit("unrelated work")
    repo.git("checkout", "--quiet", "main")
    repo.edit("docs/adr/ADR-002-b.md", "status: accepted", "status: deprecated").commit("deprecate on main")
    repo.git("checkout", "--quiet", "feature")
    # compared with main's tip, this branch would seem to move ADR-002 from deprecated back to accepted
    assert history(repo, "main") == []


def test_an_unknown_base_stops_the_check(repo):
    with pytest.raises(EnvironmentProblem, match="'origin/main' is not a commit"):
        check(repo, base="origin/main")


# --------------------------------------------------------------------------- renames


def test_a_renamed_document_is_compared_with_its_old_file(repo):
    repo.git("mv", "docs/adr/ADR-002-b.md", "docs/adr/ADR-002-better-name.md")
    repo.edit("docs/adr/ADR-002-better-name.md", "status: accepted", "status: proposed")
    assert history(repo) == [("bondstone/status-transition", "ADR-002")]


def test_a_renamed_document_that_did_not_change_passes(repo):
    repo.git("mv", "docs/adr/ADR-002-b.md", "docs/adr/ADR-002-better-name.md")
    assert history(repo) == []


def test_a_moved_document_that_git_does_not_report_as_a_rename_is_found_by_its_id(repo):
    (repo.root / "docs/adr/ADR-002-b.md").unlink()
    # rewritten so thoroughly that git sees a deletion and a new file
    repo.write("docs/adr/ADR-002-new.md", adr("ADR-002", "accepted", body="## Context\n\nnew\n\n## Decision\n\nnew\n"
                                                                         "\n## Consequences\n\nnew\n"))
    assert history(repo) == [("bondstone/immutable", "ADR-002")]


# --------------------------------------------------------------------------- items


ITEM_LIFECYCLE = ("lifecycle: {statuses: [planned, active, removed], default: active, "
                  "transitions: {planned: [active, removed], active: [removed]}}")


@pytest.fixture
def items(repo) -> Project:
    """The repository with a requirement lifecycle that has transitions (D9)."""
    repo.pack("capability", CAPABILITY_PACK.replace(
        "lifecycle: {statuses: [planned, active, removed], default: active}", ITEM_LIFECYCLE))
    repo.write("docs/capabilities/a.md", capability("CAP-a", "AA", requirements=(
        "### REQ-AA-001: Thing\n\nThe system SHALL do the thing.\n\n#### Scenario: ok\n\n- Then fine\n\n"
        "### REQ-AA-002: Later\n\nStatus: planned\n\nThe system SHALL do more.\n\n#### Scenario: ok\n\n- Then fine\n")))
    repo.commit("requirements with a lifecycle")
    return repo


def test_an_item_follows_its_lifecycle(items):
    items.edit("docs/capabilities/a.md", "Status: planned\n\n", "")  # planned -> active: allowed
    assert history(items) == []


def test_an_item_cannot_go_back_to_an_earlier_status(items):
    items.edit("docs/capabilities/a.md", "### REQ-AA-001: Thing\n", "### REQ-AA-001: Thing\n\nStatus: planned\n")
    diag = one(items, "bondstone/status-transition")
    assert diag.message == "status change active -> planned is not allowed (allowed: removed)"
    assert (diag.node, diag.path, diag.line) == ("REQ-AA-001", "docs/capabilities/a.md", 17)


def test_a_new_item_may_start_in_any_status_unless_the_lifecycle_names_an_initial_one(items):
    more = "\n### REQ-AA-003: New\n\nThe system SHALL do a new thing.\n\n#### Scenario: ok\n\n- Then fine\n"
    (items.root / "docs/capabilities/a.md").write_text(items.read("docs/capabilities/a.md") + more, encoding="utf-8")
    assert history(items) == []
    items.pack("capability", items.read(".bondstone/packs/capability/pack.yaml").replace(
        "default: active,", "default: active, initial: planned,"))
    assert history(items) == [("bondstone/status-initial", "REQ-AA-003")]


def test_items_of_a_new_document_are_new(items):
    items.pack("capability", items.read(".bondstone/packs/capability/pack.yaml").replace(
        "default: active,", "default: active, initial: planned,"))
    items.commit("items start planned")
    items.write("docs/capabilities/c.md", capability("CAP-c", "CC").replace("status: active", "status: draft"))
    assert history(items) == [("bondstone/status-initial", "REQ-CC-001")]


# --------------------------------------------------------------------------- immutability


def test_editing_the_body_of_an_immutable_document(repo):
    repo.edit("docs/adr/ADR-002-b.md", "## Decision\n\nd", "## Decision\n\nsomething else")
    diag = one(repo, "bondstone/immutable")
    assert diag.message == "ADR-002 was 'accepted' and may not be edited (only status may change)"
    assert (diag.path, diag.line, diag.severity) == ("docs/adr/ADR-002-b.md", 1, "error")
    assert diag.hint == "Create a new document that supersedes it instead."


def test_editing_a_field_of_an_immutable_document(repo):
    repo.edit("docs/adr/ADR-002-b.md", "title: Decision ADR-002", "title: A better title")
    assert history(repo) == [("bondstone/immutable", "ADR-002")]


def test_the_status_of_an_immutable_document_may_change(repo):
    repo.edit("docs/adr/ADR-002-b.md", "status: accepted", "status: deprecated")
    assert history(repo) == []


def test_whitespace_around_the_body_is_not_an_edit(repo):
    (repo.root / "docs/adr/ADR-002-b.md").write_text(repo.read("docs/adr/ADR-002-b.md") + "\n\n", encoding="utf-8")
    assert history(repo) == []


def test_a_document_in_a_mutable_status_may_be_edited_and_decided_in_one_change(repo):
    repo.edit("docs/adr/ADR-001-a.md", "## Decision\n\nd", "## Decision\n\nrefined")
    repo.edit("docs/adr/ADR-001-a.md", "status: proposed", "status: accepted")
    assert history(repo) == []


def test_allow_lists_the_fields_that_may_change(repo):
    pack = repo.read(".bondstone/packs/adr/pack.yaml")
    repo.pack("adr", pack.replace("allow: [status]", "allow: [status, deciders]")).commit("allow deciders")
    repo.edit("docs/adr/ADR-002-b.md", "date: 2026-01-01\n", "date: 2026-01-01\ndeciders: [ann]\n")
    assert history(repo) == []
    repo.pack("adr", pack.replace("allow: [status]", "allow: []"))
    assert one(repo, "bondstone/immutable").message == (
        "ADR-002 was 'accepted' and may not be edited (nothing may change)")


def test_immutable_without_when_applies_in_every_status(repo):
    pack = repo.read(".bondstone/packs/adr/pack.yaml")
    repo.pack("adr", pack.replace("immutable: {when: [accepted, rejected, deprecated, superseded], allow: [status]}",
                                  "immutable: {}")).commit("always immutable")
    repo.edit("docs/adr/ADR-001-a.md", "## Decision\n\nd", "## Decision\n\nrefined")
    assert history(repo) == [("bondstone/immutable", "ADR-001")]


def test_immutability_can_be_overridden_and_waived(repo):
    repo.edit("docs/adr/ADR-002-b.md", "## Decision\n\nd", "## Decision\n\nsomething else")
    standard(repo, overrides={"bondstone/immutable": "warn"})
    assert one(repo, "bondstone/immutable").severity == "warn"
    standard(repo, waivers=[{"rule": "bondstone/immutable", "node": "ADR-002", "reason": "typo fix",
                             "expires": "2999-01-01"}])
    assert history(repo) == []


# --------------------------------------------------------------------------- baseline


@pytest.fixture
def adopted(project) -> tuple[Project, str, str]:
    """A repository that adopted bondstone in its second commit: (project, before, adoption)."""
    project.init().write("README.md", "# app\n")
    before = project.commit("before bondstone")
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted"))
    project.write("docs/capabilities/a.md", capability("CAP-a", "AA"))
    adoption = project.commit("adopt bondstone")
    return project, before, adoption


def test_without_a_baseline_adopted_documents_look_new(adopted):
    project, before, _ = adopted
    assert history(project, before) == [("bondstone/status-initial", "ADR-001"), ("bondstone/status-initial", "CAP-a")]


def test_documents_present_at_the_baseline_are_not_new(adopted):
    project, before, adoption = adopted
    standard(project, baseline=adoption)
    assert history(project, before) == []


def test_documents_are_compared_with_their_baseline_version(adopted):
    project, before, adoption = adopted
    standard(project, baseline=adoption)
    project.edit("docs/adr/ADR-001-a.md", "## Decision\n\nd", "## Decision\n\nedited after adoption")
    project.edit("docs/capabilities/a.md", "status: active", "status: deprecated")
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "accepted"))
    assert history(project, before) == [("bondstone/immutable", "ADR-001"), ("bondstone/status-initial", "ADR-002")]


def test_a_baseline_that_is_not_in_the_clone(adopted):
    project, before, _ = adopted
    standard(project, baseline="0123456789abcdef0123456789abcdef01234567")
    found = history(project, before)
    assert found[0] == ("bondstone/baseline-missing", None)
    assert ("bondstone/status-initial", "ADR-001") in found
    diag = one(project, "bondstone/baseline-missing", before)
    assert (diag.path, diag.severity) == (".bondstone/profile.yaml", "error")
    assert "is not available in this clone" in diag.message


def test_the_baseline_is_only_read_with_a_base(adopted):
    project, _, _ = adopted
    standard(project, baseline="0123456789abcdef0123456789abcdef01234567")
    assert [d.rule for d in check(project) if d.rule in HISTORY_RULES] == []


def test_a_baseline_must_be_a_quoted_commit_id(adopted):
    from bondstone.config import load_config

    project, _, _ = adopted
    standard(project, baseline=1234567)
    assert ["baseline" in d.message for d in load_config(project.root).errors] == [True]


# --------------------------------------------------------------------------- diff rules


def test_a_diff_rule_does_not_fire_when_no_path_matches(repo):
    with_rule(repo, DIFF_RULE)
    repo.write("README.md", "# readme\n")
    assert history(repo) == []


def test_a_diff_rule_fires_when_a_matching_file_changed(repo):
    with_rule(repo, DIFF_RULE)
    repo.edit("src/code.py", "return 1", "return 10")
    diag = one(repo, "profile/code-updates-spec")
    assert diag.message == ("Code changes update a living spec. "
                            "(changed src/code.py; needs 1 changed document(s) matching role=living-spec)")
    assert (diag.path, diag.line, diag.node, diag.severity) == (".bondstone/profile.yaml", None, None, "error")


def test_a_changed_document_that_matches_satisfies_the_rule(repo):
    with_rule(repo, DIFF_RULE)
    repo.edit("src/code.py", "return 1", "return 10")
    repo.edit("docs/adr/ADR-001-a.md", "## Decision\n\nd", "## Decision\n\nnot a living spec")
    assert history(repo) == [("profile/code-updates-spec", None)]
    repo.edit("docs/capabilities/b.md", "do the thing", "do the thing well")
    assert history(repo) == []


def test_many_changed_files_are_abbreviated(repo):
    with_rule(repo, DIFF_RULE)
    for n in range(7):
        repo.write(f"src/new{n}.py", "x = 1\n")
    assert "(changed src/new0.py, src/new1.py, src/new2.py, src/new3.py, src/new4.py …; needs" in one(
        repo, "profile/code-updates-spec").message


@pytest.mark.parametrize("kinds, expected", [
    (None, ["added", "deleted", "modified"]),
    (["added"], ["added"]),
    (["modified"], ["modified"]),
    (["deleted"], ["deleted"]),
    (["added", "deleted"], ["added", "deleted"]),
])
def test_kinds_limit_which_changes_trigger_a_rule(repo, kinds, expected):
    trigger = {"paths": ["src/**"], **({"kinds": kinds} if kinds else {})}
    repo.write("src/gone.py", "x = 1\n")
    with_rule(repo, {**DIFF_RULE, "on_change": trigger})
    fired = []
    for kind in ("added", "deleted", "modified"):
        repo.git("stash", "--quiet", "--include-untracked") if repo.git("status", "--porcelain") else None
        repo.git("checkout", "--quiet", ".")
        repo.git("clean", "--quiet", "-fd")
        if kind == "added":
            repo.write("src/new.py", "x = 1\n")
        elif kind == "deleted":
            (repo.root / "src/gone.py").unlink()
        else:
            repo.edit("src/code.py", "return 1", "return 10")
        if history(repo):
            fired.append(kind)
    assert fired == expected


def test_a_file_renamed_out_of_the_watched_paths_still_triggers(repo):
    with_rule(repo, DIFF_RULE)
    repo.git("mv", "src/code.py", "code.py")
    assert history(repo) == [("profile/code-updates-spec", None)]


def test_exists_and_any_clauses(repo):
    rule = {**DIFF_RULE, "require": [{"any": [
        {"exists": {"type": "adr:Decision", "status": "deprecated"}},
        {"changed": {"type": "adr:Decision"}, "min": 1},
    ]}]}
    with_rule(repo, rule)
    repo.edit("src/code.py", "return 1", "return 10")
    assert one(repo, "profile/code-updates-spec").message == (
        "Code changes update a living spec. (changed src/code.py; needs one of: "
        "needs 1 document(s) matching type=adr:Decision status=deprecated; or "
        "needs 1 changed document(s) matching type=adr:Decision)")
    repo.edit("docs/adr/ADR-002-b.md", "status: accepted", "status: deprecated")
    assert history(repo) == []


def test_exists_alone(repo):
    with_rule(repo, {**DIFF_RULE, "require": [{"exists": {"type": "adr:Decision", "status": "accepted"}, "min": 2}]})
    repo.edit("src/code.py", "return 1", "return 10")
    assert history(repo) == [("profile/code-updates-spec", None)]
    repo.edit("docs/adr/ADR-001-a.md", "status: proposed", "status: accepted")
    assert history(repo) == []


def test_a_diff_rule_overridden_to_ignore_is_not_evaluated(repo):
    with_rule(repo, DIFF_RULE)
    standard(repo, code={"include": ["src/**/*.py"]}, rules=[DIFF_RULE],
             overrides={"profile/code-updates-spec": "ignore"})
    repo.edit("src/code.py", "return 1", "return 10")
    assert history(repo) == []


def test_diff_rules_only_run_with_a_base(repo):
    with_rule(repo, DIFF_RULE)
    repo.edit("src/code.py", "return 1", "return 10")
    assert [d.rule for d in check(repo) if d.rule in HISTORY_RULES] == []


# --------------------------------------------------------------------------- traced regions


def test_only_the_spec_tagged_in_the_changed_region_must_change(repo):
    with_rule(repo, TRACED_RULE)
    repo.edit("src/code.py", "return 1", "return 10")
    diag = one(repo, "profile/code-updates-spec")
    assert diag.message == "Code changes update a living spec. (src/code.py implements CAP-a, which was not updated)"
    assert (diag.path, diag.node) == ("docs/capabilities/a.md", "CAP-a")


def test_updating_the_traced_spec_satisfies_the_rule(repo):
    with_rule(repo, TRACED_RULE)
    repo.edit("src/code.py", "return 2", "return 20")
    repo.edit("docs/capabilities/a.md", "do the thing", "do the thing well")  # the wrong capability
    assert history(repo) == [("profile/code-updates-spec", "CAP-b")]
    repo.edit("docs/capabilities/b.md", "do the thing", "do the thing well")
    assert history(repo) == []


def test_removed_code_is_traced_through_the_file_at_the_base(repo):
    with_rule(repo, TRACED_RULE)
    repo.write("src/code.py", CODE.split("# bondstone: REQ-BB-001")[0].rstrip() + "\n")
    assert history(repo) == [("profile/code-updates-spec", "CAP-b")]


def test_removing_a_statement_inside_a_function_traces_that_function_only(repo):
    with_rule(repo, TRACED_RULE)
    repo.write("src/code.py", CODE.replace("def first():\n", "def first():\n    x = 0\n"))
    repo.commit("a statement to remove")
    repo.edit("src/code.py", "    x = 0\n", "")
    assert history(repo) == [("profile/code-updates-spec", "CAP-a")]


def test_a_new_file_and_a_deleted_file_trace_every_tag_in_them(repo):
    with_rule(repo, TRACED_RULE)
    repo.write("src/new.py", "# bondstone: REQ-BB-001\ndef third():\n    return 3\n")
    assert history(repo) == [("profile/code-updates-spec", "CAP-b")]
    repo.commit("add")
    (repo.root / "src/code.py").unlink()
    assert history(repo) == [("profile/code-updates-spec", "CAP-a"), ("profile/code-updates-spec", "CAP-b")]


def test_changing_only_a_tag_line_traces_nothing(repo):
    with_rule(repo, TRACED_RULE)
    repo.edit("src/code.py", "# bondstone: REQ-AA-001", "# bondstone: REQ-AA-001, REQ-BB-001")
    assert history(repo) == []


def test_untraced_changes_pass_unless_the_clause_also_has_a_minimum(repo):
    with_rule(repo, TRACED_RULE)
    repo.write("src/untagged.py", "x = 1\n")
    assert history(repo) == []
    with_rule(repo, {**TRACED_RULE, "require": [{"changed": {"role": "living-spec"}, "traced": True, "min": 1}]})
    assert one(repo, "profile/code-updates-spec", "HEAD~1").message == (
        "Code changes update a living spec. "
        "(changed src/untagged.py; needs 1 changed document(s) matching role=living-spec)")


def test_a_traced_document_must_match_the_selector(repo):
    with_rule(repo, {**TRACED_RULE, "require": [{"changed": {"type": "adr:Decision"}, "traced": True}]})
    repo.edit("src/code.py", "return 1", "return 10")
    assert history(repo) == []


# --------------------------------------------------------------------------- exemptions


def test_a_trailer_exempts_the_change_and_stays_visible(repo):
    with_rule(repo, TRACED_RULE)
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/code.py", "return 1", "return 10")
    commit = repo.commit("Tidy up\n\nSpec-Impact: none (no behaviour change)")
    diagnostics = check(repo, base=base)
    diag = one(repo, "bondstone/exemption-used", base)
    assert diag.severity == "info"
    assert diag.message == (
        f"profile/code-updates-spec on CAP-a exempted by commit {commit[:7]} (Spec-Impact: no behaviour change): "
        "Code changes update a living spec. (src/code.py implements CAP-a, which was not updated)")
    assert (diag.path, diag.node) == ("docs/capabilities/a.md", "CAP-a")
    assert diag.exempted_by == {"commit": commit, "trailer": "Spec-Impact", "reason": "no behaviour change"}
    assert not fails([d for d in diagnostics if d.rule in HISTORY_RULES], "warn")
    entry = next(d for d in json.loads(to_json(diagnostics))["diagnostics"] if d["rule"] == "bondstone/exemption-used")
    assert entry["exempted_by"] == {"commit": commit, "trailer": "Spec-Impact", "reason": "no behaviour change"}
    assert list(entry)[-1] == "exempted_by"


def test_no_exemptions_ignores_trailers(repo):
    with_rule(repo, TRACED_RULE)
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/code.py", "return 1", "return 10")
    repo.commit("Tidy up\n\nSpec-Impact: none (no behaviour change)")
    repo.commit("Broken trailer\n\nSpec-Impact: whatever")
    assert history(repo, base, exemptions=False) == [("profile/code-updates-spec", "CAP-a")]


def test_a_rule_without_exempt_cannot_be_exempted(repo):
    with_rule(repo, DIFF_RULE)
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/code.py", "return 1", "return 10")
    repo.commit("Tidy up\n\nSpec-Impact: none (no behaviour change)")
    assert history(repo, base) == [("profile/code-updates-spec", None)]


def test_a_trailer_can_be_limited_to_some_nodes(repo):
    with_rule(repo, TRACED_RULE)
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/code.py", "return 1", "return 10").edit("src/code.py", "return 2", "return 20")
    repo.commit("Rename\n\nSpec-Impact: none [CAP-a] (rename only)")
    assert sorted(history(repo, base)) == [("bondstone/exemption-used", "CAP-a"), ("profile/code-updates-spec", "CAP-b")]


def test_a_limited_trailer_does_not_cover_a_violation_without_a_node(repo):
    with_rule(repo, {**DIFF_RULE, "exempt": {"trailer": "Spec-Impact"}})
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/code.py", "return 1", "return 10")
    repo.commit("Rename\n\nSpec-Impact: none [CAP-a] (rename only)")
    assert history(repo, base) == [("profile/code-updates-spec", None)]
    repo.commit("And the rest\n\nspec-impact: none (trailer names ignore case)")
    assert history(repo, base) == [("bondstone/exemption-used", None)]


@pytest.mark.parametrize("value", ["yes", "none", "none ()", "none (  )", "none [] (reason)", "skip (reason)"])
def test_a_malformed_trailer_is_an_error_and_exempts_nothing(repo, value):
    with_rule(repo, TRACED_RULE)
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/code.py", "return 1", "return 10")
    commit = repo.commit(f"Tidy up\n\nSpec-Impact: {value}")
    assert sorted(history(repo, base)) == [("bondstone/exemption-invalid", None), ("profile/code-updates-spec", "CAP-a")]
    diag = one(repo, "bondstone/exemption-invalid", base)
    assert diag.message == f"commit {commit[:7]}: trailer 'Spec-Impact: {value.strip()}' is not an exemption"
    assert (diag.severity, diag.path) == ("error", None)
    assert "`Spec-Impact: none (<reason>)`" in diag.hint


def test_a_malformed_trailer_is_reported_even_when_the_rule_did_not_fire(repo):
    with_rule(repo, TRACED_RULE)
    base = repo.git("rev-parse", "HEAD")
    repo.commit("Docs only\n\nSpec-Impact: nope")
    assert history(repo, base) == [("bondstone/exemption-invalid", None)]


def test_other_trailers_and_trailers_before_the_base_are_ignored(repo):
    with_rule(repo, TRACED_RULE)
    repo.commit("Old\n\nSpec-Impact: none (before the base)")
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/code.py", "return 1", "return 10")
    repo.commit("Change\n\nReviewed-by: nope")
    assert history(repo, base) == [("profile/code-updates-spec", "CAP-a")]


def test_a_waiver_wins_over_an_exemption_and_exemption_used_can_be_silenced(repo):
    with_rule(repo, TRACED_RULE)
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/code.py", "return 1", "return 10")
    repo.commit("Tidy up\n\nSpec-Impact: none (no behaviour change)")
    options = {"code": {"include": ["src/**/*.py"]}, "rules": [TRACED_RULE]}
    standard(repo, **options, waivers=[{"rule": "profile/code-updates-spec", "node": "CAP-a", "reason": "r",
                                        "expires": "2999-01-01"}])
    assert history(repo, base) == []
    standard(repo, **options, overrides={"bondstone/exemption-used": "ignore"})
    assert history(repo, base) == []


# --------------------------------------------------------------------------- helpers


@pytest.mark.parametrize("value, expected", [
    ("none (reason)", (None, "reason")),
    ("none(reason)", (None, "reason")),
    ("none  [CAP-a]  (rename only)", (["CAP-a"], "rename only")),
    ("none [CAP-a, REQ-AA-001] (a (nested) reason)", (["CAP-a", "REQ-AA-001"], "a (nested) reason")),
    ("None (reason)", None),
    ("none", None),
    ("none []", None),
    ("partial (reason)", None),
])
def test_parse_exemption(value, expected):
    assert _parse_exemption(value) == expected


@pytest.mark.parametrize("pattern, path, expected", [
    ("src/**", "src/a.py", True),
    ("src/**", "src/deep/er/a.py", True),
    ("src/**", "lib/src/a.py", False),
    ("src/**/*.py", "src/a.py", True),
    ("src/**/*.py", "src/deep/a.py", True),
    ("src/*.py", "src/deep/a.py", False),
    ("**/*.md", "README.md", True),
    ("docs/?.md", "docs/a.md", True),
    ("docs/?.md", "docs/ab.md", False),
    ("a.b", "aXb", False),
])
def test_glob_to_regex(pattern, path, expected):
    assert bool(glob_to_regex(pattern).match(path)) is expected


def test_adr_body_helper_is_what_the_edits_assume():
    assert "## Decision\n\nd" in ADR_BODY


# --------------------------------------------------------------------------- the repository's code as a trigger

CODE_RULE = {**DIFF_RULE, "on_change": {"code": True}}


def test_a_rule_on_code_fires_for_the_files_the_profile_selects(repo):
    standard(repo, code={"include": ["src/**/*.py", "tools/*.sh"], "exclude": ["src/generated/**"]}, rules=[CODE_RULE])
    repo.write("src/generated/api.py", "x = 1\n").write("tools/build.sh", "true\n").write("notes.txt", "n\n")
    repo.commit("add the rule and some files")

    repo.edit("src/generated/api.py", "x = 1", "x = 2")
    repo.edit("notes.txt", "n", "m")
    assert history(repo) == []
    repo.edit("tools/build.sh", "true", "false")
    assert one(repo, "profile/code-updates-spec").message == (
        "Code changes update a living spec. "
        "(changed tools/build.sh; needs 1 changed document(s) matching role=living-spec)")
    repo.edit("src/code.py", "return 1", "return 10")
    assert "changed src/code.py, tools/build.sh;" in one(repo, "profile/code-updates-spec").message


def test_a_rule_on_code_respects_kinds_and_renames(repo):
    with_rule(repo, {**CODE_RULE, "on_change": {"code": True, "kinds": ["added"]}})
    repo.edit("src/code.py", "return 1", "return 10")
    assert history(repo) == []
    repo.write("src/new.py", "x = 1\n")
    assert history(repo) == [("profile/code-updates-spec", None)]

    with_rule(repo, CODE_RULE)
    repo.git("mv", "src/code.py", "code.py")  # out of the code globs: the old path still counts
    assert history(repo) == [("profile/code-updates-spec", None)]


def test_a_rule_on_code_never_fires_without_code_globs(repo):
    standard(repo, rules=[CODE_RULE])
    repo.commit("a profile without code globs")
    repo.edit("src/code.py", "return 1", "return 10")
    assert history(repo) == []


@pytest.mark.parametrize("trigger", [{}, {"kinds": ["added"]}, {"paths": ["src/**"], "code": True}])
def test_a_trigger_names_paths_or_code_but_not_both(project, trigger):
    from bondstone.config import load_config
    standard(project, rules=[{**DIFF_RULE, "on_change": trigger}])
    assert [d.message for d in load_config(project.root).errors] == [
        "profile/code-updates-spec: `on_change` needs exactly one of `paths` and `code: true`"]


def test_code_must_be_true(project):
    from bondstone.config import load_config
    standard(project, rules=[{**DIFF_RULE, "on_change": {"code": False}}])
    assert [d.message for d in load_config(project.root).errors] == [
        "rules[0].on_change.code: expected true, got false"]


# --------------------------------------------------------------------------- link targets of a changed node

LINKED_RULE = {
    "id": "capability-updates-its-decisions",
    "description": "A capability that changes updates the decisions that constrain it.",
    "on_change": {"paths": ["docs/capabilities/**"]},
    "require": [{"link_changed": "constrained_by", "from": {"type": "capability:Capability", "status": "active"}}],
    "exempt": {"trailer": "Decision-Impact"},
}


@pytest.fixture
def linked(repo) -> Project:
    """CAP-a is constrained by the proposed ADR-001, CAP-b by nothing."""
    repo.write("docs/capabilities/a.md", capability("CAP-a", "AA", extra="constrained_by: [ADR-001]\n"))
    standard(repo, code={"include": ["src/**/*.py"]}, rules=[LINKED_RULE])
    repo.commit("add the rule and the link")
    return repo


def linked_violations(project: Project, **options):
    return [(d.rule, d.node) for d in check(project, base="HEAD", **options) if d.rule.startswith("profile/")]


def test_a_changed_node_whose_link_target_did_not_change(linked):
    linked.edit("docs/capabilities/a.md", "## Purpose\n\np", "## Purpose\n\nMore.")
    diag = one(linked, "profile/capability-updates-its-decisions")
    assert (diag.node, diag.path) == ("CAP-a", "docs/capabilities/a.md")
    assert diag.message.endswith("(CAP-a changed, and ADR-001, which it names under 'constrained_by', was not updated)")


def test_the_clause_holds_when_the_target_changed_too(linked):
    linked.edit("docs/capabilities/a.md", "## Purpose\n\np", "## Purpose\n\nMore.")
    linked.edit("docs/adr/ADR-001-a.md", "## Context\n\nc", "## Context\n\nMore.")
    assert linked_violations(linked) == []


def test_only_nodes_that_match_from_are_asked(linked):
    linked.edit("docs/capabilities/a.md", "status: active", "status: deprecated")
    assert linked_violations(linked) == []
    linked.edit("docs/capabilities/b.md", "## Purpose\n\np", "## Purpose\n\nMore.")  # active, no links
    assert linked_violations(linked) == []


def test_a_trailer_exempts_the_node_that_changed(linked):
    linked.edit("docs/capabilities/a.md", "## Purpose\n\np", "## Purpose\n\nMore.")
    linked.git("add", "--all")
    linked.git("commit", "--quiet", "-m", "wording\n\nDecision-Impact: none [CAP-a] (wording only)")
    found = [(d.rule, d.severity) for d in check(linked, base="HEAD~1") if d.node == "CAP-a"]
    assert found == [("bondstone/exemption-used", "info")]


def test_a_target_that_is_an_item_changes_with_its_document(repo):
    repo.bridge("covers", """
        id: covers
        version: 1.0.0
        requires: {adr: "^1", capability: "^1"}
        links:
          covers: {from: adr:Decision, to: capability:Requirement}
    """)
    rule = {"id": "decision-updates-requirements", "on_change": {"paths": ["docs/adr/**"]},
            "require": [{"link_changed": "covers"}]}
    standard(repo, bridges=["adr-capability@1", "covers@1"], rules=[rule])
    repo.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed", extra="covers: [REQ-AA-001]\n"))
    repo.commit("link a decision to a requirement")
    repo.edit("docs/adr/ADR-001-a.md", "## Context\n\nc", "## Context\n\nMore.")
    assert linked_violations(repo) == [("profile/decision-updates-requirements", "ADR-001")]
    repo.edit("docs/capabilities/a.md", "## Purpose\n\np", "## Purpose\n\nMore.")
    assert linked_violations(repo) == []


def test_link_changed_inside_any(linked):
    rule = {**LINKED_RULE, "require": [{"any": [
        {"link_changed": "constrained_by"}, {"changed": {"type": "adr:Decision"}, "min": 1}]}]}
    standard(linked, code={"include": ["src/**/*.py"]}, rules=[rule])
    linked.commit("either")
    linked.edit("docs/capabilities/a.md", "## Purpose\n\np", "## Purpose\n\nMore.")
    diag = one(linked, "profile/capability-updates-its-decisions")
    assert "needs an update of the 'constrained_by' target(s) ADR-001 (named by CAP-a)" in diag.message
    linked.edit("docs/adr/ADR-002-b.md", "owner: me", "owner: you")
    assert linked_violations(linked) == []


def test_link_changed_must_name_a_link_and_belongs_to_diff_rules(project):
    from bondstone.config import load_config
    standard(project, rules=[
        {**LINKED_RULE, "require": [{"link_changed": "constrains"}]},
        {"id": "node-rule", "when": {"type": "adr:Decision"}, "require": [{"link_changed": "constrained_by"}]},
    ])
    assert [d.message for d in load_config(project.root).errors] == [
        "profile/capability-updates-its-decisions: unknown link 'constrains'",
        "profile/node-rule: clause `link_changed` is not available in a node rule (`when`)",
    ]


def test_context_names_the_targets_that_must_change(linked):
    from bondstone.config import load_config
    from bondstone.context import context_for, to_text
    from bondstone.graph import build_graph
    cfg = load_config(linked.root)
    text = to_text(context_for(cfg, build_graph(cfg), ["docs/capabilities/a.md"]))
    assert ("      asks that every document that a changed document matching type=capability:Capability "
            "status=active names under `constrained_by` changes too\n"
            "      must change: ADR-001\n") in text
