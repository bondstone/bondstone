"""`bondstone pack test`: fixtures of packs and bridges."""

import pytest
from conftest import ADR_PACK, Project

from bondstone.model import EnvironmentProblem
from bondstone.packtest import component_of, run_fixtures, to_dict, to_text

DECISION = """
    ---
    id: ADR-001
    type: adr:Decision
    title: Use SQLite
    status: {status}
    owner: ana
    date: 2026-01-01
    ---

    ## Context

    Text.

    ## Decision

    Text.

    ## Consequences

    Text.
"""
PROFILE = "bondstone: 1\npacks: [adr@1]\noverrides: {bondstone/view-stale: ignore}\n"


@pytest.fixture
def packs(tmp_path) -> Project:
    """A folder of packs, as a profile's source folder or a library holds them."""
    return Project(tmp_path / "packs").pack("adr", ADR_PACK, folder=".")


def case(packs: Project, name: str, status: str = "proposed", expected: str | None = "errors: []\nwarnings: []\n",
         profile: str | None = PROFILE) -> None:
    base = f"adr/fixtures/{name}"
    if profile is not None:
        packs.write(f"{base}/.bondstone/profile.yaml", profile)
    if expected is not None:
        packs.write(f"{base}/expected.yaml", expected)
    packs.write(f"{base}/docs/adr/ADR-001-use-sqlite.md", DECISION.format(status=status))


def problems(packs: Project) -> dict[str, list[str]]:
    return {result.case: result.problems for result in run_fixtures(packs.root / "adr")}


def test_fixtures_that_match_pass(packs):
    case(packs, "valid")
    case(packs, "invalid", status="accepted", expected="warnings: [adr/alternatives-considered]\n")
    results = run_fixtures(packs.root / "adr")
    assert [(r.component, r.kind, r.case, r.passed) for r in results] == [
        ("adr", "pack", "invalid", True), ("adr", "pack", "valid", True)]
    assert to_text(results) == "ok   adr/invalid\nok   adr/valid\n✓ 2 fixture(s) passed\n"
    assert to_dict(results)["summary"] == {"passed": 2, "failed": 0}


def test_a_missing_and_an_unexpected_rule_fail_the_fixture(packs):
    case(packs, "silent", expected="errors: [adr/no-such-rule, adr/no-such-rule]\n")
    case(packs, "loud", status="accepted")
    case(packs, "wrong-level", status="accepted", expected="errors: [adr/alternatives-considered]\n")
    unexpected = ("unexpected warn adr/alternatives-considered at docs/adr/ADR-001-use-sqlite.md:1: "
                  "Accepted decisions record the alternatives that were considered. "
                  "(body must match /(?im)^#{2,3}\\s+(Alternatives|Options)/)")
    assert problems(packs) == {
        "silent": ["expected error adr/no-such-rule was not reported"] * 2,
        "loud": [unexpected],
        "wrong-level": ["expected error adr/alternatives-considered was not reported", unexpected],
    }
    results = run_fixtures(packs.root / "adr")
    text = to_text(results)
    assert f"FAIL adr/loud ({(packs.root / 'adr/fixtures/loud').as_posix()})\n     unexpected warn" in text
    assert text.endswith("✗ 3 of 3 fixture(s) failed\n")
    assert to_dict(results)["fixtures"][0] == {
        "component": "adr", "kind": "pack", "case": "loud", "path": (packs.root / "adr/fixtures/loud").as_posix(),
        "passed": False, "problems": results[0].problems}


def test_rules_are_counted(packs):
    case(packs, "twice", status="accepted", expected="warnings: [adr/alternatives-considered]\n")
    packs.write("adr/fixtures/twice/docs/adr/ADR-002-other.md",
                DECISION.format(status="accepted").replace("ADR-001", "ADR-002"))
    assert len(problems(packs)["twice"]) == 1
    packs.write("adr/fixtures/twice/expected.yaml", "warnings: [adr/alternatives-considered, adr/alternatives-considered]\n")
    assert problems(packs) == {"twice": []}


def test_a_fixture_needs_a_profile_and_a_well_formed_expected_file(packs):
    case(packs, "no-profile", profile=None)
    case(packs, "no-expected", expected=None)
    case(packs, "empty-expected", expected="")
    case(packs, "bad-yaml", expected="errors: [\n")
    case(packs, "bad-shape", expected="- adr/x\n")
    case(packs, "bad-keys", expected="errors: adr/x\ninfo: []\n")
    found = problems(packs)
    assert found["no-profile"] == ["no .bondstone/profile.yaml: a fixture is a small repository with its own profile"]
    assert found["no-expected"] == ["no expected.yaml: list the expected rules under `errors` and `warnings`"]
    assert found["empty-expected"] == []
    assert len(found["bad-yaml"]) == 1 and found["bad-yaml"][0].startswith("expected.yaml: invalid YAML")
    assert found["bad-shape"] == ["expected.yaml: expected a mapping with `errors` and `warnings`"]
    assert found["bad-keys"] == ["expected.yaml: unknown key 'info' (allowed: errors, warnings)",
                                 "expected.yaml: `errors` must be a list of rule ids"]


def test_a_configuration_error_fails_the_fixture(packs):
    case(packs, "broken", profile="bondstone: 1\npacks: [adr@1, nope@1]\n")
    assert problems(packs) == {"broken": [
        "configuration error at .bondstone/profile.yaml: pack 'nope' not found in the profile's sources "
        "or in an installed package"]}


def test_a_component_without_fixtures_fails(packs):
    results = run_fixtures(packs.root / "adr")
    assert [(r.case, r.passed, r.name) for r in results] == [(None, False, "adr")]
    assert results[0].problems == ["no fixtures: add fixtures/<case>/ with a profile, documents and expected.yaml"]
    (packs.root / "adr" / "fixtures").mkdir()
    assert not run_fixtures(packs.root / "adr")[0].passed


def test_the_copy_under_test_wins_over_other_sources(packs):
    """The fixture's own source folder holds an older `adr` without the rule; the tested copy is used."""
    case(packs, "invalid", status="accepted", expected="warnings: [adr/alternatives-considered]\n")
    packs.write("adr/fixtures/invalid/.bondstone/packs/adr/pack.yaml", "id: adr\nversion: 1.0.0\n")
    assert problems(packs) == {"invalid": []}


def test_a_bridge_finds_the_packs_next_to_it(packs):
    packs.pack("note", "id: note\nversion: 1.0.0\ntypes: {Note: {id: 'N-{n}', path: 'notes/{id}.md'}}\n", folder=".")
    packs.bridge("adr-note", """
        id: adr-note
        version: 1.0.0
        requires: {adr: "^1", note: "^1"}
        links:
          explains: {from: "note:Note", to: "adr:Decision"}
    """, folder=".")
    base = "adr-note/fixtures/invalid"
    packs.write(f"{base}/.bondstone/profile.yaml",
                "bondstone: 1\npacks: [adr@1, note@1]\nbridges: [adr-note@1]\noverrides: {bondstone/view-stale: ignore}\n")
    packs.write(f"{base}/notes/N-1.md", "---\nid: N-1\ntype: note:Note\nexplains: [ADR-009]\n---\n")
    packs.write(f"{base}/expected.yaml", "errors: [bondstone/link-broken]\n")
    results = run_fixtures(packs.root / "adr-note")
    assert [(r.component, r.kind, r.problems) for r in results] == [("adr-note", "bridge", [])]


def test_component_of(packs, tmp_path):
    assert component_of(packs.root / "adr") == ("pack", "adr")
    packs.pack("renamed", "version: 1.0.0\n", folder=".")
    assert component_of(packs.root / "renamed") == ("pack", "renamed")  # no id: the folder's name
    with pytest.raises(EnvironmentProblem, match="is not a pack or a bridge: it has no pack.yaml or bridge.yaml"):
        component_of(packs.root)
    with pytest.raises(EnvironmentProblem, match="is not a directory"):
        component_of(tmp_path / "missing")
    packs.pack("broken", "id: [x\n", folder=".")
    with pytest.raises(EnvironmentProblem, match="invalid YAML"):
        component_of(packs.root / "broken")
