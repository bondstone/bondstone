"""Presets: partial profiles that a profile extends (D4)."""

import datetime as dt

import pytest
from conftest import ADR_CAPABILITY_BRIDGE, ADR_PACK, CAPABILITY_PACK, Project, adr, capability, check

from bondstone import agent
from bondstone import resolve as resolver
from bondstone.config import Lock, load_config

TODAY = dt.date(2026, 11, 10)
QUIET = {"bondstone/view-stale": "ignore"}


def preset(project: Project, preset_id: str, text: str = "", version: str = "1.0.0") -> Project:
    body = f"id: {preset_id}\nversion: {version}\n" + "\n".join(line.strip() for line in text.strip().splitlines())
    return project.write(f".bondstone/packs/{preset_id}/preset.yaml", body + "\n")


@pytest.fixture(autouse=True)
def no_installed_packages(monkeypatch):
    """Only the presets a test writes exist; the library's `starter` is out of the way."""
    monkeypatch.setattr(resolver, "entry_points", lambda group: [])


@pytest.fixture
def base(project) -> Project:
    """The three components a starter preset names, and that preset."""
    project.pack("adr", ADR_PACK).pack("capability", CAPABILITY_PACK).bridge("adr-capability", ADR_CAPABILITY_BRIDGE)
    project.write(".bondstone/packs/starter/preset.yaml", """
        id: starter
        version: 1.2.0
        packs: [adr@1, capability@1]
        bridges: [adr-capability@1]
        rules:
          - id: code-change-updates-living-spec
            description: A change to code updates the living specs that code implements.
            on_change: {code: true}
            require: [{changed: {role: living-spec}, traced: true}]
        overrides:
          bondstone/view-stale: ignore
    """)
    return project


def errors(project: Project) -> list[tuple[str, str]]:
    return [(d.path, d.message) for d in load_config(project.root).errors]


# ----------------------------------------------------------------------- resolution


def test_a_profile_that_only_extends_gets_the_presets_components_and_rules(base):
    base.profile(extends=["starter@1"])
    cfg = load_config(base.root)
    assert cfg.problems == []
    assert [(c.kind, c.id, c.version) for c in cfg.components] == [
        ("pack", "adr", "1.0.0"), ("pack", "capability", "1.0.0"), ("bridge", "adr-capability", "1.0.0"),
        ("preset", "starter", "1.2.0")]
    rule = cfg.rule("starter/code-change-updates-living-spec")
    assert (rule.owner, rule.kind, rule.source) == ("starter", "diff", ".bondstone/packs/starter/preset.yaml")
    assert cfg.severity("bondstone/view-stale", "warn") == "ignore"


def test_the_profiles_own_packs_come_after_the_presets(base):
    base.pack("note", "id: note\nversion: 1.0.0\n")
    base.profile(extends=["starter@1"], packs=["note@1", "adr@1"], overrides={"bondstone/unbridged-packs": "ignore"})
    cfg = load_config(base.root)
    assert cfg.errors == []
    assert [c.id for c in cfg.components] == ["adr", "capability", "note", "adr-capability", "starter"]


def test_presets_extend_presets_and_each_is_applied_once(base):
    preset(base, "team", "extends: [starter@1]\noverrides: {adr/alternatives-considered: error}")
    preset(base, "org", "extends: [starter, team@1]")
    base.profile(extends=["org@1", "team"])
    cfg = load_config(base.root)
    assert cfg.errors == []
    assert [c.id for c in cfg.components if c.kind == "preset"] == ["starter", "team", "org"]
    assert cfg.overrides["adr/alternatives-considered"] == "error"


def test_a_preset_that_is_missing_misplaced_or_circular_is_a_configuration_error(base):
    base.profile(extends=["nope@1"])
    assert errors(base) == [(".bondstone/profile.yaml",
                             "preset 'nope' not found in the profile's sources or in an installed package")]
    base.profile(extends=["adr@1"])
    assert errors(base)[0][1] == "preset 'adr' not found: 'adr' is a pack; list it under `packs`"
    base.profile(packs=["starter@1"])
    assert errors(base)[0][1] == "pack 'starter' not found: 'starter' is a preset; list it under `extends`"

    preset(base, "a", "extends: [b@1]")
    preset(base, "b", "extends: [a@1]")
    base.profile(extends=["a@1"])
    assert errors(base) == [(".bondstone/packs/b/preset.yaml", "extends: preset 'a' extends itself (a -> b -> a)")]


def test_preset_versions_must_fit_every_range(base):
    base.profile(extends=["starter@2"])
    assert errors(base) == [(".bondstone/profile.yaml", "preset 'starter': no version matches '2' (available: 1.2.0)")]
    preset(base, "team", "extends: [starter@1.3]")
    base.profile(extends=["starter@1", "team@1"])
    assert errors(base) == [(".bondstone/packs/team/preset.yaml",
                             "extends: preset 'starter' is needed as '1.3', but 1.2.0 is already in use")]


def test_a_component_named_twice_must_satisfy_every_range(base):
    base.profile(extends=["starter@1"], packs=["adr@1.0"])
    assert errors(base) == []
    base.profile(extends=["starter@1"], packs=["adr@1.4"])
    assert errors(base) == [(".bondstone/packs/starter/preset.yaml",
                             "pack 'adr': no version matches all of '1' (.bondstone/packs/starter/preset.yaml), "
                             "'1.4' (.bondstone/profile.yaml) (available: 1.0.0)")]


def test_a_bridge_of_the_profile_may_require_a_pack_of_a_preset(base):
    preset(base, "packs-only", "packs: [adr@1, capability@1]")
    base.profile(extends=["packs-only@1"], bridges=["adr-capability@1"])
    assert errors(base) == []
    preset(base, "packs-only", "packs: [adr@1]")
    assert errors(base) == [(".bondstone/profile.yaml",
                             "bridge 'adr-capability' requires pack 'capability', which is not in the profile")]


def test_a_preset_is_validated_against_its_schema_and_its_rules_are_checked(base):
    preset(base, "org", "docs: ['docs/**']\nrules:\n- {id: r, when: {type: nope:Type}, require: [{field: x}]}")
    base.profile(extends=["starter@1", "org@1"])
    found = errors(base)
    assert found[0][0] == ".bondstone/packs/org/preset.yaml" and found[0][1].startswith("unknown key 'docs'")

    preset(base, "org", "rules:\n- {id: r, when: {type: nope:Type}, require: [{field: x}]}\n"
                        "- {id: r, when: {type: adr:Decision}, require: [{field: x}]}")
    assert errors(base) == [(".bondstone/packs/org/preset.yaml", "org/r: unknown type 'nope:Type'"),
                            (".bondstone/packs/org/preset.yaml", "rules: rule id 'r' is used more than once")]

    preset(base, "profile")
    base.profile(extends=["profile@1"])
    assert errors(base) == [(".bondstone/packs/profile/preset.yaml", "id: 'profile' is reserved")]


def test_duplicates_inside_one_preset_are_reported_there(base):
    preset(base, "org", "packs: [adr@1, 'adr@1.0']")
    base.profile(extends=["org@1"])
    assert errors(base) == [(".bondstone/packs/org/preset.yaml", "packs: pack 'adr' is listed more than once")]


# ----------------------------------------------------------------------- severities


def test_severities_apply_in_layers(base):
    preset(base, "org", "extends: [starter@1]\noverrides: {adr/alternatives-considered: info, bondstone/todo-left: error}")
    preset(base, "team", "overrides: {adr/alternatives-considered: error}")
    base.profile(extends=["org@1", "team@1"], overrides={"bondstone/todo-left": "ignore"})
    cfg = load_config(base.root)
    assert cfg.errors == []
    assert cfg.overrides == {"bondstone/view-stale": "ignore", "adr/alternatives-considered": "error",
                             "bondstone/todo-left": "ignore"}
    assert cfg.override_sources == {"bondstone/view-stale": "preset starter",
                                    "adr/alternatives-considered": "preset team", "bondstone/todo-left": "profile"}
    listed = {rule.id: rule for rule in agent.list_rules(cfg)}
    assert listed["adr/alternatives-considered"].set_by == "preset team"
    text = agent.rules_text(list(listed.values()))
    assert ("error  adr/alternatives-considered: Accepted decisions record the alternatives that were considered. "
            "[default: warn, set by preset team]") in text
    assert "(set by the preset team; default: warn)" in agent.explain_text(cfg, "adr/alternatives-considered")
    assert "(set by the profile; default: error)" in agent.explain_text(cfg, "bondstone/todo-left")


def test_an_override_of_a_preset_must_name_a_known_rule(base):
    preset(base, "org", "overrides: {adr/nope: warn, bondstone/nope: warn, bondstone/profile: warn}")
    base.profile(extends=["starter@1", "org@1"])
    assert errors(base) == [
        (".bondstone/packs/org/preset.yaml", "overrides.adr/nope: unknown rule"),
        (".bondstone/packs/org/preset.yaml", "overrides.bondstone/nope: unknown engine rule"),
        (".bondstone/packs/org/preset.yaml", "overrides.bondstone/profile: configuration errors cannot be overridden"),
    ]


# ----------------------------------------------------------------------- locks


ORG = """
    extends: [starter@1]
    overrides: {adr/alternatives-considered: error}
    lock: [adr/alternatives-considered, bondstone/immutable, adr-capability/accepted-decision-is-applied]
"""


def test_a_preset_locks_rules_at_the_severity_in_force_after_it(base):
    preset(base, "org", ORG)
    base.profile(extends=["org@1"])
    cfg = load_config(base.root)
    assert cfg.errors == []
    assert cfg.locks == {"adr/alternatives-considered": Lock("error", "org"),
                         "bondstone/immutable": Lock("error", "org"),
                         "adr-capability/accepted-decision-is-applied": Lock("warn", "org")}
    assert cfg.rule("adr/alternatives-considered").locked


def test_a_locked_rule_may_be_raised_but_not_lowered(base):
    preset(base, "org", ORG)
    base.profile(extends=["org@1"], overrides={"adr-capability/accepted-decision-is-applied": "error"})
    assert errors(base) == []
    base.profile(extends=["org@1"], overrides={
        "adr/alternatives-considered": "warn", "bondstone/immutable": "ignore",
        "adr-capability/accepted-decision-is-applied": "info"})
    assert [message for _, message in errors(base)] == [
        "overrides.adr/alternatives-considered: the rule is locked by preset 'org'; "
        "its severity (error) can be raised but not lowered",
        "overrides.bondstone/immutable: the rule is locked by preset 'org'; "
        "its severity (error) can be raised but not lowered",
        "overrides.adr-capability/accepted-decision-is-applied: the rule is locked by preset 'org'; "
        "its severity (warn) can be raised but not lowered",
    ]


def test_a_later_preset_cannot_lower_a_locked_rule_either(base):
    preset(base, "org", ORG)
    preset(base, "team", "overrides: {adr/alternatives-considered: info}")
    base.profile(extends=["org@1", "team@1"])
    assert errors(base) == [(".bondstone/packs/team/preset.yaml",
                             "overrides.adr/alternatives-considered: the rule is locked by preset 'org'; "
                             "its severity (error) can be raised but not lowered")]
    base.profile(extends=["team@1", "org@1"])  # lowered before the lock: the floor is what org leaves
    assert errors(base) == []


def test_the_first_lock_sets_the_floor(base):
    preset(base, "org", ORG)
    preset(base, "team", "overrides: {adr-capability/accepted-decision-is-applied: error}\n"
                         "lock: [adr-capability/accepted-decision-is-applied]")
    base.profile(extends=["org@1", "team@1"], overrides={"adr-capability/accepted-decision-is-applied": "warn"})
    cfg = load_config(base.root)
    assert cfg.errors == [] and cfg.locks["adr-capability/accepted-decision-is-applied"] == Lock("warn", "org")


def test_a_lock_must_name_a_known_rule(base):
    preset(base, "org", "lock: [adr/nope, bondstone/profile]")
    base.profile(extends=["starter@1", "org@1"])
    assert errors(base) == [
        (".bondstone/packs/org/preset.yaml", "lock: adr/nope: unknown rule"),
        (".bondstone/packs/org/preset.yaml", "lock: bondstone/profile: configuration errors cannot be overridden"),
    ]


def test_a_rule_locked_where_it_is_declared_keeps_its_message(base):
    preset(base, "org", "rules:\n- {id: titled, locked: true, severity: warn, when: {type: adr:Decision}, "
                        "require: [{field: title}]}")
    base.profile(extends=["starter@1", "org@1"], overrides={"org/titled": "info"})
    assert errors(base) == [(".bondstone/profile.yaml", "overrides.org/titled: the rule is locked; "
                                                       "its severity (warn) can be raised but not lowered")]


def test_a_rule_locked_by_a_preset_cannot_be_waived(base):
    preset(base, "org", ORG)
    waiver = {"reason": "not yet", "expires": "2027-01-01"}
    base.profile(extends=["org@1"], waivers=[
        {"rule": "adr-capability/accepted-decision-is-applied", "node": "ADR-001", **waiver},
        {"rule": "bondstone/immutable", **waiver}])
    base.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    found = sorted((d.rule, d.message) for d in check(base, today=TODAY))
    assert found == [
        ("adr-capability/accepted-decision-is-applied", found[0][1]),
        ("bondstone/waiver-invalid", "waiver for adr-capability/accepted-decision-is-applied (ADR-001): "
                                     "the rule is locked and cannot be waived"),
        ("bondstone/waiver-invalid", "waiver for bondstone/immutable (all nodes): the rule is locked and cannot be waived"),
    ]


def test_rules_and_explain_name_the_preset_that_locks(base):
    preset(base, "org", ORG)
    base.profile(extends=["org@1"])
    cfg = load_config(base.root)
    listed = {rule.id: rule for rule in agent.list_rules(cfg)}
    assert (listed["bondstone/immutable"].locked, listed["bondstone/immutable"].locked_by) == (True, "org")
    assert (listed["bondstone/profile"].locked, listed["bondstone/profile"].locked_by) == (True, None)
    assert "bondstone/immutable: " in agent.rules_text(list(listed.values()))
    assert "[locked]" in next(line for line in agent.rules_text(list(listed.values())).splitlines()
                              if "bondstone/immutable:" in line)
    assert "Locked by preset org: it can be raised but not lowered or waived." in agent.explain_text(
        cfg, "bondstone/immutable")
    assert "This rule cannot be overridden or waived." in agent.explain_text(cfg, "bondstone/profile")
    explained = agent.explain_text(cfg, "adr/alternatives-considered")
    assert "Severity: error (set by the preset org; default: warn); locked" in explained
    assert agent.explain(cfg, "adr/alternatives-considered")["locked_by"] == "org"


# ----------------------------------------------------------------------- with documents


def test_a_repository_on_a_preset_checks_like_one_that_lists_the_packs(base):
    base.profile(extends=["starter@1"], code={"include": ["src/**/*.py"]})
    base.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    base.write("docs/capabilities/a.md", capability("CAP-a", "AA", extra="constrained_by: [ADR-001]\n"))
    base.write("src/code.py", "# bondstone: REQ-AA-001\nx = 1\n")
    assert [(d.rule, d.message) for d in check(base, today=TODAY)] == []


def test_the_agent_instructions_name_the_preset_and_its_rule(base):
    base.write(".bondstone/packs/starter/instructions.md", "- Update the capability with the code.\n")
    base.edit(".bondstone/packs/starter/preset.yaml", "version: 1.2.0", "version: 1.2.0\ninstructions: instructions.md")
    base.profile(extends=["starter@1"], code={"include": ["src/**/*.py"]})
    text = agent.instructions(load_config(base.root))
    assert ("Active packs, bridges and presets: adr@1.0.0 (pack), capability@1.0.0 (pack), "
            "adr-capability@1.0.0 (bridge), starter@1.2.0 (preset)") in text
    assert "**`starter/code-change-updates-living-spec`** (error)" in text
    assert "- Update the capability with the code." in text
