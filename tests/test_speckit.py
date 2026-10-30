"""Tests for docs/capabilities/speckit.md. Each test carries the example ID it proves."""

import json
import os
import re
import subprocess

import pytest

from conftest import EXTENSION, HOOK, PRESET, WRAPPER, change, fm, junit


# SPECKIT-1 Four commands

def test_SPECKIT_1_1_manifest_declares_four_commands():
    text = (EXTENSION / "extension.yml").read_text()
    names = re.findall(r"name: (speckit\.bondstone\.[a-z-]+)", text)
    assert names == ["speckit.bondstone.status", "speckit.bondstone.next",
                     "speckit.bondstone.write", "speckit.bondstone.check"]
    for f in re.findall(r"file: (commands/\S+)", text):
        assert (EXTENSION / f).is_file()


# SPECKIT-2 Command files relay, never compute

FORBIDDEN = ["brief", "roadmap", "capability spec", "PRD", "requirement-has-example", "delta-applied",
             "inception", "foundation"]
PROHIBITIONS = ["`status`, `verified` or a `Verified:` line", "`bondstone approve` or `bondstone verify`",
                "reuse an ID"]


@pytest.mark.parametrize("name", ["status", "next", "write", "check"])
def test_SPECKIT_2_1_command_files_relay_and_prohibit(name):
    text = (EXTENSION / "commands" / f"{name}.md").read_text()
    for word in FORBIDDEN:
        assert word.lower() not in text.lower(), f"{name}.md names {word}"
    for p in PROHIBITIONS:
        assert p in text, f"{name}.md lacks: {p}"


# SPECKIT-3 Wrapper script

def test_SPECKIT_3_1_wrapper_passes_exit_code(proj):
    proj.write({"docs/capabilities/sync.md": "no front-matter\n"})
    r = proj.run("check", script=WRAPPER)
    assert r.returncode == 1 and "parse-error" in r.stdout
    assert proj.run("bogus", script=WRAPPER).returncode == 2


# SPECKIT-4 Spec Kit folders are stories

def test_SPECKIT_4_1_finished_when_every_task_checked(proj):
    proj.add_change("007-photo", change("ST-1", ["SYNC-1"], tasks=[True] * 6 + [False] * 5))
    ch = proj.load().changes[0]
    assert ch.folder == "specs/007-photo" and not ch.finished


def test_SPECKIT_4_2_spec_needs_story_or_quick_track(proj):
    proj.add_change("007-photo", change(proves=["SYNC-1"]))
    assert proj.findings("change-has-story")
    proj.add_change("007-photo", change(track="quick"))
    assert not proj.findings("change-has-story")


def test_SPECKIT_4_3_no_story_before_its_prd_is_approved(proj):
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("status: stable", "status: draft"))
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"]))
    assert proj.findings("story-before-approval")


def test_SPECKIT_4_4_timestamp_folders_are_changes(proj):
    proj.add_change("20261030-101500-offline", change("ST-1", ["SYNC-1"]))
    assert proj.load().changes[0].story == "ST-1"


# SPECKIT-5 Analyze-time checks

def test_SPECKIT_5_1_spec_must_not_restate_a_requirement(proj):
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], body=(
        "The app shall keep every edit made offline until it reaches the server.")))
    assert proj.findings("change-restates-requirement")


def test_SPECKIT_5_2_plan_declares_expected_impact(proj):
    files = change("ST-1", ["SYNC-1"])
    files["plan.md"] = "# Plan\n"
    proj.add_change("001-offline", files)
    assert proj.findings("change-plan-impact")


def test_SPECKIT_5_3_tasks_name_every_example(proj):
    files = change("ST-1", ["SYNC-1"], tasks=[False], examples=["SYNC-1.1", "SYNC-1.2"])
    files["tasks.md"] = files["tasks.md"].replace("test_SYNC_1_2", "test_other")
    proj.add_change("001-offline", files)
    msgs = [f.message for f in proj.findings("change-tasks-cover-examples")]
    assert msgs == ["no test task names SYNC-1.2"]


def test_SPECKIT_5_4_tasks_include_the_living_doc_update(proj):
    files = change("ST-1", ["SYNC-1"], tasks=[False])
    files["tasks.md"] = files["tasks.md"].replace("Update the living docs", "Polish")
    proj.add_change("001-offline", files)
    assert any("living docs" in f.message for f in proj.findings("change-tasks-cover-examples"))


def test_SPECKIT_5_5_change_option_limits_findings(proj):
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], plan=False, tasks=[False],
                                          examples=["SYNC-1.1", "SYNC-1.2"]))
    proj.add_change("002-conflict", change("ST-2", ["SYNC-2"]))
    (proj.root / "specs/002-conflict/plan.md").write_text("# Plan\n")
    r = proj.run("check", "--change", "specs/001-offline")
    assert r.returncode == 0 and "002-conflict" not in r.stdout


# SPECKIT-6 Living doc changes

def test_SPECKIT_6_1_finished_story_records_living_doc_changes(proj):
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], tasks=[True], living="<!-- todo -->"))
    assert proj.findings("change-living-docs")
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], tasks=[True], living="- None: refactor only"))
    assert not proj.findings("change-living-docs")


# SPECKIT-7 Check report

def test_SPECKIT_7_1_sorted_lines_and_exit_code(proj):
    proj.write({"docs/capabilities/sync.md": "no front-matter\n", "docs/glossary.md": "none\n"})
    r = proj.run("check")
    lines = r.stdout.splitlines()
    assert r.returncode == 1
    assert lines[:-1] == sorted(lines[:-1])
    assert re.match(r"^errors: \d+ · warnings: \d+$", lines[-1])
    assert all(re.match(r"^\S+:\d+: (error|warning) [a-z-]+: ", l) for l in lines[:-1])


def test_SPECKIT_7_2_same_files_same_bytes(proj):
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], tasks=[True, False]))
    assert proj.run("check").stdout == proj.run("check").stdout
    assert proj.run("status").stdout == proj.run("status").stdout


def test_SPECKIT_7_3_json_report(proj):
    data = json.loads(proj.run("check", "--json").stdout)
    assert set(data) == {"schema_version", "summary", "findings", "requirements"}
    assert {r["id"] for r in data["requirements"]} == {"SYNC-1", "SYNC-2"}


def test_SPECKIT_7_4_usage_error(proj):
    assert proj.run("check", "--nope").returncode == 2


def test_SPECKIT_7_5_staged_reads_the_index(proj):
    git = lambda *a: subprocess.run(["git", *a], cwd=proj.root, capture_output=True, text=True)
    git("init", "-q")
    git("add", "-A")
    (proj.root / "docs/capabilities/sync.md").write_text("broken, not staged\n")
    r = proj.run("check", "--staged")
    assert r.returncode == 0, r.stdout


# SPECKIT-8 Status

def test_SPECKIT_8_1_status_shows_phase_and_story_progress(proj):
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], tasks=[True, False]))
    out = proj.run("status").stdout
    assert "phase: build V-1.0" in out
    assert "ST-1 in progress (specs/001-offline: 1/4 tasks)" in out
    assert "SYNC" in out and "untested 2" in out


# SPECKIT-9 Next step

def test_SPECKIT_9_1_errors_come_first(proj):
    proj.write({"docs/glossary.md": "none\n"})
    assert proj.next()["action"] == "fix"


def test_SPECKIT_9_2_active_story_continues(proj):
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], plan=False))
    a = proj.next()
    assert (a["action"], a["command"], a["change"]) == ("run", "speckit.plan", "specs/001-offline")


def test_SPECKIT_9_3_empty_project_starts_with_the_brief(empty):
    a = empty.next()
    assert (a["action"], a["doc"], a["path"]) == ("write", "brief", "docs/brief.md")


def test_SPECKIT_9_4_first_ready_story_is_specified(proj):
    a = proj.next()
    assert (a["action"], a["command"], a["story"]) == ("run", "speckit.specify", "ST-1")
    assert "SYNC-1" in a["args"]


def test_SPECKIT_9_5_built_version_writes_release_checklist(proj):
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], tasks=[True], living="- none"))
    proj.add_change("002-conflict", change("ST-2", ["SYNC-2"], tasks=[True], living="- none"))
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("| — | |", "| — | done |").replace("| ST-1 | |", "| ST-1 | done |"))
    proj.write({"build/test-results/junit.xml": junit(test_SYNC_1_1_a="pass", test_SYNC_1_2_b="pass",
                                                      test_SYNC_2_c="pass")})
    a = proj.next()
    assert (a["action"], a["path"]) == ("write", "plan/1.0/release.md")


def test_SPECKIT_9_6_draft_prd_waits_for_approval(proj):
    roadmap = proj.root / "docs/roadmap.md"
    roadmap.write_text(roadmap.read_text().replace("Status: active", "Status: shipped"))
    proj.write({"plan/1.1/prd.md": fm("prd", "PRD-1.1", "draft", version="V-1.1") + "# PRD-1.1\n"})
    a = proj.next()
    assert (a["action"], a["doc"]) == ("approve", "PRD-1.1")


def test_SPECKIT_9_7_uncovered_requirement_needs_a_story_row(proj):
    prd = proj.root / "plan/1.0/prd.md"
    prd.write_text(prd.read_text().replace("| ST-2 | Conflicts | SYNC-2 | ST-1 | |\n", ""))
    proj.add_change("001-offline", change("ST-1", ["SYNC-1"], tasks=[True], living="- none"))
    proj.write({"build/test-results/junit.xml": junit(test_SYNC_1_1_a="pass", test_SYNC_1_2_b="pass")})
    a = proj.next()
    assert a["action"] == "write" and "SYNC-2" in a["reason"]


def test_SPECKIT_9_8_next_changes_no_files(proj):
    before = sorted(p.as_posix() for p in proj.root.rglob("*"))
    proj.next()
    proj.next()
    assert sorted(p.as_posix() for p in proj.root.rglob("*")) == before


# SPECKIT-10 Pre-commit hook

def hook_repo(proj):
    git = lambda *a, env=None: subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=t", *a],
                                               cwd=proj.root, capture_output=True, text=True, env=env)
    ext = proj.root / ".specify/extensions/bondstone/scripts"
    (ext / "bash").mkdir(parents=True)
    (ext / "python").mkdir()
    for src, dst in ((WRAPPER, ext / "bash/bondstone.sh"), (HOOK, ext / "bash/pre-commit.sh"),
                     (EXTENSION / "scripts/python/bondstone_stopgap.py", ext / "python/bondstone_stopgap.py")):
        dst.write_text(src.read_text())
    git("init", "-q")
    git("add", "-A")
    git("commit", "-qm", "init", "--no-verify")
    hook = proj.root / ".git/hooks/pre-commit"
    hook.write_text("#!/usr/bin/env bash\nexec bash .specify/extensions/bondstone/scripts/bash/pre-commit.sh\n")
    hook.chmod(0o755)
    return git


def env_with(agent):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_CHILD_SESSION"}
    if agent:
        env["CLAUDE_CODE_CHILD_SESSION"] = "1"
    return env


def test_SPECKIT_10_1_agent_cannot_commit_an_approval(proj):
    git = hook_repo(proj)
    g = proj.root / "docs/glossary.md"
    g.write_text(g.read_text().replace("status: draft", "status: stable"))
    git("add", "-A")
    r = git("commit", "-qm", "approve", env=env_with(agent=True))
    assert r.returncode != 0 and "Approvals and manual verifications are for people" in r.stderr


def test_SPECKIT_10_2_person_can_commit_an_approval(proj):
    git = hook_repo(proj)
    g = proj.root / "docs/glossary.md"
    g.write_text(g.read_text().replace("status: draft", "status: stable"))
    git("add", "-A")
    r = git("commit", "-qm", "approve", env=env_with(agent=False))
    assert r.returncode == 0, r.stdout + r.stderr


def test_SPECKIT_10_3_staged_errors_refuse_the_commit(proj):
    git = hook_repo(proj)
    (proj.root / "docs/glossary.md").write_text("no front-matter\n")
    git("add", "-A")
    r = git("commit", "-qm", "broken", env=env_with(agent=False))
    assert r.returncode != 0 and "parse-error" in r.stdout + r.stderr


# SPECKIT-11 Preset

def manifest_entries():
    text = (PRESET / "preset.yml").read_text()
    return re.findall(r'type: "(\w+)"\s+name: "([\w.-]+)"\s+file: "([^"]+)"\s+description: "[^"]*"\s+strategy: "(\w+)"', text)


def test_SPECKIT_11_1_spec_template_carries_story_front_matter():
    entries = {n: (f, s) for _, n, f, s in manifest_entries()}
    f, strategy = entries["spec-template"]
    text = (PRESET / f).read_text()
    assert strategy == "wrap" and text.startswith("---\nstory:") and "proves:" in text
    assert text.index("{CORE_TEMPLATE}") < text.index("## Living doc changes")


def test_SPECKIT_11_2_plan_and_tasks_templates():
    entries = {n: (f, s) for _, n, f, s in manifest_entries()}
    assert "## Expected living-doc impact" in (PRESET / entries["plan-template"][0]).read_text()
    tasks = (PRESET / entries["tasks-template"][0]).read_text()
    assert "example ID" in tasks and "living docs" in tasks


def test_SPECKIT_11_3_commands_compose_without_replacing():
    entries = manifest_entries()
    commands = {n for t, n, _, s in entries if t == "command"}
    assert commands == {"speckit.specify", "speckit.plan", "speckit.tasks", "speckit.analyze", "speckit.implement"}
    assert all(s in ("append", "wrap") for _, _, _, s in entries)
    for _, _, f, _ in entries:
        assert (PRESET / f).is_file()


# SPECKIT-13 Document templates

def test_SPECKIT_13_1_every_written_doc_has_a_template():
    text = (EXTENSION / "extension.yml").read_text()
    names = set(re.findall(r"name: bondstone-([a-z-]+)\n\s+file: templates/", text))
    assert {"brief", "glossary", "ideas", "roadmap", "architecture", "prd", "runbook", "release",
            "capability", "decision", "epic"} <= names
    for n in names:
        assert (EXTENSION / "templates" / f"{n}.md").is_file()
