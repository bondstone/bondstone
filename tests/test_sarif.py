"""`check --format sarif`: SARIF 2.1.0 for code-scanning tools."""

import json

import pytest
from conftest import adr, standard
from test_cli import assert_golden, broken, clean, history, run  # noqa: F401  (fixtures)

from bondstone import __version__
from bondstone.baseline import record_known
from bondstone.config import load_config


def sarif(capsys, project, *argv):
    code, out, err = run(capsys, "--root", project.root, "check", "--format", "sarif", *argv)
    return code, json.loads(out), err


def test_golden_output(broken, capsys):
    code, out, err = run(capsys, "--root", broken.root, "check", "--format", "sarif")
    assert (code, err) == (1, "")
    assert_golden("check.sarif", out.replace(f'"version": "{__version__}"', '"version": "<version>"'))


def test_the_log_has_one_run_of_bondstone(clean, capsys):
    code, log, _ = sarif(capsys, clean)
    assert code == 0
    assert (log["version"], log["$schema"]) == ("2.1.0", "https://json.schemastore.org/sarif-2.1.0.json")
    run_, = log["runs"]
    assert run_["tool"]["driver"] == {"name": "bondstone", "version": __version__,
                                      "informationUri": "https://github.com/bondstone/bondstone", "rules": []}
    assert run_["invocations"] == [{"executionSuccessful": True}] and run_["results"] == []


def test_every_diagnostic_is_a_result_with_a_level_and_a_location(broken, capsys):
    code, log, _ = sarif(capsys, broken)
    _, plain, _ = run(capsys, "--root", broken.root, "check", "--format", "json")
    diagnostics = json.loads(plain)["diagnostics"]
    results = log["runs"][0]["results"]
    assert code == 1 and len(results) == len(diagnostics)
    levels = {"error": "error", "warn": "warning", "info": "note"}
    for diag, result in zip(diagnostics, results):
        assert (result["ruleId"], result["level"]) == (diag["rule"], levels[diag["severity"]])
        assert result["message"]["text"].startswith(diag["message"])
        location = result["locations"][0]["physicalLocation"]
        assert location["artifactLocation"] == {"uri": diag["path"], "uriBaseId": "%SRCROOT%"}
        assert location.get("region") == ({"startLine": diag["line"]} if "line" in diag else None)
    assert {result["level"] for result in results} == {"error", "warning", "note"}


def test_rules_are_listed_once_and_results_point_at_them(broken, capsys):
    _, log, _ = sarif(capsys, broken)
    rules = log["runs"][0]["tool"]["driver"]["rules"]
    ids = [rule["id"] for rule in rules]
    assert len(ids) == len(set(ids))
    for result in log["runs"][0]["results"]:
        assert rules[result["ruleIndex"]]["id"] == result["ruleId"]
    by_id = {rule["id"]: rule for rule in rules}
    engine = by_id["bondstone/link-broken"]
    assert engine["shortDescription"]["text"] == "A link points to an id that does not exist."
    assert engine["help"]["text"] and engine["defaultConfiguration"] == {"level": "error"}
    declared = by_id["adr-capability/constrained-by-live-decision"]
    assert declared["shortDescription"]["text"] == "Capabilities are constrained only by proposed or accepted decisions."
    assert declared["help"]["text"] == "Point to the decision that superseded it."
    assert by_id["bondstone/supersede-orphan"]["defaultConfiguration"] == {"level": "note"}  # overridden to info


def test_a_hint_and_a_fix_travel_with_the_result(broken, capsys):
    _, log, _ = sarif(capsys, broken)
    stale, = [r for r in log["runs"][0]["results"] if r["ruleId"] == "bondstone/view-stale"]
    assert stale["message"]["text"].endswith("\n\nRun `bondstone gen`.")
    assert stale["properties"] == {"fix": ["bondstone", "gen"]}
    broken_link, = [r for r in log["runs"][0]["results"] if r["ruleId"] == "bondstone/link-broken"]
    assert broken_link["properties"] == {"node": "ADR-002"}


def test_fingerprints_do_not_depend_on_lines(broken, capsys):
    _, before, _ = sarif(capsys, broken)
    broken.edit("docs/adr/ADR-002-b.md", "title: Decision ADR-002\n", "title: Decision ADR-002\ndeciders: [ann]\n")
    _, after, _ = sarif(capsys, broken)

    def prints(log):
        return {(r["ruleId"], r["partialFingerprints"]["bondstone/v1"]) for r in log["runs"][0]["results"]}

    def lines(log):
        return [r["locations"][0]["physicalLocation"].get("region") for r in log["runs"][0]["results"]]

    assert prints(before) == prints(after) and lines(before) != lines(after)
    assert all(len(value) == 32 for _, value in prints(before))


def test_a_known_violation_is_a_suppressed_note(broken, capsys):
    record_known(load_config(broken.root))
    code, log, _ = sarif(capsys, broken)
    results = log["runs"][0]["results"]
    known = [r for r in results if r.get("suppressions")]
    assert code == 1  # the stale view is not recorded: its rule never accepts known violations
    assert known and all(r["level"] == "note" for r in known)
    assert known[0]["suppressions"] == [
        {"kind": "external", "justification": "recorded as a known violation in .bondstone/known.json"}]
    assert [r["ruleId"] for r in results if r["level"] == "error"] == ["bondstone/view-stale"]


def test_an_exempted_violation_is_suppressed_with_its_reason(history, capsys):
    project, base, exempting = history
    _, log, _ = sarif(capsys, project, "--base", base)
    exempted, = [r for r in log["runs"][0]["results"] if r["ruleId"] == "bondstone/exemption-used"]
    assert exempted["level"] == "note"
    assert exempted["suppressions"] == [
        {"kind": "external", "justification": f"Spec-Impact: no behaviour change (commit {exempting[:7]})"}]


def test_a_configuration_error_is_a_run_that_did_not_succeed(project, capsys):
    standard(project, packs=["adr@9"])
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    code, log, err = sarif(capsys, project)
    assert code == 2 and "the configuration is invalid" in err
    run_, = log["runs"]
    assert run_["invocations"] == [{"executionSuccessful": False}]
    assert {(r["ruleId"], r["level"]) for r in run_["results"]} == {("bondstone/profile", "error")}
    assert run_["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == ".bondstone/profile.yaml"


def test_only_check_prints_sarif(clean, capsys):
    with pytest.raises(SystemExit):
        run(capsys, "--root", clean.root, "rules", "--format", "sarif")
    capsys.readouterr()


def test_an_environment_error_prints_nothing_on_stdout(tmp_path, capsys):
    code, out, err = run(capsys, "--root", tmp_path, "check", "--format", "sarif")
    assert (code, out) == (3, "") and "no .bondstone/profile.yaml" in err
