"""`bondstone context`: what to read before editing, and which diff rules will fire."""

import json

import pytest
from conftest import Project, adr, capability, standard
from test_cli import run

from bondstone.config import load_config
from bondstone.context import context_for, context_since, normalize, to_text
from bondstone.git import GitRepository
from bondstone.graph import build_graph
from bondstone.model import Refused

RULE = {
    "id": "code-updates-spec",
    "description": "Code changes update the living spec they implement.",
    "on_change": {"paths": ["src/**"]},
    "require": [{"changed": {"role": "living-spec"}, "traced": True}],
    "exempt": {"trailer": "Spec-Impact"},
    "hint": "Update the spec.",
}
CODE = "# bondstone: REQ-AA-001\ndef first():\n    return 1\n\n\n# bondstone: REQ-BB-001\ndef second():\n    return 2\n"


@pytest.fixture
def repo(project) -> Project:
    standard(project.init(), code={"include": ["src/**/*.py"]}, rules=[RULE])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed"))
    project.write("docs/capabilities/a.md", capability("CAP-a", "AA", extra="constrained_by: [ADR-001]\n"))
    project.write("docs/capabilities/b.md", capability("CAP-b", "BB", extra="depends_on: [CAP-a]\n"))
    project.write("src/code.py", CODE)
    project.write("src/plain.py", "x = 1\n")
    project.commit("first")
    return project


def load(project: Project):
    cfg = load_config(project.root)
    assert cfg.errors == []
    return cfg, build_graph(cfg)


def reasons(context) -> dict[str, list[str]]:
    return {entry.node.id: entry.reasons for entry in context.entries}


# --------------------------------------------------------------------------- --for


def test_code_leads_to_its_requirements_their_documents_and_the_linked_decisions(repo):
    found = context_for(*load(repo), ["src/code.py"])
    assert reasons(found) == {
        "REQ-AA-001": ["tagged in src/code.py:1"],
        "CAP-a": ["document of REQ-AA-001", "CAP-b links to it (depends_on)"],
        "REQ-BB-001": ["tagged in src/code.py:6"],
        "CAP-b": ["document of REQ-BB-001", "it links to CAP-a (depends_on)"],
        "ADR-001": ["CAP-a links to it (constrained_by)"],
    }


def test_an_immutable_document_is_marked(repo):
    notes = {entry.node.id: entry.note for entry in context_for(*load(repo), ["src/code.py"]).entries}
    assert notes["ADR-001"] == ("immutable in status 'accepted'; "
                                "run `bondstone supersede ADR-001 --title ...` instead of editing it")
    assert notes["CAP-a"] is None
    found = context_for(*load(repo), ["docs/adr/ADR-002-b.md"])
    assert [(entry.node.id, entry.reasons, entry.note) for entry in found.entries] == [
        ("ADR-002", ["the document itself"], None)]


def test_a_document_path_lists_the_document_and_what_links_to_it(repo):
    assert reasons(context_for(*load(repo), ["docs/adr/ADR-001-a.md"])) == {
        "ADR-001": ["the document itself"], "CAP-a": ["it links to ADR-001 (constrained_by)"]}


def test_the_rules_that_will_fire_and_the_documents_they_want_changed(repo):
    found = context_for(*load(repo), ["src/code.py"])
    assert [rule.to_dict() for rule in found.rules] == [{
        "id": "profile/code-updates-spec", "severity": "error",
        "description": "Code changes update the living spec they implement.",
        "asks": ["every document matching role=living-spec that is tagged in the changed code changes too"],
        "must_change": ["CAP-a", "CAP-b"], "hint": "Update the spec.", "exempt": "Spec-Impact"}]


def test_untagged_and_unwatched_files(repo):
    plain = context_for(*load(repo), ["src/plain.py"])
    assert plain.entries == [] and [rule.must_change for rule in plain.rules] == [[]]
    readme = context_for(*load(repo), ["README.md"])
    assert (readme.entries, readme.rules) == ([], [])
    assert to_text(readme) == "No document is traced to README.md.\n\nNo diff rule watches these files.\n"


def test_a_file_that_does_not_exist_yet_counts_as_added(repo):
    standard(repo, code={"include": ["src/**/*.py"]}, rules=[{**RULE, "on_change": {"paths": ["src/**"], "kinds": ["added"]}}])
    assert [rule.id for rule in context_for(*load(repo), ["src/new.py"]).rules] == ["profile/code-updates-spec"]
    assert context_for(*load(repo), ["src/code.py"]).rules == []


def test_a_rule_that_watches_the_repositorys_code(repo):
    standard(repo, code={"include": ["src/**/*.py"], "exclude": ["src/plain.py"]},
             rules=[{**RULE, "on_change": {"code": True}}])
    assert [rule.must_change for rule in context_for(*load(repo), ["src/code.py"]).rules] == [["CAP-a", "CAP-b"]]
    assert context_for(*load(repo), ["src/plain.py"]).rules == []  # excluded from the code globs
    assert context_for(*load(repo), ["README.md"]).rules == []


def test_a_rule_overridden_to_ignore_is_left_out(repo):
    standard(repo, code={"include": ["src/**/*.py"]}, rules=[RULE], overrides={"profile/code-updates-spec": "ignore"})
    assert context_for(*load(repo), ["src/code.py"]).rules == []


def test_a_folder_stands_for_the_files_in_it(repo):
    found = context_for(*load(repo), ["src"])
    assert found.paths == ["src/code.py", "src/plain.py"]
    assert "REQ-AA-001" in reasons(found)


def test_other_clauses_are_described(repo):
    rule = {**RULE, "require": [{"changed": {"role": "living-spec"}, "traced": True, "min": 1},
                                {"any": [{"exists": {"type": "adr:Decision", "status": "accepted"}},
                                         {"changed": {"type": "adr:Decision"}, "min": 2}]}]}
    standard(repo, code={"include": ["src/**/*.py"]}, rules=[rule])
    assert context_for(*load(repo), ["src/plain.py"]).rules[0].asks == [
        "every document matching role=living-spec that is tagged in the changed code changes too, "
        "and at least 1 such document(s) change",
        "one of: 1 document(s) matching type=adr:Decision status=accepted exist; or "
        "2 document(s) matching type=adr:Decision change"]


def test_text_output(repo):
    text = to_text(context_for(*load(repo), ["src/code.py"]))
    assert text.startswith(
        "Read before editing src/code.py:\n"
        "  REQ-AA-001  capability:Requirement  docs/capabilities/a.md:16\n"
        "      Thing (active): tagged in src/code.py:1\n"
        "  CAP-a  capability:Capability  docs/capabilities/a.md\n"
        "      Capability CAP-a (active): document of REQ-AA-001; CAP-b links to it (depends_on)\n")
    assert text.endswith(
        "\nRules that fire when these files change:\n"
        "  error profile/code-updates-spec: Code changes update the living spec they implement.\n"
        "      asks that every document matching role=living-spec that is tagged in the changed code changes too\n"
        "      must change: CAP-a, CAP-b\n"
        "      hint: Update the spec.\n"
        "      a `Spec-Impact: none (<reason>)` commit trailer exempts a change; add one only when the user asks for it\n")


# --------------------------------------------------------------------------- paths


def test_paths_may_be_relative_to_the_current_folder_or_absolute(repo, monkeypatch):
    cfg, _ = load(repo)
    monkeypatch.chdir(repo.root / "src")
    assert normalize(cfg, "code.py") == "src/code.py"
    assert normalize(cfg, "../docs/adr/ADR-001-a.md") == "docs/adr/ADR-001-a.md"
    assert normalize(cfg, str(repo.root / "src" / "code.py")) == "src/code.py"
    assert normalize(cfg, "src/not-yet.py") == "src/not-yet.py"  # falls back to the repository root
    with pytest.raises(Refused, match="is outside the repository"):
        normalize(cfg, str(repo.root.parent / "elsewhere.py"))


# --------------------------------------------------------------------------- --base


def test_base_only_counts_the_regions_that_changed(repo):
    repo.edit("src/code.py", "return 2", "return 20")
    found = context_since(*load(repo), GitRepository(repo.root), "HEAD")
    assert found.paths == ["src/code.py"]
    assert reasons(found) == {"REQ-BB-001": ["tagged in src/code.py"],
                              "CAP-b": ["document of REQ-BB-001"],
                              "CAP-a": ["CAP-b links to it (depends_on)"]}
    assert [rule.must_change for rule in found.rules] == [["CAP-b"]]


def test_base_says_which_documents_already_changed(repo):
    repo.edit("src/code.py", "return 2", "return 20")
    repo.edit("docs/capabilities/b.md", "do the thing", "do the thing well")
    found = context_since(*load(repo), GitRepository(repo.root), "HEAD")
    changed = {entry.node.id: entry.changed for entry in found.entries}
    assert changed == {"CAP-b": True, "REQ-BB-001": True, "CAP-a": False}
    assert "  CAP-b  capability:Capability  docs/capabilities/b.md [changed]\n" in to_text(found)
    assert "  CAP-a  capability:Capability  docs/capabilities/a.md [not changed]\n" in to_text(found)


def test_base_without_changes(repo):
    found = context_since(*load(repo), GitRepository(repo.root), "HEAD")
    assert (found.paths, found.entries, found.rules) == ([], [], [])
    assert to_text(found) == "Nothing changed.\n"


# --------------------------------------------------------------------------- command


def test_context_command(repo, capsys):
    code, out, err = run(capsys, "--root", repo.root, "context", "--for", "src/code.py")
    assert (code, err) == (0, "") and out == to_text(context_for(*load(repo), ["src/code.py"]))
    code, out, _ = run(capsys, "--root", repo.root, "context", "--for", "src/code.py", "src/plain.py", "--format", "json")
    payload = json.loads(out)
    assert code == 0 and payload["version"] == 1 and payload["paths"] == ["src/code.py", "src/plain.py"]
    assert payload["nodes"][0] == {"id": "REQ-AA-001", "type": "capability:Requirement", "path": "docs/capabilities/a.md",
                                   "line": 16, "title": "Thing", "status": "active",
                                   "reasons": ["tagged in src/code.py:1"]}
    assert payload["rules"][0]["must_change"] == ["CAP-a", "CAP-b"]


def test_context_command_with_base(repo, capsys):
    repo.edit("src/code.py", "return 1", "return 10")
    code, out, _ = run(capsys, "--root", repo.root, "context", "--base", "HEAD", "--format", "json")
    payload = json.loads(out)
    assert code == 0 and [node["id"] for node in payload["nodes"]][:2] == ["REQ-AA-001", "CAP-a"]
    assert payload["nodes"][1]["changed"] is False
    code, out, err = run(capsys, "--root", repo.root, "context", "--base", "nope")
    assert (code, out) == (3, "") and "'nope' is not a commit" in err


def test_context_needs_for_or_base(repo, capsys):
    with pytest.raises(SystemExit) as exit_info:
        run(capsys, "--root", repo.root, "context")
    assert exit_info.value.code == 2
    capsys.readouterr()
