"""`bondstone report`: counts about a repository's documentation."""

import datetime as dt
import json

import pytest
from conftest import ADR_BODY, Project, adr, capability, standard

from bondstone import resolve as resolver
from bondstone.baseline import record_known
from bondstone.cli import main
from bondstone.config import load_config
from bondstone.git import GitRepository
from bondstone.graph import build_graph
from bondstone.report import build_report, to_text

TODAY = dt.date(2026, 11, 13)
RULE = {"id": "code-updates-spec", "on_change": {"paths": ["src/**"]},
        "require": [{"changed": {"role": "living-spec"}, "traced": True}], "exempt": {"trailer": "Spec-Impact"}}
NO_ALTERNATIVES = ADR_BODY.replace("## Alternatives considered\n\na\n\n", "")
WAIVERS = [
    {"rule": "adr/alternatives-considered", "node": "ADR-002", "reason": "r", "expires": "2027-06-30"},
    {"rule": "adr/alternatives-considered", "node": "ADR-001", "reason": "r", "expires": "2026-12-01"},
    {"rule": "bondstone/link-broken", "reason": "r", "expires": "2026-11-01"},
    {"rule": "adr/alternatives-considered", "reason": "r"},
]


@pytest.fixture(autouse=True)
def no_installed_packages(monkeypatch):
    monkeypatch.setattr(resolver, "entry_points", lambda group: [])


@pytest.fixture
def repo(project) -> Project:
    standard(project.init(), docs=["docs/**/*.md"], code={"include": ["src/**/*.py"]}, rules=[RULE])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", body=NO_ALTERNATIVES.replace("## Consequences\n\nx\n", "")))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed"))
    project.write("docs/capabilities/a.md", capability("CAP-a", "AA", extra="constrained_by: [ADR-001]\n", requirements=(
        "### REQ-AA-001: One\n\nIt SHALL.\n\n#### Scenario: ok\n\n- Then fine\n\n"
        "### REQ-AA-002: Two\n\nIt SHALL.\n\n#### Scenario: ok\n\n- Then fine\n\n"
        "### REQ-AA-003: Three\n\nStatus: planned\n\nIt SHALL.\n\n#### Scenario: ok\n\n- Then fine\n")))
    project.write("docs/notes.md", "# Notes\n")
    project.write("src/a.py", "# bondstone: REQ-AA-001\ndef a():\n    return 1\n")
    project.commit("first")
    return project


def report(project: Project, base: str | None = None):
    cfg = load_config(project.root)
    assert cfg.errors == []
    repo = GitRepository(project.root) if base else None
    return build_report(cfg, build_graph(cfg), TODAY, repo=repo, base=base)


def test_nodes_are_counted_by_type_and_status(repo):
    assert report(repo).to_dict()["nodes"] == {"total": 6, "by_type": {
        "adr:Decision": {"total": 2, "by_status": {"accepted": 1, "proposed": 1}},
        "capability:Capability": {"total": 1, "by_status": {"active": 1}},
        "capability:Requirement": {"total": 3, "by_status": {"active": 2, "planned": 1}}}}


def test_coverage_counts_the_nodes_in_the_statuses_that_need_code(repo):
    assert report(repo).coverage == {"capability:Requirement": {"needing_code": 2, "covered": 1}}


def test_waivers_have_a_state(repo):
    standard(repo, docs=["docs/**/*.md"], waivers=WAIVERS)
    assert [(w["rule"], w.get("node"), w["state"]) for w in report(repo).waivers] == [
        ("adr/alternatives-considered", "ADR-002", "unused"),
        ("adr/alternatives-considered", "ADR-001", "expiring"),
        ("bondstone/link-broken", None, "expired"),
        ("adr/alternatives-considered", None, "invalid"),
    ]


def test_an_active_waiver(repo):
    standard(repo, docs=["docs/**/*.md"], waivers=[
        {"rule": "adr/alternatives-considered", "node": "ADR-001", "reason": "r", "expires": "2027-06-30"}])
    assert [w["state"] for w in report(repo).waivers] == ["active"]


def test_known_violations_are_counted_per_rule_and_per_type(repo):
    assert report(repo).known == {"total": 0, "by_rule": {}, "by_type": {}}
    record_known(load_config(repo.root), today=TODAY)
    assert report(repo).known == {
        "total": 4, "created": "2026-11-13",
        "by_rule": {"adr/alternatives-considered": 1, "bondstone/code-coverage": 1, "bondstone/section-missing": 1,
                    "bondstone/untyped-document": 1},
        "by_type": {"adr:Decision": 2, "(files)": 1, "capability:Requirement": 1}}


def test_exemptions_are_counted_only_with_a_base(repo):
    assert report(repo).exemptions is None
    assert "exemptions" not in report(repo).to_dict()
    base = repo.git("rev-parse", "HEAD")
    repo.edit("src/a.py", "return 1", "return 10")
    repo.commit("Tidy\n\nSpec-Impact: none (no behaviour change)")
    assert report(repo, base).exemptions == {
        "base": base, "total": 1, "by_rule": {"profile/code-updates-spec": 1}, "by_author": {"Test": 1}}


def test_text_output(repo):
    standard(repo, docs=["docs/**/*.md"], code={"include": ["src/**/*.py"]}, waivers=WAIVERS[:2])
    record_known(load_config(repo.root), today=TODAY)
    assert to_text(report(repo, "HEAD")) == (
        "Nodes: 6\n"
        "  adr:Decision: 2 (1 accepted, 1 proposed)\n"
        "  capability:Capability: 1 (1 active)\n"
        "  capability:Requirement: 3 (2 active, 1 planned)\n"
        "\n"
        "Traced to code:\n"
        "  capability:Requirement: 1 of 2 that need code (50%)\n"
        "\n"
        "Waivers: 2 (1 expiring, 1 unused)\n"
        "  unused: adr/alternatives-considered on ADR-002, until 2027-06-30\n"
        "  expiring: adr/alternatives-considered on ADR-001, until 2026-12-01\n"
        "\n"
        "Known violations: 3 (recorded 2026-11-13)\n"
        "  by rule:\n"
        "       1  bondstone/code-coverage\n"
        "       1  bondstone/section-missing\n"
        "       1  bondstone/untyped-document\n"
        "  by type:\n"
        "       1  (files)\n"
        "       1  adr:Decision\n"
        "       1  capability:Requirement\n"
        "\n"
        "Exemptions used since HEAD: 0\n")


def test_the_command_always_exits_with_0_when_it_could_report(repo, capsys):
    assert main(["--root", str(repo.root), "check"]) == 1
    capsys.readouterr()
    assert main(["--root", str(repo.root), "report", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert list(payload) == ["version", "nodes", "coverage", "waivers", "known"]
    assert main(["--root", str(repo.root), "report", "--base", "HEAD"]) == 0
    assert "Exemptions used since HEAD: 0" in capsys.readouterr().out


def test_a_configuration_error_stops_the_report(repo, capsys):
    standard(repo, packs=["adr@9"])
    assert main(["--root", str(repo.root), "report"]) == 2
