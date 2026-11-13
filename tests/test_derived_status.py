"""The derived-status trait: a document's status comes from the files next to it."""

import pytest
from conftest import Project, check

from bondstone import agent, edit
from bondstone.config import load_config
from bondstone.graph import all_checked, build_graph
from bondstone.model import Refused

PACK = """
    id: kit
    version: 1.0.0
    types:
      Feature:
        id: "{n:03d}-{slug}"
        path: "specs/{id}/spec.md"
        traits:
          derived-status:
            implemented: {all_checked: tasks.md}
            planned: {exists: plan.md}
            specified: {exists: spec.md}
    rules:
      - id: implemented-has-summary
        description: An implemented feature has a summary.
        when: {type: Feature, status: implemented}
        require: [{section: Summary}]
"""
SPEC = "---\nid: 001-login\ntype: kit:Feature\ntitle: Login\n---\n\n# Login\n"


@pytest.fixture
def feature(project) -> Project:
    project.pack("kit", PACK).profile(packs=["kit@1"])
    return project.write("specs/001-login/spec.md", SPEC)


def status(project: Project) -> str | None:
    cfg = load_config(project.root)
    assert cfg.errors == [], [d.message for d in cfg.errors]
    return build_graph(cfg).by_id["001-login"].status


def test_the_first_status_whose_condition_holds_wins(feature):
    assert status(feature) == "specified"
    feature.write("specs/001-login/plan.md", "# Plan\n")
    assert status(feature) == "planned"
    feature.write("specs/001-login/tasks.md", "# Tasks\n\n- [x] T001 Do it\n- [ ] T002 Test it\n")
    assert status(feature) == "planned"
    feature.write("specs/001-login/tasks.md", "# Tasks\n\n- [x] T001 Do it\n  - [X] T002 Test it\n* [x] T003 Ship\n")
    assert status(feature) == "implemented"
    (feature.root / "specs/001-login/plan.md").unlink()
    assert status(feature) == "implemented"  # the order of the trait decides, not the order of the work


def test_a_task_list_without_checkboxes_is_not_done():
    assert all_checked("- [x] a\n- [X] b\n")
    assert not all_checked("- [x] a\n- [ ] b\n")
    assert not all_checked("# Tasks\n\nNothing yet.\n")
    assert not all_checked("")
    assert all_checked("1. intro\n\n   - [x] nested\n")


def test_a_document_without_a_condition_that_holds_has_no_status(project):
    project.pack("kit", PACK.replace("specified: {exists: spec.md}", "specified: {exists: research.md}"))
    project.profile(packs=["kit@1"]).write("specs/001-login/spec.md", SPEC)
    assert status(project) is None
    assert check(project) == []


def test_the_companion_files_are_remembered_and_read_from_the_documents_folder(feature):
    node = build_graph(load_config(feature.root)).by_id["001-login"]
    assert node.companions == ["specs/001-login/tasks.md", "specs/001-login/plan.md"]  # spec.md is the document


def test_rules_select_on_the_derived_status(feature):
    assert check(feature) == []
    feature.write("specs/001-login/tasks.md", "- [x] T001\n")
    assert [(d.rule, d.node) for d in check(feature)] == [("kit/implemented-has-summary", "001-login")]


def test_a_status_in_frontmatter_is_refused(feature):
    feature.edit("specs/001-login/spec.md", "title: Login\n", "title: Login\nstatus: implemented\n")
    found = check(feature)
    assert [(d.rule, d.line, d.message, d.hint) for d in found] == [(
        "bondstone/field-unknown", 5, "`status` cannot be set for kit:Feature: it is derived from files",
        "Remove `status` from the frontmatter.")]
    assert status(feature) == "specified"


def test_the_status_command_refuses_a_derived_status(feature):
    cfg = load_config(feature.root)
    with pytest.raises(Refused, match=r"whose status is derived from its files \(tasks.md, plan.md, spec.md\)"):
        edit.change_status(cfg, build_graph(cfg), "001-login", "implemented")


def test_the_agent_instructions_say_where_the_status_comes_from(feature):
    text = agent.instructions(load_config(feature.root))
    assert ("- status: taken from the files in the document's folder, never written in frontmatter; the first that "
            "holds: `implemented` when every task in `tasks.md` is ticked; `planned` when `plan.md` exists; "
            "`specified` when `spec.md` exists") in text


@pytest.mark.parametrize("change,message", [
    (("traits:", "traits:\n          lifecycle: {statuses: [specified]}"),
     "types.Feature: a type takes its status from `lifecycle` or from `derived-status`, not from both"),
    (("planned: {exists: plan.md}", "planned: {exists: ../plan.md}"),
     "types.Feature: derived-status.planned: '../plan.md' must be a path inside the document's folder"),
    (("planned: {exists: plan.md}", "planned: {exists: plan.md, all_checked: tasks.md}"),
     "types.Feature.traits.derived-status.planned: expected exactly one of `exists` or `all_checked`, "
     'got {"exists": "plan.md", "all_checked": "tasks.md"}'),
    (("derived-status:", "code-traceable: {when: [shipped]}\n          derived-status:"),
     "types.Feature: code-traceable.when: 'shipped' is not one of the derived statuses"),
])
def test_the_trait_is_validated(project, change, message):
    project.pack("kit", PACK.replace(*change)).profile(packs=["kit@1"])
    assert [d.message for d in load_config(project.root).errors] == [message]


def test_other_traits_may_name_derived_statuses(project):
    project.pack("kit", PACK.replace("derived-status:", "code-traceable: {when: [implemented]}\n          derived-status:"))
    project.profile(packs=["kit@1"])
    assert load_config(project.root).errors == []


def test_an_embedded_type_cannot_derive_its_status(project):
    project.pack("kit", """
        id: kit
        version: 1.0.0
        types:
          Doc: {id: "D-{n}", path: "docs/{id}.md", items: {type: Part}}
          Part: {embedded: true, traits: {derived-status: {done: {exists: done.md}}}}
    """).profile(packs=["kit@1"])
    assert [d.message for d in load_config(project.root).errors] == [
        "types.Part: derived-status: an embedded type has no folder of its own to derive a status from"]


# ----------------------------------------------------------------------- changes


RULE = {"id": "code-has-feature", "description": "Code changes come with a feature.",
        "on_change": {"paths": ["src/**"]}, "require": [{"changed": {"type": "kit:Feature"}, "min": 1}]}


def test_a_change_to_a_companion_file_is_a_change_to_the_document(project):
    project.init().pack("kit", PACK).profile(packs=["kit@1"], rules=[RULE])
    project.write("specs/001-login/spec.md", SPEC).write("specs/001-login/tasks.md", "- [ ] T001\n")
    project.write("src/code.py", "x = 1\n").write("specs/001-login/research.md", "notes\n")
    project.commit("first")

    def fired() -> list[str]:
        return [d.rule for d in check(project, base="HEAD") if d.rule == "profile/code-has-feature"]

    project.edit("src/code.py", "x = 1", "x = 2")
    assert fired() == ["profile/code-has-feature"]
    project.edit("specs/001-login/research.md", "notes", "more notes")  # not a file the status is derived from
    assert fired() == ["profile/code-has-feature"]
    project.edit("specs/001-login/tasks.md", "- [ ] T001", "- [x] T001")
    assert fired() == []
    project.git("checkout", "--quiet", "specs")
    project.write("specs/001-login/plan.md", "# Plan\n")  # a companion that is new
    assert fired() == []
