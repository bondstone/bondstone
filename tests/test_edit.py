"""`new`, `status` and `supersede`: commands that change documents and leave the repository valid."""

import datetime as dt
import json

import pytest
from conftest import ADR_PACK, CAPABILITY_PACK, Project, adr, capability, check, standard
from test_cli import run

from bondstone.config import load_config
from bondstone.edit import (
    change_status,
    new_document,
    replace_target,
    set_field,
    set_item_status,
    slugify,
    supersede,
)
from bondstone.graph import build_graph
from bondstone.model import Refused

TODAY = dt.date(2026, 11, 12)

TEMPLATE = "## Context\n\n<!-- todo: context -->\n\n## Decision\n\n{title} ({id}).\n\n## Consequences\n\nc\n"


@pytest.fixture
def repo(project) -> Project:
    project.pack("adr", ADR_PACK.replace('path: "docs/adr/{id}-{slug}.md"',
                                         'path: "docs/adr/{id}-{slug}.md"\n        template: templates/decision.md'))
    project.write(".bondstone/packs/adr/templates/decision.md", TEMPLATE)
    project.pack("capability", CAPABILITY_PACK)
    from conftest import ADR_CAPABILITY_BRIDGE
    project.bridge("adr-capability", ADR_CAPABILITY_BRIDGE)
    project.profile(packs=["adr@1", "capability@1"], bridges=["adr-capability@1"], defaults={"owner": "ann"},
                    overrides={"bondstone/view-stale": "ignore"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "accepted"))
    project.write("docs/capabilities/a.md", capability("CAP-a", "AA", extra="constrained_by: [ADR-002]\n"))
    return project


def load(project: Project):
    cfg = load_config(project.root)
    assert cfg.errors == [], [d.message for d in cfg.errors]
    return cfg, build_graph(cfg)


def new(project: Project, type_name: str, title: str, **sets):
    return new_document(*load(project), type_name, title, sets, TODAY)


def rules(project: Project) -> list[tuple[str, str]]:
    return [(d.rule, d.severity) for d in check(project)]


# --------------------------------------------------------------------------- text edits


def test_slugify():
    assert slugify("Store habits locally, with SQLite!") == "store-habits-locally-with-sqlite"
    assert slugify("Zażółć gęślą") == "za-g-l"  # letters outside a-z are separators
    assert slugify("  ") == "untitled"
    assert len(slugify("word " * 40)) <= 60 and not slugify("word " * 40).endswith("-")


DOC = "---\n# the id\nid: ADR-001\nstatus: proposed   # for now\ntags:\n  - a\n  - b\nlinks: [ADR-002, ADR-020]\n---\n\nBody: status: x\n"


def test_set_field_replaces_one_line_and_keeps_the_rest():
    assert set_field(DOC, "status", "accepted") == DOC.replace("status: proposed   # for now", "status: accepted")
    assert set_field(DOC, "tags", ["c"]) == DOC.replace("tags:\n  - a\n  - b\n", "tags: [c]\n")


def test_set_field_adds_a_missing_key_at_the_end_of_the_frontmatter():
    assert set_field(DOC, "owner", "ann") == DOC.replace("links: [ADR-002, ADR-020]\n---", "links: [ADR-002, ADR-020]\nowner: ann\n---")


def test_set_field_quotes_what_yaml_would_misread():
    assert "title: 'Snooze: later'" in set_field(DOC, "title", "Snooze: later")
    assert "flag: 'no'" in set_field(DOC, "flag", "no")


def test_set_field_rewrites_flow_style_frontmatter_as_one_key_per_line():
    flow = "---\n{id: ADR-001, status: proposed, tags: [a, b]}\n---\nbody\n"
    assert set_field(flow, "status", "accepted") == "---\nid: ADR-001\nstatus: accepted\ntags: [a, b]\n---\nbody\n"


def test_set_field_needs_frontmatter():
    with pytest.raises(Refused, match="no frontmatter"):
        set_field("# just text\n", "status", "x")


def test_replace_target_only_touches_the_whole_id_in_that_key():
    text, changed = replace_target(DOC, "links", "ADR-002", "ADR-009")
    assert changed and text == DOC.replace("links: [ADR-002, ADR-020]", "links: [ADR-009, ADR-020]")
    assert replace_target(DOC, "links", "ADR-02", "ADR-009") == (DOC, False)
    assert replace_target(DOC, "missing", "ADR-002", "ADR-009") == (DOC, False)
    block = "---\nlinks:\n  - ADR-002\n  - ADR-003\n---\n"
    assert replace_target(block, "links", "ADR-003", "ADR-004")[0] == block.replace("ADR-003", "ADR-004")


ITEM = "## Requirements\n\n### REQ-AA-001: Thing\n\nThe system SHALL.\n"


def test_set_item_status_adds_the_line_or_changes_the_one_that_is_there():
    added = set_item_status(ITEM, 3, None, "planned")
    assert added == "## Requirements\n\n### REQ-AA-001: Thing\n\nStatus: planned\n\nThe system SHALL.\n"
    assert set_item_status(added, 3, 5, "removed") == added.replace("planned", "removed")
    assert set_item_status(ITEM.replace("\nThe system", "The system"), 3, None, "planned") == added


def test_set_item_status_refuses_a_line_that_moved():
    with pytest.raises(Refused, match="not a `Status:` line"):
        set_item_status(ITEM, 3, 5, "planned")


# --------------------------------------------------------------------------- new


def test_new_takes_the_next_id_the_types_path_and_the_template(repo):
    created = new(repo, "adr:Decision", "Use a queue: why not?")
    assert (created.id, created.path) == ("ADR-003", "docs/adr/ADR-003-use-a-queue-why-not.md")
    assert repo.read(created.path) == (
        "---\nid: ADR-003\ntype: adr:Decision\ntitle: 'Use a queue: why not?'\nstatus: proposed\nowner: ann\n"
        "date: 2026-11-12\n---\n\n## Context\n\n<!-- todo: context -->\n\n## Decision\n\n"
        "Use a queue: why not? (ADR-003).\n\n## Consequences\n\nc\n")


def test_a_scaffolded_document_passes_check_with_placeholder_warnings_only(repo):
    before = rules(repo)
    new(repo, "adr:Decision", "Use a queue")
    assert [r for r in rules(repo) if r not in before] == [("bondstone/todo-left", "warn")]


def test_new_accepts_an_unqualified_type_and_numbers_after_the_highest_id(repo):
    repo.write("docs/adr/ADR-041-z.md", adr("ADR-041", "proposed"))
    assert new(repo, "Decision", "Next one").id == "ADR-042"


def test_new_without_a_template_writes_the_required_sections(repo):
    repo.pack("adr", ADR_PACK)
    created = new(repo, "Decision", "No template")
    assert repo.read(created.path).endswith(
        "---\n\n## Context\n\n<!-- todo: write this section -->\n\n## Decision\n\n<!-- todo: write this section -->\n\n"
        "## Consequences\n\n<!-- todo: write this section -->\n")


def test_new_sets_fields_and_links(repo):
    created = new(repo, "capability:Capability", "Sync", code="SYN", constrained_by=["ADR-002"], depends_on="CAP-a")
    assert (created.id, created.path) == ("CAP-sync", "docs/capabilities/sync.md")
    head = repo.read(created.path).split("---\n")[1]
    assert head == ("id: CAP-sync\ntype: capability:Capability\ntitle: Sync\nstatus: draft\nowner: ann\ncode: SYN\n"
                    "constrained_by: [ADR-002]\ndepends_on: [CAP-a]\n")


def test_new_lets_the_id_the_slug_the_status_and_the_owner_be_set(repo):
    created = new(repo, "Decision", "A title", id="ADR-100", slug="short", status="accepted", owner="bob",
                  date=dt.date(2026, 1, 2))
    assert created.path == "docs/adr/ADR-100-short.md"
    text = repo.read(created.path)
    assert "status: accepted\nowner: bob\ndate: 2026-01-02\n" in text


@pytest.mark.parametrize("type_name, title, sets, message", [
    ("adr:Nope", "T", {}, r"unknown type 'adr:Nope' \(known: adr:Decision, capability:Capability\)"),
    ("Requirement", "T", {}, "capability:Requirement is an item type; add it as a heading inside a capability:Capability"),
    ("Capability", "T", {}, r"capability:Capability requires code; pass --set code=\.\.\."),
    ("Decision", "  ", {}, "--title is empty"),
    ("Decision", "T", {"colour": "red"}, r"--set colour: adr:Decision has no such field or link \(known: .*title"),
    ("Decision", "T", {"supersedes": "ADR-009"}, "no node with id ADR-009"),
    ("Decision", "T", {"id": "ADR-001"}, "id 'ADR-001' is already used by docs/adr/ADR-001-a.md"),
    ("Capability", "A", {"code": "AB", "slug": "a"}, "id 'CAP-a' is already used"),
])
def test_new_refuses_what_check_would_reject(repo, type_name, title, sets, message):
    before = sorted(p.name for p in repo.root.rglob("*.md"))
    with pytest.raises(Refused, match=message):
        new(repo, type_name, title, **sets)
    assert sorted(p.name for p in repo.root.rglob("*.md")) == before


def test_new_refuses_to_overwrite_a_file(repo):
    repo.write("docs/adr/ADR-003-taken.md", "not a document\n")
    with pytest.raises(Refused, match="docs/adr/ADR-003-taken.md already exists"):
        new(repo, "Decision", "Taken")


def test_new_needs_an_owner_and_required_links(project):
    standard(project.init())
    pack = project.read(".bondstone/packs/adr/pack.yaml").replace("max: 1}", "max: 1, min: 1}")
    project.pack("adr", pack)
    project.git("config", "user.name", "")
    with pytest.raises(Refused, match="needs an owner; pass --set owner=..., set `user.name` in git"):
        new(project, "Decision", "T")
    with pytest.raises(Refused, match="needs at least 1 'supersedes' link"):
        new(project, "Decision", "T", owner="ann")


def test_the_owner_is_the_git_user_and_the_profile_default_is_the_fallback(repo):
    assert "owner: ann\n" in repo.read(new(repo, "Decision", "No git user here").path)  # `defaults.owner`
    repo.init().git("config", "user.name", "Git User")
    assert "owner: Git User\n" in repo.read(new(repo, "Decision", "With a git user").path)
    assert "owner: bob\n" in repo.read(new(repo, "Decision", "Set by hand", owner="bob").path)


# --------------------------------------------------------------------------- status


def status(project: Project, node_id: str, new_status: str):
    return change_status(*load(project), node_id, new_status)


def test_status_changes_one_line_of_a_document(repo):
    before = repo.read("docs/adr/ADR-001-a.md")
    change = status(repo, "ADR-001", "accepted")
    assert (change.old, change.new, change.changed, change.path) == ("proposed", "accepted", True, "docs/adr/ADR-001-a.md")
    assert repo.read("docs/adr/ADR-001-a.md") == before.replace("status: proposed", "status: accepted")


def test_status_that_is_already_set_changes_nothing(repo):
    before = repo.read("docs/adr/ADR-001-a.md")
    assert status(repo, "ADR-001", "proposed").changed is False
    assert repo.read("docs/adr/ADR-001-a.md") == before


@pytest.mark.parametrize("node_id, new_status, message", [
    ("ADR-009", "accepted", "no node with id 'ADR-009'"),
    ("ADR-001", "done", r"'done' is not a status of adr:Decision \(statuses: proposed, accepted"),
    ("ADR-002", "proposed", r"ADR-002 is 'accepted', which cannot become 'proposed' \(allowed: deprecated, superseded\)"),
])
def test_status_refuses_what_the_lifecycle_does_not_allow(repo, node_id, new_status, message):
    with pytest.raises(Refused, match=message):
        status(repo, node_id, new_status)


def test_status_refuses_a_type_without_a_lifecycle(repo):
    repo.pack("capability", CAPABILITY_PACK.replace(
        "lifecycle: {statuses: [planned, active, removed], default: active}\n", "").replace(
        "code-traceable: {coverage: warn, when: [active], retired: [removed]}", "code-traceable: {coverage: warn}"))
    with pytest.raises(Refused, match="REQ-AA-001 is a capability:Requirement, which has no lifecycle"):
        status(repo, "REQ-AA-001", "planned")


def test_status_respects_an_immutable_document_whose_status_may_not_change(repo):
    repo.pack("adr", repo.read(".bondstone/packs/adr/pack.yaml").replace("allow: [status]", "allow: []"))
    with pytest.raises(Refused, match="ADR-002 is immutable in status 'accepted'"):
        status(repo, "ADR-002", "deprecated")
    assert status(repo, "ADR-001", "accepted").changed  # proposed is not immutable


def test_status_of_an_item_is_a_line_under_its_heading(repo):
    path = "docs/capabilities/a.md"
    before = repo.read(path)
    assert status(repo, "REQ-AA-001", "planned").old == "active"
    assert repo.read(path) == before.replace("### REQ-AA-001: Thing\n", "### REQ-AA-001: Thing\n\nStatus: planned\n")
    status(repo, "REQ-AA-001", "removed")
    assert "Status: removed\n" in repo.read(path)
    status(repo, "REQ-AA-001", "active")  # the default status is written out too
    assert repo.read(path) == before.replace("### REQ-AA-001: Thing\n", "### REQ-AA-001: Thing\n\nStatus: active\n")
    assert status(repo, "REQ-AA-001", "active").changed is False


def test_status_of_an_item_follows_its_transitions(repo):
    repo.pack("capability", CAPABILITY_PACK.replace(
        "default: active}", "default: active, transitions: {planned: [active], active: [removed]}}"))
    with pytest.raises(Refused, match=r"REQ-AA-001 is 'active', which cannot become 'planned' \(allowed: removed\)"):
        status(repo, "REQ-AA-001", "planned")


# --------------------------------------------------------------------------- supersede


def test_supersede_creates_the_successor_marks_the_old_one_and_moves_links(repo):
    result = supersede(*load(repo), "ADR-002", "Do it better", None, TODAY)
    assert (result.created.id, result.created.path) == ("ADR-003", "docs/adr/ADR-003-do-it-better.md")
    assert result.updated == ["docs/adr/ADR-002-b.md (status: accepted -> superseded)",
                              "docs/capabilities/a.md (constrained_by: ADR-002 -> ADR-003)"]
    assert result.skipped == []
    assert "status: proposed\nowner: ann\ndate: 2026-11-12\nsupersedes: [ADR-002]\n" in repo.read(result.created.path)
    assert "status: superseded\n" in repo.read("docs/adr/ADR-002-b.md")
    assert "constrained_by: [ADR-003]\n" in repo.read("docs/capabilities/a.md")
    assert [r for r in rules(repo) if r[1] == "error"] == []


def test_supersede_leaves_links_of_immutable_documents_and_says_so(repo):
    repo.pack("adr", repo.read(".bondstone/packs/adr/pack.yaml").replace(
        "links:\n", "links:\n  relates_to: {from: Decision, to: Decision}\n", 1))
    repo.write("docs/adr/ADR-003-c.md", adr("ADR-003", "accepted", extra="relates_to: [ADR-002]\n"))
    repo.write("docs/adr/ADR-004-d.md", adr("ADR-004", "proposed", extra="adr:relates_to: [ADR-002]\n"))
    result = supersede(*load(repo), "ADR-002", "Do it better", None, TODAY)
    assert result.skipped == ["docs/adr/ADR-003-c.md (relates_to: ADR-002): ADR-003 is immutable in status 'accepted'"]
    assert "docs/adr/ADR-004-d.md (relates_to: ADR-002 -> ADR-005)" in result.updated
    assert "adr:relates_to: [ADR-005]\n" in repo.read("docs/adr/ADR-004-d.md")
    assert "relates_to: [ADR-002]\n" in repo.read("docs/adr/ADR-003-c.md")


@pytest.mark.parametrize("node_id, message", [
    ("ADR-009", "no node with id 'ADR-009'"),
    ("CAP-a", "CAP-a is a capability:Capability, which is not supersedable"),
    ("ADR-001", r"ADR-001 is 'proposed', which cannot become 'superseded' \(allowed: accepted, rejected\)"),
])
def test_supersede_refuses_and_changes_nothing(repo, node_id, message):
    before = {p: p.read_text(encoding="utf-8") for p in repo.root.rglob("*.md")}
    with pytest.raises(Refused, match=message):
        supersede(*load(repo), node_id, "New", None, TODAY)
    assert {p: p.read_text(encoding="utf-8") for p in repo.root.rglob("*.md")} == before


def test_a_document_is_superseded_only_once(repo):
    supersede(*load(repo), "ADR-002", "Second", None, TODAY)
    with pytest.raises(Refused, match="ADR-002 is already superseded"):
        supersede(*load(repo), "ADR-002", "Third", None, TODAY)


def test_supersede_passes_fields_to_the_successor(repo):
    result = supersede(*load(repo), "ADR-002", "With deciders", {"deciders": ["ann", "bob"]}, TODAY)
    assert "deciders: [ann, bob]\nsupersedes: [ADR-002]\n" in repo.read(result.created.path)


# --------------------------------------------------------------------------- commands


@pytest.fixture
def cli(repo) -> Project:
    """The repository with stale views treated as errors, and its views generated."""
    repo.profile(packs=["adr@1", "capability@1"], bridges=["adr-capability@1"], defaults={"owner": "ann"})
    from bondstone.cli import main
    assert main(["--root", str(repo.root), "gen"]) == 0
    return repo


def test_new_command_regenerates_views(cli, capsys):
    capsys.readouterr()
    code, out, err = run(capsys, "--root", cli.root, "new", "adr:Decision", "--title", "Use a queue")
    assert (code, err) == (0, "")
    assert out == "created docs/adr/ADR-003-use-a-queue.md (ADR-003)\nwrote docs/generated/decisions.md\n"
    assert "ADR-003" in cli.read("docs/generated/decisions.md")
    code, out, _ = run(capsys, "--root", cli.root, "check")
    assert code == 0 and "bondstone/view-stale" not in out


def test_new_command_json_and_set(cli, capsys):
    capsys.readouterr()
    code, out, _ = run(capsys, "--root", cli.root, "new", "Capability", "--title", "Sync", "--set", "code=SYN",
                       "--set", "constrained_by=[ADR-002]", "--format", "json")
    assert code == 0
    assert json.loads(out) == {"version": 1, "id": "CAP-sync", "path": "docs/capabilities/sync.md",
                               "views": []}
    assert "constrained_by: [ADR-002]\n" in cli.read("docs/capabilities/sync.md")


def test_refusals_exit_with_1_and_write_nothing(cli, capsys):
    capsys.readouterr()
    code, out, err = run(capsys, "--root", cli.root, "new", "Capability", "--title", "Sync")
    assert (code, out, err) == (1, "", "bondstone: capability:Capability requires code; pass --set code=...\n")
    code, out, err = run(capsys, "--root", cli.root, "new", "Decision", "--title", "T", "--set", "broken")
    assert (code, out, err) == (1, "", "bondstone: --set expects KEY=VALUE, got 'broken'\n")
    code, out, err = run(capsys, "--root", cli.root, "status", "ADR-002", "proposed")
    assert (code, out) == (1, "") and "cannot become 'proposed'" in err


def test_status_command(cli, capsys):
    capsys.readouterr()
    code, out, _ = run(capsys, "--root", cli.root, "status", "ADR-001", "accepted")
    assert (code, out) == (0, "ADR-001: proposed -> accepted (docs/adr/ADR-001-a.md)\nwrote docs/generated/decisions.md\n")
    assert run(capsys, "--root", cli.root, "status", "ADR-001", "accepted")[:2] == (0, "ADR-001 is already accepted\n")
    code, out, _ = run(capsys, "--root", cli.root, "status", "REQ-AA-001", "planned", "--format", "json")
    assert json.loads(out) == {"version": 1, "id": "REQ-AA-001", "path": "docs/capabilities/a.md", "old": "active",
                               "new": "planned", "changed": True, "views": []}


def test_supersede_command(cli, capsys):
    capsys.readouterr()
    code, out, err = run(capsys, "--root", cli.root, "supersede", "ADR-002", "--title", "Do it better")
    assert (code, err) == (0, "")
    assert out == ("created docs/adr/ADR-003-do-it-better.md (ADR-003)\n"
                   "updated docs/adr/ADR-002-b.md (status: accepted -> superseded)\n"
                   "updated docs/capabilities/a.md (constrained_by: ADR-002 -> ADR-003)\n"
                   "wrote docs/generated/decisions.md\n")
    code, out, _ = run(capsys, "--root", cli.root, "check")
    assert code == 0 and out.endswith("✓ 0 error(s), 1 warning(s), 5 nodes\n")
