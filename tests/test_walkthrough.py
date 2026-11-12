"""The exit criterion of phase 3, as a script: an agent's feature task, played with commands only.

The task is "add snoozing a reminder" on a copy of examples/habit-tracker. The script does what
the generated instructions tell an agent to do. Ids, paths, statuses and views change only
through bondstone commands; the script writes document content and code, as an agent would.
It reads JSON output only and runs every `fix.command` it is given. At the end
`check --base` passes, and nobody edited a file by hand to get there."""

import json
import re
import shutil

import pytest
from conftest import EXAMPLE, Project

from bondstone.cli import main


class Agent:
    """Runs bondstone the way an agent does: one command, JSON back."""

    def __init__(self, project: Project, capsys):
        self.project, self.capsys = project, capsys
        self.commands: list[str] = []

    def run(self, *args: str) -> tuple[int, dict]:
        self.commands.append(args[0])
        self.capsys.readouterr()
        code = main(["--root", str(self.project.root), *args, "--format", "json"])
        out = self.capsys.readouterr().out
        return code, json.loads(out)

    def run_plain(self, *args: str) -> int:
        self.commands.append(args[0])
        code = main(["--root", str(self.project.root), *args])
        self.capsys.readouterr()
        return code

    def check_until_clean(self, rounds: int = 3) -> tuple[int, dict, int]:
        """Check, run the fix commands of the diagnostics, and check again: (exit code, last report, rounds)."""
        for used in range(1, rounds + 1):
            code, report = self.run("check", "--base", "HEAD")
            fixes = [d["fix"]["command"] for d in report["diagnostics"] if "fix" in d]
            if code == 0 or not fixes:
                return code, report, used
            for command in dict.fromkeys(tuple(fix) for fix in fixes):
                assert command[0] == "bondstone"
                assert self.run_plain(*command[1:]) == 0
        return code, report, rounds


@pytest.fixture
def agent(tmp_path, capsys) -> Agent:
    root = tmp_path / "habit-tracker"
    shutil.copytree(EXAMPLE, root)
    project = Project(root).init()
    project.commit("the example")
    return Agent(project, capsys)


REQUIREMENT = """
### REQ-REM-003: Snooze a reminder

Status: planned

The app SHALL let the user snooze a reminder for 10, 30 or 60 minutes.

#### Scenario: Snooze for ten minutes

- Given a reminder shown at 07:45
- When the user snoozes it for 10 minutes
- Then the reminder is shown again at 07:55
"""

CODE = """
// bondstone: REQ-REM-003
Future<void> snoozeReminder(Habit habit, Duration delay) async {
  await notifications.schedule(habit.id, DateTime.now().add(delay));
}
"""


def test_an_agent_adds_a_feature_and_check_passes_without_hand_edits(agent):
    project = agent.project

    # 1. What do I need to read before touching the reminder code?
    code, context = agent.run("context", "--for", "app/lib/reminders.dart")
    assert code == 0
    nodes = {node["id"]: node for node in context["nodes"]}
    assert {"REQ-REM-001", "REQ-REM-002", "CAP-reminders", "ADR-003"} <= set(nodes)
    assert nodes["ADR-003"]["note"].startswith("immutable in status 'accepted'")
    assert [(rule["id"], rule["must_change"]) for rule in context["rules"]] == [
        ("profile/code-change-updates-living-spec", ["CAP-reminders"])]

    # 2. The feature needs a decision: scaffold it and write its content. It stays `proposed`.
    code, created = agent.run("new", "adr:Decision", "--title", "Snooze with a second local notification")
    assert (code, created["id"]) == (0, "ADR-004")
    decision = created["path"]
    text = re.sub(r"<!-- todo:.*?-->", "Snoozing schedules one more local notification; no server is involved.",
                  project.read(decision))
    (project.root / decision).write_text(text, encoding="utf-8")

    # 3. The living spec gets the requirement, planned for now, and points at the decision.
    spec = "docs/capabilities/reminders.md"
    project.edit(spec, "constrained_by: [ADR-002, ADR-003]", "constrained_by: [ADR-002, ADR-003, ADR-004]")
    (project.root / spec).write_text(project.read(spec).rstrip("\n") + "\n" + REQUIREMENT, encoding="utf-8")

    # 4. The code, tagged for the requirement it implements.
    source = "app/lib/reminders.dart"
    (project.root / source).write_text(project.read(source).rstrip("\n") + "\n" + CODE, encoding="utf-8")

    # 5. The requirement is implemented now: move it along its lifecycle with the command.
    code, change = agent.run("status", "REQ-REM-003", "active")
    assert (code, change["old"], change["new"], change["changed"]) == (0, "planned", "active", True)
    assert "Status: planned" not in project.read(spec)

    # 6. A last wording change to the decision's title makes the decision log stale.
    project.edit(decision, "title: Snooze with a second local notification", "title: Snooze with one more local notification")

    # 7. Check against the base, and run what the diagnostics say fixes them.
    code, first = agent.run("check", "--base", "HEAD")
    assert code == 1
    assert [(d["rule"], d.get("fix")) for d in first["diagnostics"]] == [
        ("bondstone/view-stale", {"command": ["bondstone", "gen"]})]
    code, report, rounds = agent.check_until_clean()
    assert (code, rounds) == (0, 2)
    assert report["summary"] == {"errors": 0, "warnings": 0, "info": 0, "nodes": 17}
    assert report["diagnostics"] == []

    # Only commands touched ids, paths, statuses and views; the views say what the documents say.
    assert "| [ADR-004](../adr/ADR-004-snooze-with-a-second-local-notification.md) | Snooze with one more local notification | proposed |" in project.read("docs/generated/decisions.md")
    assert "REQ-REM-003" in project.read("docs/generated/requirements.md")
    assert set(agent.commands) == {"context", "new", "status", "check", "gen"}


def test_an_agent_that_forgets_the_spec_is_told_which_one_to_update(agent):
    project = agent.project
    source = "app/lib/reminders.dart"
    project.edit(source, "days: 14", "days: 21")
    code, report = agent.run("check", "--base", "HEAD")
    assert code == 0  # the example's profile makes this rule a warning
    assert [(d["rule"], d["severity"], d["node"], d["path"]) for d in report["diagnostics"]] == [
        ("profile/code-change-updates-living-spec", "warn", "CAP-reminders", "docs/capabilities/reminders.md")]
    code, context = agent.run("context", "--base", "HEAD")
    assert [(node["id"], node["changed"]) for node in context["nodes"]][:2] == [
        ("REQ-REM-001", False), ("CAP-reminders", False)]
    project.edit("docs/capabilities/reminders.md", "last 14 days", "last 21 days")
    code, report = agent.run("check", "--base", "HEAD")
    assert (code, report["diagnostics"]) == (0, [])


def test_an_agent_replaces_a_decision_it_may_not_edit(agent):
    project = agent.project
    code, result = agent.run("supersede", "ADR-003", "--title", "Schedule reminders with push notifications")
    assert code == 0 and result["id"] == "ADR-004"
    assert result["updated"] == [
        "docs/adr/ADR-003-local-notifications-for-reminders.md (status: accepted -> superseded)",
        "docs/capabilities/reminders.md (constrained_by: ADR-003 -> ADR-004)"]
    text = re.sub(r"<!-- todo:.*?-->", "Push notifications reach the user on every device.", project.read(result["path"]))
    (project.root / result["path"]).write_text(text, encoding="utf-8")
    code, report, _ = agent.check_until_clean()
    assert (code, report["diagnostics"]) == (0, [])
