"""Commands, exit codes and golden output.

Golden files live in tests/golden. To accept new output on purpose, run
`BONDSTONE_UPDATE_GOLDEN=1 uv run pytest tests/test_cli.py` and review the diff."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import adr, capability, standard

from bondstone import __version__
from bondstone.cli import main

GOLDEN = Path(__file__).parent / "golden"


def run(capsys, *argv):
    code = main([str(arg) for arg in argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def assert_golden(name: str, actual: str) -> None:
    path = GOLDEN / name
    if os.environ.get("BONDSTONE_UPDATE_GOLDEN"):
        path.parent.mkdir(exist_ok=True)
        path.write_text(actual, encoding="utf-8")
    assert path.is_file(), f"missing golden file {path}"
    assert actual == path.read_text(encoding="utf-8")


@pytest.fixture
def broken(project):
    """A repository with one diagnostic of every shape: hint, no hint, no line, fix, warn, info."""
    standard(project, docs=["docs/**/*.md"], code={"include": ["src/*.py"]},
             overrides={"bondstone/view-stale": "error", "bondstone/supersede-orphan": "info"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "superseded"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="colour: red\nsupersedes: ADR-009\n",
                                               body="## Context\n\n## Decision\n\n## Consequences\n"))
    project.write("docs/capabilities/a.md", capability(extra="constrained_by: [ADR-001]\n"))
    project.write("docs/notes.md", "# Loose notes\n")
    project.write("src/a.py", "# bondstone: REQ-ZZ-009\nx = 1\n")
    return project


@pytest.fixture
def clean(project):
    standard(project, docs=["docs/**/*.md"], overrides={"bondstone/view-stale": "error"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    project.write("docs/capabilities/a.md", capability(extra="constrained_by: [ADR-001]\n"))
    assert main(["--root", str(project.root), "gen"]) == 0
    return project


# --------------------------------------------------------------------------- check


def test_check_text_output(broken, capsys):
    code, out, err = run(capsys, "--root", broken.root, "check")
    assert (code, err) == (1, "")
    assert_golden("check.txt", out)


def test_check_json_output(broken, capsys):
    code, out, err = run(capsys, "check", "--root", broken.root, "--format", "json")
    assert (code, err) == (1, "")
    assert_golden("check.json", out)
    payload = json.loads(out)
    assert payload["version"] == 1
    assert payload["summary"] == {"errors": 6, "warnings": 3, "info": 1, "nodes": 4}
    stale = next(d for d in payload["diagnostics"] if d["rule"] == "bondstone/view-stale")
    assert stale["fix"] == {"command": ["bondstone", "gen"]}
    assert all(set(d) <= {"rule", "severity", "path", "line", "node", "message", "hint", "fix"}
               for d in payload["diagnostics"])


def test_check_clean_repository(clean, capsys):
    assert run(capsys, "--root", clean.root, "check") == (0, "✓ 0 error(s), 0 warning(s), 3 nodes\n", "")
    code, out, _ = run(capsys, "--root", clean.root, "check", "--format", "json")
    assert code == 0
    assert json.loads(out) == {"version": 1, "summary": {"errors": 0, "warnings": 0, "info": 0, "nodes": 3},
                               "diagnostics": []}


def test_fail_on_warn(clean, capsys):
    clean.write("docs/adr/ADR-002-b.md", adr("ADR-002"))  # accepted but applied nowhere: a warning
    assert main(["--root", str(clean.root), "gen"]) == 0
    capsys.readouterr()
    code, out, _ = run(capsys, "--root", clean.root, "check")
    assert code == 0 and "warn adr-capability/accepted-decision-is-applied" in out
    assert out.endswith("✓ 0 error(s), 1 warning(s), 4 nodes\n")
    assert run(capsys, "--root", clean.root, "check", "--fail-on", "warn")[0] == 1
    assert run(capsys, "--root", clean.root, "check", "--fail-on", "error")[0] == 0


# --------------------------------------------------------------------------- gen


def test_gen_writes_views_once(broken, capsys):
    assert run(capsys, "--root", broken.root, "gen") == (0, "wrote docs/generated/decisions.md\n", "")
    assert broken.read("docs/generated/decisions.md").startswith("<!-- bondstone:generated view=adr/decision-log;")
    assert run(capsys, "gen", "--root", broken.root) == (0, "views are up to date\n", "")
    code, out, _ = run(capsys, "--root", broken.root, "check")
    assert code == 1 and "bondstone/view-stale" not in out


# --------------------------------------------------------------------------- configuration errors (exit 2)


@pytest.fixture
def misconfigured(project):
    standard(project, packs=["adr@1", "capability@2", "missing@1"],
             overrides={"adr/alternatives-considered": False, "bondstone/view-stale": "ignore"})
    return project


def test_schema_errors_stop_everything_with_exit_code_2(misconfigured, capsys):
    code, out, err = run(capsys, "--root", misconfigured.root, "check")
    assert code == 2
    assert_golden("config-error.txt", out)
    assert err == "bondstone: the configuration is invalid; nothing was checked\n"


def test_configuration_errors_in_json(project, capsys):
    standard(project, packs=["adr@1", "capability@2", "missing@1"])
    code, out, _ = run(capsys, "--root", project.root, "check", "--format", "json")
    assert code == 2
    assert_golden("config-error.json", out)
    payload = json.loads(out)
    assert "nodes" not in payload["summary"]
    assert {d["rule"] for d in payload["diagnostics"]} == {"bondstone/profile"}


def test_gen_refuses_an_invalid_configuration(misconfigured, capsys):
    code, out, _ = run(capsys, "--root", misconfigured.root, "gen")
    assert code == 2 and "bondstone/profile" in out
    assert not (misconfigured.root / "docs/generated").exists()


def test_profile_check(clean, misconfigured, capsys):
    # `clean` and `misconfigured` share the project; the last profile written wins
    code, out, err = run(capsys, "--root", misconfigured.root, "profile", "check")
    assert (code, err) == (2, "")
    assert "overrides.adr/alternatives-considered: severity is the YAML boolean false" in out

    standard(clean, bridges=[])
    code, out, _ = run(capsys, "--root", clean.root, "profile", "check")
    assert code == 0
    assert_golden("profile-check.txt", out)
    code, out, _ = run(capsys, "profile", "check", "--root", clean.root, "--format", "json")
    assert code == 0
    assert json.loads(out)["summary"] == {"errors": 0, "warnings": 1, "info": 0}

    standard(clean, bridges=[], overrides={"bondstone/unbridged-packs": "ignore"})
    assert run(capsys, "--root", clean.root, "profile", "check") == (0, "✓ 0 error(s), 0 warning(s)\n", "")


# --------------------------------------------------------------------------- environment errors (exit 3)


def test_missing_root_and_missing_profile_exit_with_3(tmp_path, capsys, monkeypatch):
    code, out, err = run(capsys, "--root", tmp_path / "nope", "check")
    assert (code, out) == (3, "") and "is not a directory" in err
    code, out, err = run(capsys, "--root", tmp_path, "check")
    assert (code, out) == (3, "") and err == f"bondstone: no .bondstone/profile.yaml in {tmp_path.resolve()}\n"
    monkeypatch.chdir(tmp_path)
    code, _, err = run(capsys, "gen")
    assert code == 3 and "no .bondstone/profile.yaml found" in err


def test_root_defaults_to_the_nearest_profile(clean, capsys, monkeypatch):
    monkeypatch.chdir(clean.root / "docs" / "adr")
    assert run(capsys, "check")[0] == 0


# --------------------------------------------------------------------------- check --base


SPEC_RULE = {
    "id": "code-updates-spec",
    "description": "Code changes update the living spec they implement.",
    "on_change": {"paths": ["src/**"]},
    "require": [{"changed": {"role": "living-spec"}, "traced": True}],
    "exempt": {"trailer": "Spec-Impact"},
    "hint": 'Update the spec, or add the trailer "Spec-Impact: none (<reason>)".',
}


@pytest.fixture
def history(project):
    """A git repository whose last commits break one rule of every kind that needs a base.

    Returns the project, the base commit and the commit that carries an exemption trailer."""
    standard(project.init(), docs=["docs/**/*.md"], code={"include": ["src/*.py"]}, rules=[SPEC_RULE],
             overrides={"bondstone/view-stale": "error"})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed"))
    project.write("docs/capabilities/a.md", capability("CAP-a", "AA", extra="constrained_by: [ADR-001]\n"))
    project.write("docs/capabilities/b.md", capability("CAP-b", "BB", extra="constrained_by: [ADR-001]\n"))
    project.write("src/a.py", "# bondstone: REQ-AA-001\ndef a():\n    return 1\n")
    project.write("src/b.py", "# bondstone: REQ-BB-001\ndef b():\n    return 2\n")
    assert main(["--root", str(project.root), "gen"]) == 0
    base = project.commit("first")
    project.edit("docs/adr/ADR-001-a.md", "## Decision\n\nd", "## Decision\n\nrewritten")  # immutable
    project.edit("docs/adr/ADR-002-b.md", "status: proposed", "status: deprecated")  # not a transition
    project.write("docs/adr/ADR-003-c.md", adr("ADR-003", "rejected"))  # not the initial status
    project.edit("src/a.py", "return 1", "return 10")
    exempting = project.commit("Tidy a\n\nSpec-Impact: none [CAP-a] (no behaviour change)")
    project.edit("src/b.py", "return 2", "return 20")  # CAP-b is not updated, and this is not committed
    assert main(["--root", str(project.root), "gen"]) == 0
    return project, base, exempting


def test_check_base_text_output(history, capsys):
    project, base, exempting = history
    code, out, err = run(capsys, "--root", project.root, "check", "--base", base)
    assert (code, err) == (1, "")
    assert_golden("check-base.txt", out.replace(exempting[:7], "<commit>"))


def test_check_base_json_output(history, capsys):
    project, base, exempting = history
    code, out, _ = run(capsys, "--root", project.root, "check", "--base", base, "--format", "json")
    assert code == 1
    assert_golden("check-base.json", out.replace(exempting, "<commit>").replace(exempting[:7], "<commit>"))
    payload = json.loads(out)
    exempted = [d for d in payload["diagnostics"] if "exempted_by" in d]
    assert [(d["rule"], d["severity"], d["node"]) for d in exempted] == [("bondstone/exemption-used", "info", "CAP-a")]
    assert exempted[0]["exempted_by"] == {"commit": exempting, "trailer": "Spec-Impact",
                                          "reason": "no behaviour change"}


def test_no_exemptions_reports_the_exempted_violation(history, capsys):
    project, base, _ = history
    _, out, _ = run(capsys, "--root", project.root, "check", "--base", base, "--no-exemptions", "--format", "json")
    found = [(d["rule"], d["node"]) for d in json.loads(out)["diagnostics"] if d["rule"].startswith("profile/")]
    assert found == [("profile/code-updates-spec", "CAP-a"), ("profile/code-updates-spec", "CAP-b")]


def test_without_base_the_history_is_not_checked(history, capsys):
    project, _, _ = history
    code, out, _ = run(capsys, "--root", project.root, "check")
    assert code == 0 and out == "✓ 0 error(s), 0 warning(s), 7 nodes\n"


def test_check_base_on_a_clean_tree(history, capsys):
    project, _, _ = history
    project.commit("everything")
    assert run(capsys, "--root", project.root, "check", "--base", "HEAD") == (
        0, "✓ 0 error(s), 0 warning(s), 7 nodes\n", "")


def test_base_outside_git_and_unknown_refs_exit_with_3(clean, capsys):
    code, out, err = run(capsys, "--root", clean.root, "check", "--base", "HEAD")
    assert (code, out) == (3, "") and "is not inside a git repository" in err
    clean.init().commit("first")
    code, out, err = run(capsys, "--root", clean.root, "check", "--base", "origin/main")
    assert (code, out) == (3, "")
    assert err == ("bondstone: --base: 'origin/main' is not a commit in this repository; "
                   "fetch it, e.g. `git fetch origin`\n")
    assert run(capsys, "--root", clean.root, "check", "--base", "HEAD")[0] == 0


# --------------------------------------------------------------------------- baseline


def test_baseline_records_head_in_the_profile(clean, capsys):
    clean.write(".bondstone/profile.yaml", "# what this repository uses\n" + clean.read(".bondstone/profile.yaml"))
    before = clean.read(".bondstone/profile.yaml")
    head = clean.init().commit("first")
    assert run(capsys, "--root", clean.root, "baseline") == (0, f"baseline: {head}\n", "")
    assert clean.read(".bondstone/profile.yaml") == before.replace(
        "bondstone: 1\n", f"bondstone: 1\nbaseline: '{head}'\n")
    assert run(capsys, "--root", clean.root, "check", "--base", "HEAD")[0] == 0


def test_baseline_replaces_an_earlier_one_and_takes_a_ref(clean, capsys):
    first = clean.init().commit("first")
    assert run(capsys, "--root", clean.root, "baseline")[0] == 0
    second = clean.commit("second")
    assert run(capsys, "baseline", "HEAD~1", "--root", clean.root) == (0, f"baseline: {first}\n", "")
    assert run(capsys, "--root", clean.root, "baseline", "main")[1] == f"baseline: {second}\n"
    text = clean.read(".bondstone/profile.yaml")
    assert text.count("baseline:") == 1 and f"baseline: '{second}'" in text


def test_baseline_outside_git_or_with_an_unknown_ref_exits_with_3(clean, capsys):
    before = clean.read(".bondstone/profile.yaml")
    code, out, err = run(capsys, "--root", clean.root, "baseline")
    assert (code, out) == (3, "") and "is not inside a git repository" in err
    clean.init().commit("first")
    code, out, err = run(capsys, "--root", clean.root, "baseline", "v9.9.9")
    assert (code, out, err) == (3, "", "bondstone: baseline: 'v9.9.9' is not a commit in this repository\n")
    assert clean.read(".bondstone/profile.yaml") == before


# --------------------------------------------------------------------------- the program itself


def test_usage_errors_and_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([])
    assert exit_info.value.code == 2
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"bondstone {__version__}\n"


def test_commands_of_later_phases_do_not_exist_yet(capsys):
    for command in (["new", "adr:Decision"], ["check", "--format", "sarif"], ["explain", "x"], ["pack", "test", "."]):
        with pytest.raises(SystemExit) as exit_info:
            main(command)
        assert exit_info.value.code == 2
    capsys.readouterr()


def test_module_entry_point(clean):
    result = subprocess.run([sys.executable, "-m", "bondstone", "--root", str(clean.root), "check"],
                            capture_output=True, text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert (result.returncode, result.stdout) == (0, "✓ 0 error(s), 0 warning(s), 3 nodes\n")
