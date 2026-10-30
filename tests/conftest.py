"""Helpers that build simple-app projects in a temporary folder and run the stopgap on them."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXTENSION = REPO / "integrations" / "speckit" / "extension"
PRESET = REPO / "integrations" / "speckit" / "preset"
STOPGAP = EXTENSION / "scripts" / "python" / "bondstone_stopgap.py"
WRAPPER = EXTENSION / "scripts" / "bash" / "bondstone.sh"
HOOK = EXTENSION / "scripts" / "bash" / "pre-commit.sh"

_spec = importlib.util.spec_from_file_location("bondstone_stopgap", STOPGAP)
stopgap = importlib.util.module_from_spec(_spec)
sys.modules["bondstone_stopgap"] = stopgap
_spec.loader.exec_module(stopgap)


def fm(type_, id_, status="stable", **extra):
    lines = ["---", f"type: {type_}", f"id: {id_}", f"title: {id_} title",
             f"description: {id_} description.", f"status: {status}"]
    lines += [f"{k}: {v}" for k, v in extra.items()]
    return "\n".join(lines + ["---", ""])


SYNC = fm("capability", "SYNC", retired="[]") + """
# Sync

### SYNC-1 Save offline
Release: V-1.0

The app shall keep every edit made offline until it reaches the server.

- SYNC-1.1: GIVEN no network WHEN the person edits a note THEN the edit is kept after a restart.
- SYNC-1.2: GIVEN a kept edit WHEN the network returns THEN the edit is uploaded once.

### SYNC-2 Conflict notice
Release: V-1.0

The app shall tell the person when two devices edited the same note.

- SYNC-2: WHEN two devices edit one note THEN a conflict notice names both devices.
"""

BASE = {
    "docs/brief.md": fm("brief", "BRIEF") + "# Notes\n",
    "docs/glossary.md": fm("glossary", "GLOSSARY", "draft") + "# Glossary\n",
    "docs/ideas.md": fm("ideas", "IDEAS", "draft") + "# Ideas\n",
    "docs/roadmap.md": fm("roadmap", "ROADMAP") + """
# Roadmap

### V-1.0 MVP
Status: active · Capabilities: SYNC

### V-1.1 Sharing
Status: planned · Capabilities: SYNC
""",
    "docs/architecture/overview.md": fm("architecture", "ARCH") + "# Architecture\n",
    "docs/runbook.md": fm("runbook", "RUNBOOK", "draft") + "# Runbook\n",
    "docs/capabilities/sync.md": SYNC,
    ".specify/memory/constitution.md": "# Constitution\n\nTests are named after example IDs.\n",
    "plan/1.0/prd.md": fm("prd", "PRD-1.0", version="V-1.0") + """
# PRD-1.0

## Deltas

- ADDED: SYNC-1, SYNC-2

## Stories

| ID | Title | Proves | Depends on | Status |
| --- | --- | --- | --- | --- |
| ST-1 | Offline edits | SYNC-1 | — | |
| ST-2 | Conflicts | SYNC-2 | ST-1 | |
""",
    "tests/test_sync.py": "def test_SYNC_1_1_kept():\n    pass\n",
    "build/test-results/junit.xml": (
        '<testsuite><testcase classname="tests.test_sync" name="test_SYNC_1_1_kept"/></testsuite>'),
}


def junit(**cases):
    """junit(test_SYNC_1_1_x='pass', test_SYNC_2_y='fail')"""
    body = "".join(
        f'<testcase classname="t" name="{n}">' + ("<failure/>" if r == "fail" else "") + "</testcase>"
        for n, r in cases.items())
    return f"<testsuite>{body}</testsuite>"


def change(story=None, proves=None, tasks=None, plan=True, living="", body="", track=None, removes=None,
           examples=None):
    """Files of one Spec Kit folder; tasks is a list of booleans (checked) or None for no tasks.md."""
    head = ["---"]
    if story:
        head.append(f"story: {story}")
    if proves is not None:
        head.append(f"proves: [{', '.join(proves)}]")
    if removes:
        head.append(f"removes: [{', '.join(removes)}]")
    if track:
        head.append(f"track: {track}")
    head.append("---")
    spec = "\n".join(head) + f"\n\n# Feature Specification\n\n{body}\n\n## Living doc changes\n\n{living}\n"
    files = {"spec.md": spec}
    if plan:
        files["plan.md"] = "# Plan\n\n## Expected living-doc impact\n\n- none\n"
    if tasks is not None:
        ids = " ".join(f"test_{i.replace('-', '_').replace('.', '_')}" for i in (examples or proves or []))
        lines = [f"- [{'x' if t else ' '}] T00{n} task" for n, t in enumerate(tasks, 1)]
        lines.append(f"- [{'x' if all(tasks) else ' '}] T090 Write failing tests {ids}")
        lines.append(f"- [{'x' if all(tasks) else ' '}] T091 Update the living docs")
        files["tasks.md"] = "\n".join(lines) + "\n"
    return files


class Proj:
    def __init__(self, root: Path):
        self.root = root

    def write(self, files):
        for rel, text in files.items():
            p = self.root / rel
            if text is None:
                if p.exists():
                    p.unlink()
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        return self

    def add_change(self, folder, files):
        return self.write({f"specs/{folder}/{k}": v for k, v in files.items()})

    def load(self, evidence=True):
        p = stopgap.Project(self.root, evidence=evidence)
        p.load()
        p.check()
        return p

    def findings(self, rule=None):
        return [f for f in self.load().findings if rule is None or f.rule == rule]

    def run(self, *args, script=None):
        cmd = ["bash", str(script)] if script else [sys.executable, str(STOPGAP)]
        return subprocess.run(cmd + list(args), cwd=self.root, capture_output=True, text=True)

    def next(self):
        r = self.run("next", "--json")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)


@pytest.fixture
def proj(tmp_path):
    return Proj(tmp_path).write(BASE)


@pytest.fixture
def empty(tmp_path):
    return Proj(tmp_path)
