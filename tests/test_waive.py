"""`bondstone waive`: add a waiver to the profile."""

import datetime as dt
import json

import pytest
from conftest import ADR_BODY, Project, adr, capability, check, standard

from bondstone import resolve as resolver
from bondstone.cli import main
from bondstone.config import load_config
from bondstone.graph import build_graph
from bondstone.model import Refused
from bondstone.waive import add_entry, add_waiver

TODAY = dt.date(2026, 11, 13)
RULE = "adr/alternatives-considered"
ENTRY = '- {rule: adr/x, node: ADR-001, reason: "r", expires: 2027-01-01}'


@pytest.fixture(autouse=True)
def no_installed_packages(monkeypatch):
    monkeypatch.setattr(resolver, "entry_points", lambda group: [])


@pytest.fixture
def repo(project) -> Project:
    """An accepted decision without alternatives: one warning to waive."""
    standard(project, docs=["docs/**/*.md"])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", body=ADR_BODY.replace("## Alternatives considered\n\na\n\n", "")))
    project.write("docs/capabilities/a.md", capability(extra="constrained_by: [ADR-001]\n"))
    return project


def waive(project: Project, rule: str = RULE, node: str | None = "ADR-001", reason: str = "Decided long ago.",
          expires: str = "2027-06-30"):
    cfg = load_config(project.root)
    return add_waiver(cfg, build_graph(cfg), rule, node, reason, expires, TODAY)


# --------------------------------------------------------------------------- the edit


def test_a_profile_without_waivers_gets_the_key():
    assert add_entry("bondstone: 1\npacks: [adr@1]\n", ENTRY) == f"bondstone: 1\npacks: [adr@1]\n\nwaivers:\n  {ENTRY}\n"


def test_an_entry_goes_after_the_last_one_with_its_indentation():
    text = "bondstone: 1\nwaivers:\n    # old ones\n    - {rule: a/b, reason: r, expires: 2027-01-01}\n\n# views follow\nviews: []\n"
    assert add_entry(text, ENTRY) == (
        "bondstone: 1\nwaivers:\n    # old ones\n    - {rule: a/b, reason: r, expires: 2027-01-01}\n"
        f"    {ENTRY}\n\n# views follow\nviews: []\n")


def test_an_empty_list_becomes_a_block():
    assert add_entry("waivers: []  # none yet\nviews: []\n", ENTRY) == f"waivers:\n  {ENTRY}\nviews: []\n"
    assert add_entry("bondstone: 1\nwaivers:\n", ENTRY) == f"bondstone: 1\nwaivers:\n  {ENTRY}\n"


def test_waivers_written_on_one_line_are_left_to_the_author():
    with pytest.raises(Refused, match="add the waiver by hand"):
        add_entry("waivers: [{rule: a/b, reason: r, expires: 2027-01-01}]\n", ENTRY)


# --------------------------------------------------------------------------- the command


def test_a_waiver_is_written_and_applies(repo):
    assert [(d.rule, d.node) for d in check(repo, TODAY)] == [(RULE, "ADR-001")]
    before = repo.read(".bondstone/profile.yaml")
    waived = waive(repo)
    assert waived.to_dict() == {"rule": RULE, "node": "ADR-001", "reason": "Decided long ago.",
                                "expires": "2027-06-30", "path": ".bondstone/profile.yaml"}
    assert repo.read(".bondstone/profile.yaml") == (
        before + '\nwaivers:\n  - {rule: adr/alternatives-considered, node: ADR-001, '
                 'reason: "Decided long ago.", expires: 2027-06-30}\n')
    assert check(repo, TODAY) == []


def test_a_waiver_without_a_node_covers_every_node(repo):
    repo.write("docs/notes.md", "# Notes\n")
    waive(repo, "bondstone/untyped-document", None, "Notes move out next month.")
    assert load_config(repo.root).waivers == [
        {"rule": "bondstone/untyped-document", "reason": "Notes move out next month.", "expires": "2027-06-30"}]
    assert "bondstone/untyped-document" not in [d.rule for d in check(repo, TODAY)]


def test_a_reason_with_quotes_and_colons_survives(repo):
    waive(repo, reason='Kept: the "old" way,\n  see #12')
    assert load_config(repo.root).waivers[0]["reason"] == 'Kept: the "old" way, see #12'


@pytest.mark.parametrize("change, message", [
    ({"rule": "adr/alternatives"}, "unknown rule 'adr/alternatives'; did you mean adr/alternatives-considered?"),
    ({"rule": "bondstone/profile"}, "configuration errors cannot be waived"),
    ({"node": "ADR-404"}, "no node with id 'ADR-404'"),
    ({"reason": "  "}, "--reason is empty"),
    ({"expires": "next year"}, "'next year' is not a date such as 2027-11-13"),
    ({"expires": "2026-11-12"}, "2026-11-12 is in the past"),
])
def test_what_check_would_reject_is_refused(repo, change, message):
    before = repo.read(".bondstone/profile.yaml")
    with pytest.raises(Refused) as refused:
        waive(repo, **change)
    assert message in str(refused.value)
    assert repo.read(".bondstone/profile.yaml") == before


def test_a_waiver_may_end_today(repo):
    assert waive(repo, expires="2026-11-13").expires == "2026-11-13"


def test_a_locked_rule_cannot_be_waived(repo):
    repo.write(".bondstone/packs/org/preset.yaml", f"id: org\nversion: 1.0.0\nlock: [{RULE}]\n")
    standard(repo, docs=["docs/**/*.md"], extends=["org@1"])
    with pytest.raises(Refused, match="is locked by org and cannot be waived"):
        waive(repo)


def test_the_same_waiver_twice_is_refused(repo):
    waive(repo)
    with pytest.raises(Refused, match="already waived for ADR-001 until 2027-06-30"):
        waive(repo, reason="again")


def test_the_command_line(repo, capsys):
    argv = ["--root", str(repo.root), "waive", RULE, "ADR-001", "--reason", "Decided long ago.", "--expires", "2099-01-01"]
    assert main(argv) == 0
    assert capsys.readouterr().out == f"waived {RULE} for ADR-001 until 2099-01-01 (.bondstone/profile.yaml)\n"
    assert main([*argv, "--format", "json"]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out)["error"]["kind"] == "refused" and "already waived" in captured.err
    assert main(["--root", str(repo.root), "waive", "bondstone/waiver-unused", "--reason", "r", "--expires", "2099-01-01",
                 "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "version": 1, "rule": "bondstone/waiver-unused", "reason": "r", "expires": "2099-01-01",
        "path": ".bondstone/profile.yaml"}
