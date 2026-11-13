import re
from pathlib import Path

import bondstone
from bondstone.catalogue import BY_ID, ENGINE_RULES, default_severity, diagnostic, engine_rule
from bondstone.model import SEVERITIES

SOURCE = Path(bondstone.__file__).parent
RULE_ID = re.compile(r"""["'](bondstone/[a-z][a-z-]*)["']""")


def emitted_rule_ids() -> set[str]:
    found: set[str] = set()
    for path in SOURCE.rglob("*.py"):
        if path.name != "catalogue.py":
            found |= set(RULE_ID.findall(path.read_text(encoding="utf-8")))
    return found


def test_every_rule_the_engine_emits_is_in_the_catalogue_and_the_other_way_round():
    assert emitted_rule_ids() == set(BY_ID)


def test_catalogue_entries_are_complete_and_unique():
    assert len(BY_ID) == len(ENGINE_RULES) == 43
    for rule in ENGINE_RULES:
        assert rule.id.startswith("bondstone/")
        assert rule.severity in SEVERITIES
        assert rule.fires.endswith(".") and rule.why.endswith(".") and rule.fix.endswith(".")


def test_only_configuration_errors_cannot_be_overridden():
    assert [rule.id for rule in ENGINE_RULES if not rule.overridable] == ["bondstone/profile"]


def test_new_rules_of_v1_are_present():
    assert default_severity("bondstone/untyped-document") == "error"
    assert default_severity("bondstone/type-missing") == "error"
    assert default_severity("bondstone/tag-retired") == "warn"
    assert default_severity("bondstone/exemption-used") == "info"
    assert default_severity("bondstone/exemption-invalid") == "error"


def test_rules_that_compare_with_a_base_commit_are_present():
    for name in ("status-initial", "status-transition", "immutable", "baseline-missing"):
        assert engine_rule(f"bondstone/{name}").severity == "error"


def test_diagnostic_helper_uses_the_default_severity_unless_told_otherwise():
    assert diagnostic("bondstone/waiver-unused", "m").severity == "warn"
    assert diagnostic("bondstone/code-coverage", "m", severity="error").severity == "error"
