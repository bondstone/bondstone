import re

import pytest

from bondstone.config import heading_pattern, id_regex, load_config, path_glob, qualify, template_problem

ADR = """
    id: adr
    version: 1.0.0
    types:
      Decision:
        id: "ADR-{n:03d}"
        path: "docs/adr/{id}-{slug}.md"
        fields:
          title: {type: string, minLength: 3}
          date: {type: string, format: date}
        required: [title, date]
        sections: [Context, Decision]
        traits:
          lifecycle:
            statuses: [proposed, accepted, superseded]
            initial: proposed
            transitions: {proposed: [accepted], accepted: [superseded]}
          owned: {}
          supersedable: {link: supersedes}
          immutable: {when: [accepted, superseded], allow: [status]}
    links:
      supersedes: {from: Decision, to: Decision, max: 1}
    rules:
      - id: alternatives-considered
        severity: warn
        when: {type: Decision, status: accepted}
        require: [{contains: "(?im)^#{2,3}\\\\s+Alternatives"}]
      - id: has-date
        locked: true
        when: {type: Decision}
        require: [{field: date}]
    views:
      - {id: decision-log, title: Decision log, output: docs/generated/decisions.md, select: {type: Decision}}
"""

CAPABILITY = """
    id: capability
    version: 1.0.0
    types:
      Capability:
        id: "CAP-{slug}"
        path: "docs/capabilities/{slug}.md"
        fields: {title: {type: string}, code: {type: string, pattern: "^[A-Z]{2,6}$"}}
        required: [title, code]
        items:
          type: Requirement
          section: Requirements
          heading: "### {id}: {title}"
          id: "REQ-{code}-{n:03d}"
      Requirement:
        embedded: true
        traits:
          lifecycle: {statuses: [planned, active, removed], default: active}
          code-traceable: {coverage: error, when: [active], retired: [removed]}
"""

BRIDGE = """
    id: adr-capability
    version: 1.0.0
    requires: {adr: "^1", capability: "^1"}
    links:
      constrained_by: {from: capability:Capability, to: adr:Decision}
    roles:
      decision: [adr:Decision]
      living-spec: capability:Capability
    rules:
      - id: constrained-by-live-decision
        when: {type: capability:Capability}
        require: [{link: constrained_by, all: true, to: {type: adr:Decision, status: [proposed, accepted]}}]
"""


def setup(project, **profile):
    project.pack("adr", ADR).pack("capability", CAPABILITY).bridge("adr-capability", BRIDGE)
    profile.setdefault("packs", ["adr@1", "capability@1"])
    profile.setdefault("bridges", ["adr-capability@1"])
    project.profile(**profile)
    return project


def problems(project):
    return [(d.path, d.message) for d in load_config(project.root).problems]


# --------------------------------------------------------------------------- templates


@pytest.mark.parametrize("template,pattern", [
    ("ADR-{n:03d}", r"^ADR\-\d{3,}$"),
    ("OUT-{n}", r"^OUT\-\d+$"),
    ("CAP-{slug}", r"^CAP\-[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ("v{version}", r"^v[^\s/]+$"),
])
def test_id_pattern_is_derived_from_the_template(template, pattern):
    assert id_regex(template) == pattern


@pytest.mark.parametrize("template,good,bad", [
    ("ADR-{n:03d}", ["ADR-001", "ADR-1234"], ["ADR-01", "ADR-001a", "adr-001", "XADR-001"]),
    ("OUT-{n}", ["OUT-1", "OUT-12"], ["OUT-", "OUT-x"]),
    ("CAP-{slug}", ["CAP-habits", "CAP-a-b2"], ["CAP-Habits", "CAP-a--b", "CAP-"]),
])
def test_derived_id_patterns_match_whole_ids(template, good, bad):
    pattern = re.compile(id_regex(template))
    assert all(pattern.match(i) for i in good)
    assert not any(pattern.match(i) for i in bad)


def test_field_placeholders_take_the_value_when_known():
    assert re.match(id_regex("REQ-{code}-{n:03d}", {"code": "REM"}), "REQ-REM-001")
    assert not re.match(id_regex("REQ-{code}-{n:03d}", {"code": "REM"}), "REQ-HAB-001")
    assert re.match(id_regex("REQ-{code}-{n:03d}", {}), "REQ-HAB-001")
    assert re.match(id_regex("v{version}", {"version": "0.1.0"}), "v0.1.0")
    assert not re.match(id_regex("v{version}", {"version": "0.1.0"}), "v0x1y0")


@pytest.mark.parametrize("template,glob", [
    ("docs/adr/{id}-{slug}.md", "docs/adr/*.md"),
    ("docs/capabilities/{slug}.md", "docs/capabilities/*.md"),
    ("docs/releases/v{version}.md", "docs/releases/v*.md"),
    ("specs/{n:03d}-{slug}/spec.md", "specs/*/spec.md"),
    ("docs/overview.md", "docs/overview.md"),
])
def test_match_glob_is_derived_from_the_path_template(template, glob):
    assert path_glob(template) == glob


def test_template_problems():
    assert template_problem("ADR-{n:03d}") is None
    assert "unbalanced" in template_problem("ADR-{n")
    assert "unbalanced" in template_problem("ADR-{}")
    assert "only {n} takes a format" in template_problem("ADR-{slug:03d}")
    assert "only {n} takes a format" in template_problem("ADR-{n:x}")


def test_item_heading_pattern():
    level, pattern = heading_pattern("### {id}: {title}")
    assert level == 3
    assert pattern.match("REQ-REM-001: Remind at the usual time").groupdict() == {
        "id": "REQ-REM-001", "title": "Remind at the usual time"}
    assert pattern.match("REQ-REM-001:No space").group("title") == "No space"
    assert pattern.match("Not a requirement heading") is None
    level, pattern = heading_pattern("#### {id}")
    assert (level, pattern.match("ENG-012").group("id")) == (4, "ENG-012")
    assert heading_pattern("{id}: {title}") is None  # no level
    assert heading_pattern("### {title}") is None  # no id
    assert heading_pattern("### {id}: {name}") is None  # unknown placeholder


def test_qualify():
    assert qualify("Decision", "adr") == "adr:Decision"
    assert qualify("adr:Decision", "ost") == "adr:Decision"
    assert qualify("Decision", None) == "Decision"


# --------------------------------------------------------------------------- effective configuration


def test_builds_types_links_roles_rules_and_views(project):
    cfg = load_config(setup(project).root)
    assert cfg.problems == []
    decision = cfg.types["adr:Decision"]
    assert (decision.id_template, decision.path_glob) == ("ADR-{n:03d}", "docs/adr/*.md")
    capability = cfg.types["capability:Capability"]
    assert capability.items.type == "capability:Requirement"
    assert (capability.items.level, capability.items.section) == (3, "Requirements")
    assert cfg.types["capability:Requirement"].embedded
    assert cfg.links["adr:supersedes"].max == 1
    assert cfg.links["adr-capability:constrained_by"].from_types == ["capability:Capability"]
    assert cfg.roles == {"decision": ["adr:Decision"], "living-spec": ["capability:Capability"]}
    assert [(r.qid, r.severity, r.locked, r.kind) for r in cfg.rules] == [
        ("adr/alternatives-considered", "warn", False, "node"),
        ("adr/has-date", "error", True, "node"),
        ("adr-capability/constrained-by-live-decision", "error", False, "node"),
    ]
    assert [(v.qid, v.output) for v in cfg.views] == [("adr/decision-log", "docs/generated/decisions.md")]


def test_document_schema_adds_trait_fields(project):
    schema = load_config(setup(project).root).schema_for("adr:Decision")
    assert schema["required"] == ["date", "owner", "status", "title"]
    assert schema["properties"]["status"] == {"enum": ["proposed", "accepted", "superseded"]}
    assert schema["additionalProperties"] is False


def test_link_keys_resolve_by_name_and_qualified_name(project):
    cfg = load_config(setup(project).root)
    assert cfg.resolve_link_key("capability:Capability", "constrained_by")[0].qname == "adr-capability:constrained_by"
    assert cfg.resolve_link_key("capability:Capability", "adr-capability:constrained_by")[0] is not None
    assert cfg.resolve_link_key("adr:Decision", "constrained_by") == (None, None)


def test_ambiguous_link_names(project):
    setup(project, bridges=["adr-capability@1", "other@1"])
    project.bridge("other", """
        id: other
        version: 1.0.0
        requires: {adr: "^1", capability: "^1"}
        links:
          constrained_by: {from: capability:Capability, to: adr:Decision}
    """)
    cfg = load_config(project.root)
    link, error = cfg.resolve_link_key("capability:Capability", "constrained_by")
    assert link is None and "ambiguous (adr-capability:constrained_by, other:constrained_by)" in error


def test_overrides_set_the_effective_severity(project):
    setup(project, overrides={"adr/alternatives-considered": "error", "bondstone/view-stale": "ignore",
                              "adr/has-date": "error"})
    cfg = load_config(project.root)
    assert cfg.problems == []
    assert cfg.severity("adr/alternatives-considered", "warn") == "error"
    assert cfg.severity("bondstone/view-stale", "error") == "ignore"
    assert cfg.severity("adr/has-date", "error") == "error"
    assert cfg.severity("bondstone/link-broken", "error") == "error"


def test_override_problems(project):
    setup(project, overrides={"adr/has-date": "warn", "adr/nope": "warn", "bondstone/nope": "warn",
                              "bondstone/profile": "ignore"})
    cfg = load_config(project.root)
    assert [d.message for d in cfg.errors] == [
        "overrides.adr/has-date: the rule is locked; its severity (error) can be raised but not lowered",
        "overrides.adr/nope: unknown rule",
        "overrides.bondstone/nope: unknown engine rule",
        "overrides.bondstone/profile: configuration errors cannot be overridden",
    ]
    assert cfg.overrides == {}


def test_unbridged_packs_is_a_warning_not_a_configuration_error(project):
    setup(project, bridges=[])
    cfg = load_config(project.root)
    assert [(d.rule, d.severity) for d in cfg.problems] == [("bondstone/unbridged-packs", "warn")]
    assert "adr; capability" in cfg.problems[0].message
    assert cfg.errors == []


def test_profile_rules_roles_and_views(project):
    setup(project, roles={"spec": ["capability:Capability"], "broken": ["capability:Nope"]},
          rules=[{"id": "specs-have-owner", "when": {"role": "spec"}, "require": [{"field": "owner"}]},
                 {"id": "code-needs-spec", "on_change": {"paths": ["src/**"]},
                  "require": [{"changed": {"role": "living-spec"}, "traced": True, "min": 1}],
                  "exempt": {"trailer": "Spec-Impact"}}],
          views=[{"id": "all", "output": "docs/generated/all.md", "select": {"role": "spec"}}])
    cfg = load_config(project.root)
    assert [(d.path, d.message) for d in cfg.problems] == [
        (".bondstone/profile.yaml", "roles.broken: unknown type 'capability:Nope'")]
    assert [(r.qid, r.kind, r.context_pack) for r in cfg.rules[-2:]] == [
        ("profile/specs-have-owner", "node", None), ("profile/code-needs-spec", "diff", None)]
    assert cfg.views[-1].qid == "profile/all"


# --------------------------------------------------------------------------- semantic checks


def pack_problems(project, text):
    project.pack("p", text)
    project.profile(packs=["p"])
    return [d.message for d in load_config(project.root).errors]


def test_type_needs_templates_or_embedded(project):
    assert pack_problems(project, """
        id: p
        version: 1.0.0
        types:
          Note: {id: "N-{n}"}
          Loose: {embedded: true}
          Odd: {embedded: true, path: "x/{slug}.md", traits: {owned: {}}}
          Host: {id: "H-{n}", path: "h/{id}.md", items: {type: Odd}}
    """) == [
        "types.Note: needs an `id` template and a `path` template (or `embedded: true`)",
        "types.Odd: an embedded type takes no `path`; its documents' type declares the items",
        "types.Odd: trait 'owned' needs frontmatter and is not available on an embedded type",
        "types.Loose: embedded type is not used by any type's `items`",
    ]


def test_template_and_field_checks(project):
    project.write(".bondstone/packs/p/templates/ok.md", "x\n")
    assert pack_problems(project, """
        id: p
        version: 1.0.0
        types:
          A:
            id: "A-{n:x}"
            path: "/abs/{id}.md"
            template: templates/missing.md
            fields: {id: {type: string}, size: {type: nonsense}}
            required: [colour]
          B:
            id: "B-{code}-{n}"
            path: "docs/b/{id}.md"
            template: templates/ok.md
            id_pattern: "B-("
    """) == [
        "types.A: field 'id' is reserved; every document has it already",
        "types.A: fields are not valid JSON Schema (size.type: 'nonsense' is not valid under any of the given schemas)",
        "types.A: required field 'colour' is not declared in `fields`",
        "types.A: id: 'A-{n:x}': only {n} takes a format, such as {n:03d}",
        "types.A: path: must be relative to the repository root",
        "types.A: template 'templates/missing.md' not found",
        "types.B: id: placeholder {code} is neither n, slug nor a declared field",
        "types.B: id_pattern is not a valid regular expression (missing ), unterminated subpattern at position 2)",
    ]


def test_trait_checks(project):
    assert pack_problems(project, """
        id: p
        version: 1.0.0
        types:
          A:
            id: "A-{n}"
            path: "a/{id}.md"
            traits:
              lifecycle:
                statuses: [draft, final]
                initial: new
                transitions: {draft: [final, gone], old: [final]}
              immutable: {when: [frozen]}
              supersedable: {}
            items: {type: Item}
          B:
            id: "B-{n}"
            path: "b/{id}.md"
            traits: {code-traceable: {when: [active]}}
          Item:
            embedded: true
            traits:
              lifecycle: {statuses: [planned, active]}
              code-traceable: {when: [active, planned], retired: [planned]}
    """) == [
        "types.A: lifecycle.initial: 'new' is not one of the lifecycle statuses",
        "types.A: lifecycle.transitions.draft: 'gone' is not one of the lifecycle statuses",
        "types.A: lifecycle.transitions: 'old' is not one of the lifecycle statuses",
        "types.A: immutable.when: 'frozen' is not one of the lifecycle statuses",
        "types.B: code-traceable.when lists statuses, so the type needs the lifecycle trait",
        "types.Item: lifecycle.default is required on an embedded type: an item without a `Status:` line takes it",
        "types.Item: code-traceable: planned cannot be in both `when` and `retired`",
        "types.A: supersedable link 'p:supersedes' is not a link from this type",
    ]


def test_items_checks(project):
    assert pack_problems(project, """
        id: p
        version: 1.0.0
        types:
          A: {id: "A-{n}", path: "a/{id}.md", items: {type: Missing}}
          B: {id: "B-{n}", path: "b/{id}.md", items: {type: A}}
          C: {id: "C-{n}", path: "c/{id}.md", items: {type: "other:Item"}}
          D: {id: "D-{n}", path: "d/{id}.md", items: {type: Item, heading: "{id}"}}
          E: {id: "E-{n}", path: "e/{id}.md", items: {type: Item, id: "I-{code}-{n}"}}
          Item: {embedded: true}
    """) == [
        "types.A: items.type 'Missing' is not defined",
        "types.B: items.type 'A' must be declared with `embedded: true`",
        "types.C: items.type 'other:Item' must be a type of the same pack",
        "types.D: items.heading '{id}' must look like '### {id}: {title}': a heading level, {id} and optionally {title}",
        "types.E: items.id: placeholder {code} is neither n, slug nor a field of E",
    ]


def test_link_checks(project):
    assert pack_problems(project, """
        id: p
        version: 1.0.0
        types:
          A: {id: "A-{n}", path: "a/{id}.md", fields: {size: {type: string}}, items: {type: Item}}
          Item: {embedded: true}
        links:
          size: {from: A, to: A}
          title: {from: A, to: A}
          parts: {from: Item, to: A}
          refs: {from: A, to: [Item, Nope], min: 2, max: 1}
    """) == [
        "links.size: 'size' is already a frontmatter key of p:A",
        "links.title: 'title' is already a frontmatter key of p:A",
        "links.parts: links are written in frontmatter, so they cannot start at the embedded type p:Item",
        "links.refs: unknown type 'p:Nope'",
        "links.refs: max is lower than min",
    ]


def test_bridge_types_must_be_qualified(project):
    setup(project)
    project.bridge("adr-capability", BRIDGE.replace("to: adr:Decision}", "to: Decision}"))
    assert problems(project) == [(".bondstone/packs/adr-capability/bridge.yaml",
                                  "links.constrained_by: unknown type 'Decision' (use a qualified name such as pack:Type)")]


def test_rule_checks(project):
    assert pack_problems(project, """
        id: p
        version: 1.0.0
        types:
          A: {id: "A-{n}", path: "a/{id}.md"}
        links:
          refs: {from: A, to: A}
        rules:
          - id: no-kind
            require: [{field: x}]
          - id: two-kinds
            when: {type: A}
            for_each: {glob: "x/*", document: "{dir}/README.md"}
          - id: no-require
            when: {type: A}
          - id: selectors
            when: {type: [A, Nope], role: nobody, trait: sticky}
            require: [{field: x}]
          - id: clauses
            when: {type: A}
            require:
              - {field: x, section: y}
              - {}
              - {link: nope}
              - {link: refs, from: {type: A}}
              - {incoming: refs, from: {type: Gone}}
              - {contains: "("}
              - {items: {type: Missing}}
              - {changed: {type: A}}
              - any: [{exists: {type: A}}, {section: ok}]
          - id: diff
            on_change: {paths: ["src/**"]}
            require:
              - {section: x}
              - any: [{changed: {type: A}, traced: true}]
          - id: existence
            for_each: {glob: "lib/*/x.yaml", document: "{dir}/README.md", type: Nope}
            require: [{field: x}]
          - id: exempt
            when: {type: A}
            require: [{field: x}]
            exempt: {trailer: T}
          - id: exempt
            when: {type: A}
            require: [{field: x}]
    """) == [
        "p/no-kind: a rule needs exactly one of `when`, `on_change` and `for_each`",
        "p/two-kinds: a rule needs exactly one of `when`, `on_change` and `for_each`",
        "p/no-require: rule has no `require` clauses",
        "p/selectors: unknown type 'p:Nope'",
        "p/selectors: role 'nobody' is not assigned by any bridge or the profile",
        "p/selectors: unknown trait 'sticky'",
        "p/clauses: a clause needs exactly one of link, incoming, field, section, contains, items, covered, "
        "file_field, any; got field, section",
        "p/clauses: a clause needs exactly one of link, incoming, field, section, contains, items, covered, "
        "file_field, any; got nothing",
        "p/clauses: unknown link 'nope'",
        "p/clauses: clause `link` does not take `from`",
        "p/clauses: unknown type 'p:Gone'",
        "p/clauses: `contains` is not a valid regular expression (missing ), unterminated subpattern at position 0)",
        "p/clauses: unknown type 'p:Missing'",
        "p/clauses: clause `changed` is not available in a node rule (`when`)",
        "p/clauses: clause `exists` is not available in a node rule (`when`)",
        "p/diff: clause `section` is not available in a diff rule (`on_change`)",
        "p/diff: `traced` is not supported inside `any`",
        "p/existence: an existence rule (`for_each`) takes no `require`",
        "p/existence: unknown type 'p:Nope'",
        "p/exempt: `exempt` only applies to diff rules (`on_change`)",
        "rules: rule id 'exempt' is used more than once",
    ]


def test_view_checks(project):
    assert pack_problems(project, """
        id: p
        version: 1.0.0
        types:
          A: {id: "A-{n}", path: "a/{id}.md"}
        views:
          - {id: one, output: docs/generated/a.md, select: {type: Nope}}
          - {id: two, output: docs/generated/a.md, render: tree, levels: [{incoming: nope}]}
          - {id: three, output: ../outside.md}
          - {id: one, output: docs/generated/b.md}
    """) == [
        "p/one: unknown type 'p:Nope'",
        "p/two: output 'docs/generated/a.md' is already written by view p/one",
        "p/two: unknown link 'nope'",
        "p/three: output '../outside.md' must be a path inside the repository",
        "views: view id 'one' is used more than once",
    ]


def test_reserved_component_ids_and_missing_instructions(project):
    project.pack("profile", "id: profile\nversion: 1.0.0\ninstructions: instructions.md\n")
    project.profile(packs=["profile"])
    assert [d.message for d in load_config(project.root).errors] == [
        "id: 'profile' is reserved", "instructions: file 'instructions.md' not found"]
    project.write(".bondstone/packs/profile/instructions.md", "- Guidance.\n")
    assert [d.message for d in load_config(project.root).errors] == ["id: 'profile' is reserved"]


def test_invalid_profile_gives_an_empty_configuration(project):
    project.write(".bondstone/profile.yaml", "bondstone: 1\npacks: adr\n")
    cfg = load_config(project.root)
    assert len(cfg.errors) == 1 and cfg.types == {} and cfg.rules == []
