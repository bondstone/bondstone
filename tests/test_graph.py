from bondstone.config import load_config
from bondstone.graph import build_graph, glob_files, scan_tags, tag_regions

PACK = """
    id: spec
    version: 1.0.0
    types:
      Decision:
        id: "ADR-{n:03d}"
        path: "docs/adr/{id}-{slug}.md"
      Capability:
        id: "CAP-{slug}"
        path: "docs/capabilities/{slug}.md"
        fields: {code: {type: string}}
        items:
          type: Requirement
          section: Requirements
          id: "REQ-{code}-{n:03d}"
      Requirement:
        embedded: true
        traits:
          lifecycle: {statuses: [planned, active, removed], default: active}
          code-traceable: {coverage: error, when: [active], retired: [removed]}
      Note:
        id: "NOTE-{n}"
        path: "docs/adr/{slug}.md"
    links:
      supersedes: {from: Decision, to: Decision, max: 1}
      constrained_by: {from: Capability, to: Decision}
      depends_on: {from: Capability, to: Capability}
    views:
      - {id: log, output: docs/generated/decisions.md, select: {type: Decision}}
"""

CAPABILITY = """
    ---
    id: CAP-reminders
    type: spec:Capability
    title: Reminders
    code: REM
    constrained_by: [ADR-002, ADR-003]
    depends_on: CAP-habits
    ---
    ## Requirements

    ### REQ-REM-001: Remind at the usual time

    The app SHALL remind.

    ### REQ-REM-002: Snooze

    Status: planned

    ### Not an item
"""


def setup(project, **profile):
    project.pack("spec", PACK)
    profile.setdefault("packs", ["spec@1"])
    profile.setdefault("docs", ["docs/**/*.md"])
    return project.profile(**profile)


def graph_of(project):
    cfg = load_config(project.root)
    assert cfg.errors == [], cfg.errors
    return build_graph(cfg)


def found(graph):
    return [(d.rule, d.path, d.line) for d in graph.diagnostics]


def adr(doc_id, extra="", doc_type="spec:Decision"):
    type_line = f"type: {doc_type}\n" if doc_type else ""
    return f"---\nid: {doc_id}\n{type_line}title: T\n{extra}---\n## Context\n"


# --------------------------------------------------------------------------- documents and typing


def test_documents_become_nodes_with_fields_and_links(project):
    setup(project).write("docs/capabilities/reminders.md", CAPABILITY)
    graph = graph_of(project)
    node = graph.by_id["CAP-reminders"]
    assert (node.type, node.path, node.line, node.is_item) == ("spec:Capability", "docs/capabilities/reminders.md", 1, False)
    assert node.fields == {"title": "Reminders", "code": "REM"}  # id, type and links are not fields
    assert {k: [(r.target, r.line) for r in v] for k, v in node.links.items()} == {
        "spec:constrained_by": [("ADR-002", 6), ("ADR-003", 6)],
        "spec:depends_on": [("CAP-habits", 7)],
    }
    assert node.body_line == 9


def test_items_become_nodes_with_parent_status_and_part_of(project):
    setup(project).write("docs/capabilities/reminders.md", CAPABILITY)
    graph = graph_of(project)
    first, second = graph.by_id["REQ-REM-001"], graph.by_id["REQ-REM-002"]
    assert (first.type, first.parent, first.line, first.is_item) == ("spec:Requirement", "CAP-reminders", 11, True)
    assert first.title == "Remind at the usual time"
    assert first.status == "active"  # the lifecycle default (D9)
    assert (second.status, second.field_lines) == ("planned", {"status": 17})
    assert first.links["bondstone:part_of"][0].target == "CAP-reminders"
    assert [n.id for n in graph.items_of(graph.by_id["CAP-reminders"])] == ["REQ-REM-001", "REQ-REM-002"]
    assert found(graph) == [("bondstone/item-heading", "docs/capabilities/reminders.md", 19)]
    assert "expected '### {id}: {title}'" in graph.diagnostics[0].message


def test_incoming_index(project):
    setup(project)
    project.write("docs/capabilities/reminders.md", CAPABILITY)
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "supersedes: ADR-001\n"))
    graph = graph_of(project)
    assert [(link, source.id) for link, source in graph.incoming["ADR-002"]] == [
        ("spec:constrained_by", "CAP-reminders")]
    assert [n.id for n in graph.sources("ADR-001", {"spec:supersedes"})] == ["ADR-002"]
    assert [n.id for n in graph.sources("CAP-reminders", {"bondstone:part_of"})] == ["REQ-REM-001", "REQ-REM-002"]
    assert graph.sources("ADR-999", {"spec:supersedes"}) == []


def test_type_is_mandatory_but_the_document_is_still_checked(project):
    setup(project).write("docs/capabilities/a.md", "---\nid: CAP-a\ntitle: A\n---\n")
    graph = graph_of(project)
    assert found(graph) == [("bondstone/type-missing", "docs/capabilities/a.md", 1)]
    assert graph.diagnostics[0].hint == "Add `type: spec:Capability` to the frontmatter."
    assert graph.by_id["CAP-a"].type == "spec:Capability"


def test_unknown_mismatched_and_ambiguous_types(project):
    setup(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", doc_type="Decision"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", doc_type="spec:Capability"))
    project.write("docs/adr/ADR-003-c.md", adr("ADR-003", doc_type=None))
    project.write("docs/adr/ADR-004-d.md", adr("ADR-004", doc_type="spec:Requirement"))
    project.write("docs/adr/note.md", adr("NOTE-1", doc_type="spec:Note"))
    project.write("docs/other/x.md", adr("ADR-005"))
    graph = graph_of(project)
    assert found(graph) == [
        ("bondstone/unknown-type", "docs/adr/ADR-001-a.md", 3),
        ("bondstone/type-mismatch", "docs/adr/ADR-002-b.md", 3),
        ("bondstone/type-ambiguous", "docs/adr/ADR-003-c.md", 1),
        ("bondstone/type-mismatch", "docs/adr/ADR-004-d.md", 3),
        ("bondstone/type-mismatch", "docs/other/x.md", 3),
    ]
    by_path = {d.path: d for d in graph.diagnostics}
    assert by_path["docs/adr/ADR-001-a.md"].hint == "Use the qualified name `spec:Decision`."
    assert by_path["docs/adr/ADR-002-b.md"].message == (
        "declared type spec:Capability, but spec:Capability documents live at docs/capabilities/*.md; "
        "this path matches spec:Decision, spec:Note")
    assert "embedded type" in by_path["docs/adr/ADR-004-d.md"].message
    assert by_path["docs/other/x.md"].message == "declared type spec:Decision, but spec:Decision documents live at docs/adr/*.md"
    assert [n.id for n in graph.nodes] == ["NOTE-1"]  # the declared type resolves the ambiguity


def test_managed_folders_report_untyped_and_unreadable_files(project):
    setup(project)
    project.write("docs/notes/plain.md", "# Just notes\n")
    project.write("docs/notes/typed-nowhere.md", "---\nid: X-1\ntitle: T\n---\n")
    project.write("docs/adr/ADR-001-a.md", "# No frontmatter\n")
    project.write("docs/adr/ADR-002-b.md", "---\nid: [broken\n---\n")
    (project.root / "docs/adr/ADR-003-c.md").write_bytes(b"---\nid: \xff\xfe\n---\n")
    project.write("elsewhere/readme.md", "# Not managed: ignored\n")
    graph = graph_of(project)
    assert found(graph) == [
        ("bondstone/frontmatter-missing", "docs/adr/ADR-001-a.md", 1),
        ("bondstone/parse-error", "docs/adr/ADR-002-b.md", 2),
        ("bondstone/parse-error", "docs/adr/ADR-003-c.md", 1),
        ("bondstone/untyped-document", "docs/notes/plain.md", 1),
        ("bondstone/untyped-document", "docs/notes/typed-nowhere.md", 1),
    ]
    assert graph.nodes == []


def test_documents_at_a_type_path_are_read_even_outside_docs(project):
    setup(project, docs=[])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    project.write("docs/notes/plain.md", "# Not managed\n")
    graph = graph_of(project)
    assert [n.id for n in graph.nodes] == ["ADR-001"] and graph.diagnostics == []


def test_generated_views_are_not_documents(project):
    setup(project)
    project.write("docs/generated/decisions.md", "hand-written, but it is a view output\n")
    project.write("docs/generated/old.md", "<!-- bondstone:generated view=spec/old; do not edit -->\n# Old\n")
    assert found(graph_of(project)) == []


def test_ambiguous_link_keys(project):
    setup(project, packs=["spec@1", "other@1"], bridges=["b@1"])
    project.pack("other", "id: other\nversion: 1.0.0\n")
    project.bridge("b", """
        id: b
        version: 1.0.0
        requires: {spec: "^1", other: "^1"}
        links:
          supersedes: {from: spec:Decision, to: spec:Decision}
    """)
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "supersedes: ADR-001\n"))
    project.write("docs/adr/ADR-003-c.md", adr("ADR-003", "b:supersedes: ADR-001\n"))
    graph = graph_of(project)
    assert found(graph) == [("bondstone/link-ambiguous", "docs/adr/ADR-002-b.md", 5)]
    assert list(graph.by_id["ADR-003"].links) == ["b:supersedes"]
    assert graph.by_id["ADR-002"].links == {}


def test_glob_files_is_sorted_relative_and_files_only(project):
    project.write("docs/b.md", "b").write("docs/a/c.md", "c").write("docs/a.md", "a")
    assert glob_files(project.root, "docs/**/*.md") == ["docs/a.md", "docs/a/c.md", "docs/b.md"]
    assert glob_files(project.root, "docs/*") == ["docs/a.md", "docs/b.md"]
    assert glob_files(project.root, "nope/*.md") == []


# --------------------------------------------------------------------------- code tags


def test_scan_tags():
    assert scan_tags("// bondstone: REQ-REM-001, REQ-REM-002\ncode\n  # bondstone: CAP-a") == [
        (1, "REQ-REM-001"), (1, "REQ-REM-002"), (3, "CAP-a")]
    assert scan_tags("# bondstone: REQ-AA-001, CLI-pack-test.") == [(1, "REQ-AA-001"), (1, "CLI-pack-test")]
    assert scan_tags("# bondstone: A") == [(1, "A")]


def test_mentions_that_are_not_tags():
    for text in ['MARK = "<!-- bondstone:generated"', 'LINK = "bondstone:part_of"',
                 'HINT = "add a `bondstone: <id>` comment"', "hint: tag it with `bondstone: REQ-...`",
                 "bondstone: 1", 'bondstone: ">=1.0"', "mybondstone: REQ-1"]:
        assert scan_tags(text) == [], text


def test_code_tags_cover_nodes_and_respect_include_and_exclude(project):
    setup(project, code={"include": ["app/**/*.dart", "app/lib/reminders.dart"], "exclude": ["**/*.g.dart"]})
    project.write("docs/capabilities/reminders.md", CAPABILITY)
    project.write("app/lib/reminders.dart", "// bondstone: REQ-REM-001, REQ-XXX-009\nvoid f() {}\n")
    project.write("app/lib/reminders.g.dart", "// bondstone: REQ-REM-002\n")
    project.write("lib/other.dart", "// bondstone: REQ-REM-002\n")
    (project.root / "app/lib/blob.dart").write_bytes(b"\xff\xfe\x00")
    graph = graph_of(project)
    assert [(t.path, t.line, t.id) for t in graph.code_tags] == [
        ("app/lib/reminders.dart", 1, "REQ-REM-001"), ("app/lib/reminders.dart", 1, "REQ-XXX-009")]
    assert graph.by_id["REQ-REM-001"].covered and not graph.by_id["REQ-REM-002"].covered
    assert [(r.path, r.id, r.start, r.end) for r in graph.code_regions] == [
        ("app/lib/reminders.dart", "REQ-REM-001", 1, 2), ("app/lib/reminders.dart", "REQ-XXX-009", 1, 2)]


def test_tag_regions_end_with_the_tagged_block():
    py = ("# bondstone: A-1\ndef f(x,\n      y):\n    a = 1\n\n    return a\n\n\n"
          "def untagged():\n    pass\n\n\nclass C:\n    # bondstone: B-1\n    def m(self):\n        pass\n\n"
          "    def n(self):\n        pass\n")
    assert tag_regions(py) == [("A-1", 1, 6), ("B-1", 14, 16)]
    js = "// bondstone: J-1\nfunction f() {\n  return 1;\n}\n\nfunction g() {}\n"
    assert tag_regions(js) == [("J-1", 1, 4)]


def test_stacked_tags_share_a_region_and_the_next_tag_ends_it():
    text = "# bondstone: A-1\n# bondstone: B-1\ndef f():\n    pass\n# bondstone: C-1\ndef g():\n    pass\n"
    assert tag_regions(text) == [("A-1", 1, 4), ("B-1", 1, 4), ("C-1", 5, 7)]


def test_nested_tags_keep_the_outer_region():
    py = ("# bondstone: A-1\ndef f():\n    x = 1\n    # bondstone: E-1\n    raise E()\n\n    return x\n\n\n"
          "# bondstone: B-1\ndef g():\n    pass\n")
    assert sorted(tag_regions(py)) == [("A-1", 1, 7), ("B-1", 10, 12), ("E-1", 4, 5)]


def test_tag_at_the_end_of_a_file_and_tag_followed_by_nothing():
    assert tag_regions("x = 1\n# bondstone: A-1\n") == [("A-1", 2, 2)]
    assert tag_regions("# bondstone: A-1\n\n\n") == [("A-1", 1, 1)]
    assert tag_regions("# bondstone: A-1\nx = 1\ny = 2\n\nz = 3\n") == [("A-1", 1, 3)]
