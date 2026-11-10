from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

from bondstone.checks import run_check
from bondstone.loader import load_config

REPO = Path(__file__).resolve().parents[1]
LIBRARY = REPO / "src" / "bondstone" / "library"
EXAMPLE = REPO / "examples" / "habit-tracker"


class Project:
    def __init__(self, root: Path):
        self.root = root

    def profile(self, **data) -> "Project":
        data.setdefault("bondstone", 0.1)
        (self.root / ".bondstone").mkdir(parents=True, exist_ok=True)
        (self.root / ".bondstone/profile.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
        return self

    def write(self, path: str, text: str) -> "Project":
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text).lstrip("\n"))
        return self

    def check(self, base: str | None = None):
        return run_check(load_config(self.root), base=base)

    def rules(self, base: str | None = None, severity: str | None = None) -> list[str]:
        return sorted(d.rule for d in self.check(base) if severity is None or d.severity == severity)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              cwd=self.root, check=True, capture_output=True, text=True).stdout

    def commit(self, message: str = "c") -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)


@pytest.fixture
def project(tmp_path: Path) -> Project:
    return Project(tmp_path)


ADR_BODY = """
## Context

c

## Decision

d

## Alternatives considered

a

## Consequences

x
"""


def adr(doc_id: str, status: str, extra: str = "", body: str = ADR_BODY) -> str:
    return (f"---\nid: {doc_id}\ntitle: Decision {doc_id}\nstatus: {status}\nowner: me\n"
            f"date: 2026-01-01\n{extra}---\n{body}")
