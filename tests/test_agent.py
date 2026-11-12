"""`bondstone rules` and `bondstone explain`: what is active, and what one rule means."""

import json

import pytest
from conftest import standard
from test_cli import run

from bondstone.agent import explain, explain_text, list_rules, rules_text
from bondstone.catalogue import ENGINE_RULES
from bondstone.config import load_config
from bondstone.model import Refused


@pytest.fixture
def cfg(project):
    standard(project, overrides={"adr/alternatives-considered": "error", "bondstone/code-coverage": "ignore"})
    return load_config(project.root)


def by_id(cfg):
    return {rule.id: rule for rule in list_rules(cfg)}


# --------------------------------------------------------------------------- rules


def test_declared_rules_come_first_and_engine_rules_follow(cfg):
    ids = [rule.id for rule in list_rules(cfg)]
    declared = [rule.qid for rule in cfg.rules]
    assert ids[:len(declared)] == declared
    assert ids[len(declared):] == [rule.id for rule in ENGINE_RULES]


def test_severity_is_the_effective_one_and_says_where_it_comes_from(cfg):
    rules = by_id(cfg)
    overridden = rules["adr/alternatives-considered"]
    assert (overridden.severity, overridden.default, overridden.set_by) == ("error", "warn", "profile")
    untouched = rules["capability/requirement-has-scenario"]
    assert (untouched.severity, untouched.default, untouched.set_by) == ("error", "error", "default")
    assert rules["bondstone/code-coverage"].severity == "ignore"
    assert rules["bondstone/view-stale"].set_by == "profile"  # the test profile ignores stale views


def test_kind_and_source_of_a_rule(cfg):
    rules = by_id(cfg)
    assert rules["adr/alternatives-considered"].kind == "node"
    assert rules["adr/alternatives-considered"].declared_in == ".bondstone/packs/adr/pack.yaml"
    assert rules["adr-capability/accepted-decision-is-applied"].declared_in == ".bondstone/packs/adr-capability/bridge.yaml"
    assert (rules["bondstone/immutable"].kind, rules["bondstone/immutable"].declared_in) == ("engine", None)
    assert rules["bondstone/profile"].locked and not rules["bondstone/immutable"].locked


def test_rules_text(cfg):
    text = rules_text(list_rules(cfg))
    assert ("error  adr/alternatives-considered: Accepted decisions record the alternatives that were "
            "considered. [default: warn]\n") in text
    assert "ignore bondstone/code-coverage: " in text
    assert text.count("\n") == len(cfg.rules) + len(ENGINE_RULES)


def test_rules_command(project, cfg, capsys):
    code, out, err = run(capsys, "--root", project.root, "rules")
    assert (code, err) == (0, "") and out == rules_text(list_rules(cfg))
    code, out, _ = run(capsys, "--root", project.root, "rules", "--format", "json")
    payload = json.loads(out)
    assert code == 0 and payload["version"] == 1
    first = payload["rules"][0]
    assert first == {"id": "adr/alternatives-considered", "kind": "node", "severity": "error", "default": "warn",
                     "set_by": "profile", "locked": False,
                     "description": "Accepted decisions record the alternatives that were considered.",
                     "declared_in": ".bondstone/packs/adr/pack.yaml",
                     "hint": 'Add a "## Alternatives considered" section.'}
    assert "declared_in" not in payload["rules"][-1]


# --------------------------------------------------------------------------- explain


def test_explain_a_declared_rule(cfg):
    data = explain(cfg, "adr/alternatives-considered")
    assert data["severity"] == "error" and data["default"] == "warn"
    assert data["spec"] == {"when": {"type": "Decision", "status": "accepted"},
                            "require": [{"contains": "(?im)^#{2,3}\\s+(Alternatives|Options)"}]}
    text = explain_text(cfg, "adr/alternatives-considered")
    assert text.startswith("adr/alternatives-considered (node rule, declared in .bondstone/packs/adr/pack.yaml)\n"
                           "Severity: error (set by the profile; default: warn)\n\n"
                           "Accepted decisions record the alternatives that were considered.\n"
                           'Hint: Add a "## Alternatives considered" section.\n\nwhen:\n')


def test_explain_says_in_words_what_a_diff_rule_asks(project):
    rule = {"id": "code-updates-spec", "description": "Code changes update a living spec.",
            "on_change": {"paths": ["src/**", "lib/**"]},
            "require": [{"changed": {"role": "living-spec"}, "traced": True}]}
    standard(project, rules=[rule])
    cfg = load_config(project.root)
    sentence = ("When files matching src/**, lib/** change, it asks that every document matching role=living-spec "
                "that is tagged in the changed code changes too.")
    assert explain(cfg, "profile/code-updates-spec")["asks"] == [sentence]
    assert f"Code changes update a living spec.\n{sentence}\n\non_change:" in explain_text(cfg, "profile/code-updates-spec")
    assert "asks" not in explain(cfg, "adr/alternatives-considered")


def test_explain_an_engine_rule(cfg):
    data = explain(cfg, "bondstone/code-coverage")
    assert data["kind"] == "engine" and data["severity"] == "ignore"
    assert {"fires", "why", "fix", "note"} <= set(data) and "description" not in data
    text = explain_text(cfg, "bondstone/code-coverage")
    assert text.startswith("bondstone/code-coverage (engine rule)\nSeverity: ignore (set by the profile; default: warn)\n")
    assert "\nFires when: " in text and "\nWhy: " in text and "\nFix: " in text and "\nNote: " in text


def test_explain_says_when_a_rule_cannot_be_loosened(project, cfg):
    assert explain_text(cfg, "bondstone/profile").endswith("This rule cannot be overridden or waived.\n")
    pack = project.read(".bondstone/packs/adr/pack.yaml").replace("severity: warn", "severity: warn\n    locked: true")
    project.pack("adr", pack)
    text = explain_text(load_config(project.root), "adr/alternatives-considered")
    assert ("Severity: error (set by the profile; default: warn); "
            "locked: it can be raised but not lowered or waived\n") in text


@pytest.mark.parametrize("asked, suggestion", [
    ("alternatives-considered", "adr/alternatives-considered"),
    ("bondstone/immutabel", "bondstone/immutable"),
    ("adr/alternatives", "adr/alternatives-considered"),
])
def test_explain_suggests_a_rule_for_an_unknown_id(cfg, asked, suggestion):
    with pytest.raises(Refused, match=f"unknown rule '{asked}'; did you mean {suggestion}"):
        explain(cfg, asked)


def test_explain_without_a_suggestion(cfg):
    with pytest.raises(Refused, match="unknown rule 'zzz'; `bondstone rules` lists them"):
        explain(cfg, "zzz")


def test_explain_command(project, cfg, capsys):
    code, out, err = run(capsys, "--root", project.root, "explain", "bondstone/immutable")
    assert (code, err) == (0, "") and out == explain_text(cfg, "bondstone/immutable")
    code, out, _ = run(capsys, "--root", project.root, "explain", "bondstone/immutable", "--format", "json")
    assert code == 0 and json.loads(out)["fix"] == "Undo the edit and create a new document that supersedes it."
    code, out, err = run(capsys, "--root", project.root, "explain", "nope")
    assert (code, out) == (1, "") and err.startswith("bondstone: unknown rule 'nope'")
