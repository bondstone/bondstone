import json
import textwrap

import pytest
import yaml
from jsonschema import Draft202012Validator

from bondstone.manifest import KINDS, SCHEMA_DIR, load_manifest, normalize, schema, validate


def y(text: str):
    return normalize(yaml.safe_load(textwrap.dedent(text)))


DESIGN_PACK = """
    id: adr
    version: 1.0.0
    bondstone: ">=1.0"
    description: Architecture decision records with a lifecycle and supersession.
    types:
      Decision:
        description: One architecturally significant decision and its rationale.
        id: "ADR-{n:03d}"
        path: "docs/adr/{id}-{slug}.md"
        template: templates/decision.md
        fields:
          title: {type: string, minLength: 3}
          date: {type: string, format: date}
          deciders: {type: array, items: {type: string}}
        required: [title, date]
        sections: [Context, Decision, Alternatives considered, Consequences]
        traits:
          lifecycle:
            statuses: [proposed, accepted, rejected, deprecated, superseded]
            initial: proposed
            transitions:
              proposed: [accepted, rejected]
              accepted: [deprecated, superseded]
          owned: {}
          supersedable: {link: supersedes}
          immutable: {when: [accepted, rejected, deprecated, superseded], allow: [status]}
          indexed: {}
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
          lifecycle:
            statuses: [planned, active, removed]
            default: active
            transitions: {planned: [active, removed], active: [removed]}
          code-traceable: {coverage: error, when: [active], retired: [removed]}
    links:
      supersedes: {from: Decision, to: Decision, max: 1, description: The decision this one replaces.}
    rules: []
    views: []
    instructions: instructions.md
"""

DESIGN_BRIDGE = """
    id: adr-capability
    version: 1.0.0
    bondstone: ">=1.0"
    requires: {adr: "^1", capability: "^1"}
    links:
      constrained_by: {from: capability:Capability, to: adr:Decision}
    roles:
      decision: [adr:Decision]
      living-spec: [capability:Capability]
    rules:
      - id: constrained-by-live-decision
        description: Capabilities are constrained only by proposed or accepted decisions.
        when: {type: capability:Capability}
        require: [{link: constrained_by, all: true, to: {type: adr:Decision, status: [proposed, accepted]}}]
        hint: Point to the decision that superseded it.
    views: []
    instructions: instructions.md
"""

DESIGN_PROFILE = """
    bondstone: 1
    extends: [starter@1]
    packs: [release@1, runbooks@0.1]
    bridges: []
    sources: [.bondstone/packs]
    docs: ["docs/**/*.md"]
    code:
      include: ["app/lib/**/*.dart"]
      exclude: ["**/*.g.dart"]
    defaults: {owner: dawid}
    roles: {}
    rules:
      - id: code-change-updates-living-spec
        description: Changing app code updates the living specs that code implements.
        on_change:
          paths: ["app/lib/**"]
          kinds: [added, modified, deleted]
        require:
          - changed: {role: living-spec}
            traced: true
            min: 1
        exempt: {trailer: Spec-Impact}
        hint: Update the spec, or add the trailer.
    views: []
    overrides:
      adr/alternatives-considered: warn
    waivers:
      - rule: adr-capability/accepted-decision-is-applied
        node: ADR-001
        reason: Organisation-wide decision that constrains no single capability.
        expires: 2027-06-30
"""


@pytest.mark.parametrize("name", [*KINDS, "common"])
def test_shipped_schemas_are_valid_json_schema(name):
    Draft202012Validator.check_schema(schema(name))
    assert (SCHEMA_DIR / f"{name}.schema.json").is_file()


@pytest.mark.parametrize("kind,text", [("pack", DESIGN_PACK), ("bridge", DESIGN_BRIDGE),
                                       ("profile", DESIGN_PROFILE)])
def test_design_examples_are_valid(kind, text):
    assert validate(kind, y(text)) == []


def test_dates_are_normalized_before_validation():
    data = y(DESIGN_PROFILE)
    assert data["waivers"][0]["expires"] == "2027-06-30"


def test_boolean_severity_names_the_fix():
    # D3: `off` is a YAML boolean
    [message] = validate("profile", y("""
        bondstone: 1
        overrides: {adr/alternatives-considered: off}
    """))
    assert message.startswith("overrides.adr/alternatives-considered: severity is the YAML boolean false")
    assert "`ignore` switches a rule off" in message


def test_old_severity_mapping_is_rejected():
    [message] = validate("profile", y("""
        bondstone: 1
        overrides: {adr/x: {severity: warn}}
    """))
    assert "expected one of error, warn, info, ignore" in message


def test_format_version_must_be_the_integer_one():
    [message] = validate("profile", y("bondstone: 0.1"))
    assert message == "bondstone: expected the format version 1, got 0.1"
    assert validate("profile", y("packs: []")) == ["missing required key 'bondstone'"]


def test_poc_keys_are_unknown():
    messages = validate("pack", y("""
        id: adr
        version: 1.0.0
        types:
          Decision:
            id_format: "ADR-{n:03d}"
            paths: ["docs/adr/*.md"]
            required_fields: [title]
    """))
    assert len(messages) == 1
    assert messages[0].startswith("types.Decision: unknown keys 'id_format', 'paths', 'required_fields' (allowed: ")


def test_unknown_trait_and_trait_options():
    messages = validate("pack", y("""
        id: p
        version: 1.0.0
        types:
          Note:
            traits:
              versioned: {}
              lifecycle: {initial: draft}
              code-traceable: {coverage: off}
    """))
    assert any(m.startswith("types.Note.traits: unknown key 'versioned'") for m in messages)
    assert "types.Note.traits.lifecycle: missing required key 'statuses'" in messages
    assert any(m.startswith("types.Note.traits.code-traceable.coverage: severity is the YAML boolean") for m in messages)


def test_version_must_be_semantic():
    messages = validate("pack", y("{id: p, version: 1.0}"))
    assert messages == ["version: expected a semantic version such as 1.0.0, got 1.0"]


def test_bridge_defines_no_types_and_needs_requires():
    messages = validate("bridge", y("""
        id: a-b
        version: 1.0.0
        types: {X: {}}
    """))
    assert "missing required key 'requires'" in messages
    assert any(m.startswith("unknown key 'types'") for m in messages)


def test_rule_and_view_shapes():
    messages = validate("pack", y("""
        id: p
        version: 1.0.0
        rules:
          - description: no id
          - id: Bad_Id
          - id: ok
            when: {kind: Note}
            require: [{sections: Summary}]
        views:
          - {id: v, output: out.md, render: chart}
          - {id: w, output: out.md, levels: [{link: a, incoming: b}]}
    """))
    assert "rules[0]: missing required key 'id'" in messages
    assert any(m.startswith("rules[1].id: expected a lower-case rule id") for m in messages)
    assert any(m.startswith("rules[2].when: unknown key 'kind'") for m in messages)
    assert any(m.startswith("rules[2].require[0]: unknown key 'sections'") for m in messages)
    assert 'views[0].render: expected one of table, tree, matrix, got "chart"' in messages
    assert any(m.startswith("views[1].levels[0]: expected exactly one of `link` or `incoming`") for m in messages)


def test_type_and_link_names():
    messages = validate("pack", y("""
        id: p
        version: 1.0.0
        types: {note: {}}
        links: {Depends-On: {from: X, to: Y}}
    """))
    assert 'types: type names start with a capital letter and contain only letters and digits, got "note"' in messages
    assert 'links: link names are lower-case with underscores, such as constrained_by, got "Depends-On"' in messages


def test_load_manifest_reports_yaml_errors_and_schema_errors(tmp_path):
    bad = tmp_path / "pack.yaml"
    bad.write_text("id: [unclosed\n")
    data, problems = load_manifest("pack", bad, "packs/x/pack.yaml")
    assert data is None
    assert [(d.rule, d.severity, d.path) for d in problems] == [("bondstone/profile", "error", "packs/x/pack.yaml")]
    assert problems[0].message.startswith("invalid YAML:")

    bad.write_text("id: p\n")
    data, problems = load_manifest("pack", bad, "packs/x/pack.yaml")
    assert data is None and problems[0].message == "missing required key 'version'"

    bad.write_text("")
    data, problems = load_manifest("profile", bad, ".bondstone/profile.yaml")
    assert data is None and problems[0].message == "missing required key 'bondstone'"

    bad.write_text("- a\n- b\n")
    assert load_manifest("profile", bad, "p")[1][0].message == "expected a mapping at the top level"

    good = tmp_path / "profile.yaml"
    good.write_text(json.dumps({"bondstone": 1}))
    assert load_manifest("profile", good, "p") == ({"bondstone": 1}, [])
