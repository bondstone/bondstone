import datetime as dt
import json

import pytest

from bondstone.cli import main
from bondstone.loader import load_config, version_matches
from bondstone.graph import build_graph
from bondstone.scaffold import new_document

from .conftest import adr


@pytest.mark.parametrize("version,spec,ok", [
    ("1.2.0", "1", True), ("2.0.0", "1", False), ("1.2.0", "^1.3", False),
    ("1.4.1", "1.3", True), ("1.0.0", ">=1,<2", True), ("1.0.0", None, True),
])
def test_version_matches(version, spec, ok):
    assert version_matches(version, spec) is ok


def test_missing_pack_and_unmet_bridge(project):
    project.profile(packs=["adr@1", "nope@1"], bridges=["adr-capability@1"])
    messages = [d.message for d in project.check() if d.rule == "bondstone/profile"]
    assert any("'nope' not found" in m for m in messages)
    assert any("requires pack 'capability'" in m for m in messages)


def test_version_mismatch(project):
    project.profile(packs=["adr@2"])
    assert any("no version matches" in d.message for d in project.check())


def test_unbridged_packs_warning(project):
    project.profile(packs=["adr@1", "ost@1"], overrides={"bondstone/view-stale": "off"})
    assert project.rules() == ["bondstone/unbridged-packs"]


def test_unknown_key_and_broken_link(project):
    project.profile(packs=["adr@1"], overrides={"bondstone/view-stale": "off"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted", "supersedes: ADR-009\ncolour: red\n"))
    assert project.rules() == ["bondstone/field-unknown", "bondstone/link-broken"]


def test_explicit_type_outside_paths(project):
    project.profile(packs=["adr@1"], scan=["notes/**/*.md"], overrides={"bondstone/view-stale": "off"})
    project.write("notes/x.md", adr("ADR-001", "accepted").replace("---\nid", "---\ntype: adr:Decision\nid", 1))
    project.write("notes/plain.md", "# not a bondstone doc\n")
    graph = build_graph(load_config(project.root))
    assert [n.id for n in graph.nodes] == ["ADR-001"]
    assert project.rules() == []


def test_overrides_waivers_and_locks(project):
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    project.profile(
        packs=["adr@1"],
        overrides={"bondstone/view-stale": "off", "adr/alternatives-considered": "error"},
        waivers=[
            {"rule": "bondstone/field-unknown", "node": "ADR-001", "reason": "legacy", "expires": tomorrow},
            {"rule": "bondstone/link-broken", "reason": "x", "expires": "2020-01-01"},
            {"rule": "bondstone/id-format", "reason": "never matches"},
            {"rule": "bondstone/section-missing"},
        ],
    )
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted", "colour: red\n",
                                               body="## Context\n\n## Decision\n\n## Consequences\n"))
    diags = {d.rule: d.severity for d in project.check()}
    assert diags == {
        "adr/alternatives-considered": "error",      # raised by override
        "bondstone/waiver-expired": "error",
        "bondstone/waiver-unused": "warn",
        "bondstone/waiver-invalid": "error",          # no reason
    }


def test_locked_rule_cannot_be_loosened(project):
    project.write(".bondstone/packs/strict/pack.yaml", """
        id: strict
        version: 1.0.0
        types:
          Note:
            paths: ["notes/*.md"]
        rules:
          - id: has-summary
            locked: true
            when: {type: Note}
            require: [{section: Summary}]
    """)
    project.profile(packs=["strict@1"], sources=[".bondstone/packs"],
                    overrides={"strict/has-summary": "off"},
                    waivers=[{"rule": "strict/has-summary", "reason": "please"}])
    project.write("notes/a.md", "---\nid: N1\ntitle: A note\n---\n# Body\n")
    rules = project.rules()
    assert "strict/has-summary" in rules
    assert "bondstone/profile" in rules  # override rejected


def test_roles_from_bridges_and_profile_role_rule(project):
    project.profile(
        packs=["adr@1", "capability@1"], bridges=["adr-capability@1"],
        roles={"spec": ["capability:Capability"]},
        overrides={"bondstone/view-stale": "off"},
        rules=[{"id": "specs-have-owner-team", "when": {"role": "spec"}, "require": [{"field": "owner"}]}],
    )
    cfg = load_config(project.root)
    assert cfg.roles["living-spec"] == ["capability:Capability"]  # deduplicated across bridges
    assert cfg.roles["spec"] == ["capability:Capability"]


def test_diff_lifecycle_immutability_and_diff_rule(project):
    project.profile(
        packs=["adr@1", "capability@1"], bridges=["adr-capability@1"],
        code={"include": ["src/**/*.py"]},
        overrides={"bondstone/view-stale": "off", "bondstone/code-coverage": "off"},
        rules=[{"id": "code-needs-spec", "on_change": {"paths": ["src/**"]},
                "require": [{"changed": {"role": "living-spec"}, "min": 1}]}],
    )
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed"))
    project.write("docs/capabilities/a.md", """
        ---
        id: CAP-a
        title: Capability A
        status: active
        owner: me
        code: AA
        constrained_by: [ADR-001]
        ---
        ## Purpose

        p

        ## Requirements

        ### REQ-AA-001: Thing

        The system SHALL do the thing.

        #### Scenario: ok

        - Then fine
    """)
    project.write("src/app.py", "x = 1\n")
    project.git("init", "-q")
    project.commit()
    assert project.rules(base="HEAD") == []

    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted").replace("\nc\n", "\nchanged\n"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "deprecated"))
    project.write("src/app.py", "x = 2  # bondstone: REQ-AA-001\n")
    assert project.rules(base="HEAD") == [
        "bondstone/immutable", "bondstone/status-transition", "profile/code-needs-spec"]

    # status-only change of an accepted ADR is allowed; touching the spec satisfies the diff rule
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "deprecated"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "accepted"))
    text = (project.root / "docs/capabilities/a.md").read_text()
    project.write("docs/capabilities/a.md", text.replace("do the thing", "do the thing well"))
    assert project.rules(base="HEAD", severity="error") == ["adr-capability/constrained-by-live-decision"]


def test_new_document_is_valid_after_filling_todos(project):
    project.profile(packs=["adr@1"], defaults={"owner": "me"}, overrides={"bondstone/view-stale": "off"})
    project.write("docs/adr/ADR-007-old.md", adr("ADR-007", "accepted"))
    cfg = load_config(project.root)
    path = new_document(cfg, build_graph(cfg), "Decision", "Use SQLite", {})
    assert path.name == "ADR-008-use-sqlite.md"
    assert "status: proposed" in path.read_text()
    assert project.rules() == ["bondstone/todo-left"]
    assert [d.severity for d in project.check()] == ["warn"]  # still a draft
    path.write_text(path.read_text().replace("proposed", "accepted"))
    assert [d.severity for d in project.check()] == ["error"]  # accepted with placeholders


def test_cli_json_and_exit_codes(project, capsys):
    project.profile(packs=["adr@1"], overrides={"bondstone/view-stale": "off"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted", "colour: red\n"))
    code = main(["--root", str(project.root), "check", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["summary"]["errors"] == 1
    assert payload["diagnostics"][0]["rule"] == "bondstone/field-unknown"
    assert payload["diagnostics"][0]["line"] == 7

    assert main(["--root", str(project.root), "gen"]) == 0
    assert (project.root / "docs/generated/decisions.md").exists()
    assert main(["--root", str(project.root), "explain", "adr/alternatives-considered"]) == 0
    assert main(["--root", str(project.root), "explain", "nope"]) == 2


def test_code_tags_ignore_non_tag_mentions(project):
    project.profile(packs=["capability@1"], code={"include": ["src/*.py"]},
                    overrides={"bondstone/view-stale": "off"})
    project.write("src/a.py", '''
        MARK = "<!-- bondstone:generated"
        LINK = "bondstone:part_of"
        HINT = "add a `bondstone: <id>` comment"
        # bondstone: REQ-ZZ-001
    ''')
    assert project.rules() == ["bondstone/code-ref-unknown"]


def test_todo_markers_inside_code_are_ignored(project):
    project.profile(packs=["adr@1"], overrides={"bondstone/view-stale": "off"})
    body = ("\n## Context\n\nUse `<!-- todo: ... -->` markers.\n\n```md\n<!-- todo: x -->\n```\n\n"
            "## Decision\n\nd\n\n## Alternatives considered\n\na\n\n## Consequences\n\nx\n")
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted", body=body))
    assert project.rules() == []
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted", body=body + "\n<!-- todo: y -->\n"))
    assert project.rules() == ["bondstone/todo-left"]


def test_init_generates_views_so_fresh_repo_is_clean(project, capsys):
    assert main(["--root", str(project.root), "init", "--packs", "adr@1,capability@1",
                 "--bridges", "adr-capability@1"]) == 0
    assert "wrote docs/generated/decisions.md" in capsys.readouterr().out
    assert project.rules() == []


def _git_project(project, **profile):
    profile.setdefault("overrides", {"bondstone/view-stale": "off"})
    project.profile(**profile)
    project.git("init", "-q")
    return project


def test_new_documents_must_start_in_initial_status(project):
    _git_project(project, packs=["adr@1"])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    project.commit()
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "accepted"))
    assert project.rules(base="HEAD") == ["bondstone/status-initial"]

    # a renamed document is not new
    (project.root / "docs/adr/ADR-002-b.md").unlink()
    project.git("mv", "docs/adr/ADR-001-a.md", "docs/adr/ADR-001-renamed.md")
    project.write("docs/adr/ADR-001-renamed.md", adr("ADR-001", "accepted"))
    assert project.rules(base="HEAD") == []
    # moved without git mv (untracked new path, deleted old path) is also recognised
    project.git("reset", "-q", "--hard")
    (project.root / "docs/adr/ADR-001-a.md").rename(project.root / "docs/adr/ADR-001-moved.md")
    assert project.rules(base="HEAD") == []


def test_create_as_allows_other_creation_statuses(project):
    project.write(".bondstone/packs/note/pack.yaml", """
        id: note
        version: 1.0.0
        types:
          Note:
            paths: ["notes/*.md"]
            traits:
              lifecycle: {statuses: [draft, final], initial: draft, create_as: [draft, final]}
    """)
    _git_project(project, packs=["note@1"], sources=[".bondstone/packs"])
    project.write("notes/a.md", "---\nid: N1\ntitle: A note\nstatus: draft\n---\n")
    project.commit()
    project.write("notes/b.md", "---\nid: N2\ntitle: B note\nstatus: final\n---\n")
    assert project.rules(base="HEAD") == []


CAP = """
---
id: CAP-a
title: Capability A
status: active
owner: me
code: AA
constrained_by: [{adr}]
---
## Purpose

p

## Requirements

### REQ-AA-001: Thing

The system SHALL do the thing.

#### Scenario: ok

- Then fine
"""


def test_supersede_moves_links_and_respects_immutability(project):
    from bondstone.graph import build_graph
    from bondstone.scaffold import supersede
    from bondstone.model import BondstoneError

    project.profile(packs=["adr@1", "capability@1"], bridges=["adr-capability@1"],
                    defaults={"owner": "me"}, overrides={"bondstone/view-stale": "off"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed"))
    project.write("docs/capabilities/a.md", CAP.format(adr="ADR-001, ADR-002"))
    cfg = load_config(project.root)
    result = supersede(cfg, build_graph(cfg), "ADR-001", "Better decision", {})
    assert result.created.name == "ADR-003-better-decision.md"
    assert "supersedes: ADR-001" in result.created.read_text()
    assert "status: superseded" in (project.root / "docs/adr/ADR-001-a.md").read_text()
    assert "constrained_by: [ADR-003, ADR-002]" in (project.root / "docs/capabilities/a.md").read_text()
    assert project.rules(severity="error") == []

    cfg = load_config(project.root)
    with pytest.raises(BondstoneError, match="already superseded"):
        supersede(cfg, build_graph(cfg), "ADR-001", "Again", {})
    with pytest.raises(BondstoneError, match="cannot become 'superseded'"):
        supersede(cfg, build_graph(cfg), "ADR-002", "Too early", {})
    with pytest.raises(BondstoneError, match="not supersedable"):
        supersede(cfg, build_graph(cfg), "CAP-a", "Nope", {})


def test_traced_diff_rule_requires_the_tagged_spec(project):
    _git_project(
        project, packs=["adr@1", "capability@1"], bridges=["adr-capability@1"],
        code={"include": ["src/*.py"]},
        overrides={"bondstone/view-stale": "off", "bondstone/code-coverage": "off"},
        rules=[{"id": "code-needs-spec", "on_change": {"paths": ["src/**"]},
                "require": [{"changed": {"role": "living-spec"}, "traced": True, "min": 1}]}],
    )
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "accepted"))
    project.write("docs/capabilities/a.md", CAP.format(adr="ADR-001"))
    project.write("docs/capabilities/b.md", CAP.format(adr="ADR-001").replace("CAP-a", "CAP-b")
                  .replace("AA", "BB"))
    project.write("src/a.py", "# bondstone: REQ-AA-001\nx = 1\n")
    project.write("src/plain.py", "y = 1\n")
    project.commit()

    project.write("src/a.py", "# bondstone: REQ-AA-001\nx = 2\n")
    project.write("docs/capabilities/b.md", (project.root / "docs/capabilities/b.md").read_text() + "\nmore\n")
    diags = [d for d in project.check(base="HEAD") if d.rule == "profile/code-needs-spec"]
    assert [d.node for d in diags] == ["CAP-a"]  # the wrong spec changed
    assert "src/a.py implements CAP-a" in diags[0].message

    project.write("docs/capabilities/a.md", (project.root / "docs/capabilities/a.md").read_text() + "\nmore\n")
    assert project.rules(base="HEAD") == []

    # untraced code falls back to "any living spec changed"
    project.git("checkout", "-q", "--", ".")
    project.write("src/plain.py", "y = 2\n")
    assert project.rules(base="HEAD") == ["profile/code-needs-spec"]


def test_id_format_uses_set_values(project):
    from bondstone.graph import build_graph
    from bondstone.model import BondstoneError
    from bondstone.scaffold import next_id

    project.profile(packs=["adr@1"])
    graph = build_graph(load_config(project.root))
    assert next_id("x:Release", "v{version}", graph, "s", {"version": "0.2.0"}) == "v0.2.0"
    with pytest.raises(BondstoneError, match="pass --set version"):
        next_id("x:Release", "v{version}", graph, "s", {})


def test_frontmatter_edits_handle_flow_style():
    from bondstone.edit import replace_id, set_scalar

    text = "---\n{id: ADR-001, title: T, status: accepted,\n  owner: me}\n---\n## Context\n"
    edited = set_scalar(text, "status", "superseded")
    assert "status: superseded" in edited and "{" not in edited
    assert edited.endswith("---\n## Context\n")
    text = "---\n{id: CAP-a, constrained_by: [ADR-001, ADR-002]}\n---\n"
    edited, changed = replace_id(text, "constrained_by", "ADR-001", "ADR-009")
    assert changed and "ADR-009" in edited and "ADR-002" in edited
    block = "---\nid: X\nlinks: [A, B]   # keep\n---\n"
    assert replace_id(block, "links", "A", "C")[0] == "---\nid: X\nlinks: [C, B]   # keep\n---\n"
