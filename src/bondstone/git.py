"""The git layer: what changed since a base commit, files at a commit, and commit trailers.

Rules only see the `Repository` interface, so they can be tested without git. `GitRepository`
is its one implementation; it runs the `git` command and never touches the network."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .model import EnvironmentProblem

ADDED, MODIFIED, DELETED = "added", "modified", "deleted"
KINDS = (ADDED, MODIFIED, DELETED)


@dataclass(frozen=True)
class Change:
    """One changed file. A renamed file is `modified` and keeps its previous path."""

    path: str  # the current path; for a deleted file, the path it had
    kind: str  # added | modified | deleted
    old_path: str | None = None  # set when the file was renamed


@dataclass(frozen=True)
class Trailer:
    """A `Key: value` line at the end of a commit message."""

    commit: str
    key: str
    value: str


@dataclass(frozen=True)
class ChangedLines:
    """Line numbers a change touched: in the current file and in the file at the base."""

    new: frozenset[int]
    old: frozenset[int]


class Repository(Protocol):
    """What the rules need from version control."""

    def commit(self, ref: str) -> str | None:
        """The commit a ref names, or None when it is not available."""

    def merge_base(self, ref: str) -> str:
        """The commit where the current branch left `ref`."""

    def changes(self, base: str) -> list[Change]:
        """Files that differ between a commit and the working tree, untracked files included."""

    def file_at(self, commit: str, path: str) -> str | None:
        """A file's text at a commit, or None when it did not exist there."""

    def changed_lines(self, base: str, change: Change) -> ChangedLines:
        """The lines of one modified file that differ from the base."""

    def trailers(self, base: str) -> list[Trailer]:
        """Trailers of the commits made since `base`, newest commit first."""

    def author(self, commit: str) -> str | None:
        """The name of a commit's author."""


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", re.M)
_TRAILER = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*)\s*:\s*(.*)$")


# bondstone: REQ-DIF-001
class GitRepository:
    """A git work tree. Paths are relative to `root`, which may be a folder inside the repository."""

    def __init__(self, root: Path):
        self.root = root
        inside = self._run("rev-parse", "--is-inside-work-tree", check=False)
        if inside is None or inside.strip() != "true":
            raise EnvironmentProblem(f"'{root}' is not inside a git repository; `--base` and `baseline` need one")

    def _run(self, *args: str, check: bool = True) -> str | None:
        try:
            result = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace")
        except FileNotFoundError:
            raise EnvironmentProblem("the `git` command was not found") from None
        if result.returncode != 0:
            if check:
                raise EnvironmentProblem(result.stderr.strip() or f"git {' '.join(args)} failed")
            return None
        return result.stdout

    def commit(self, ref: str) -> str | None:
        if not ref or ref.startswith("-"):
            return None
        out = self._run("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
        return out.strip() if out else None

    # bondstone: REQ-DIF-002
    def merge_base(self, ref: str) -> str:
        if self.commit(ref) is None:
            raise EnvironmentProblem(
                f"--base: '{ref}' is not a commit in this repository; fetch it, e.g. `git fetch origin`")
        if self.commit("HEAD") is None:
            raise EnvironmentProblem("--base: the repository has no commits yet")
        out = self._run("merge-base", ref, "HEAD", check=False)
        if not out:
            raise EnvironmentProblem(
                f"--base: '{ref}' and HEAD have no common commit in this clone; "
                "fetch the full history, e.g. `git fetch --unshallow`")
        return out.strip()

    # bondstone: REQ-DIF-003
    def changes(self, base: str) -> list[Change]:
        out = self._run("diff", "--name-status", "-M", "--relative", "-z", base) or ""
        parts = out.split("\0")
        found: dict[str, Change] = {}
        index = 0
        while index < len(parts) and parts[index]:
            status = parts[index]
            if status[0] in "RC":
                old, new = parts[index + 1], parts[index + 2]
                index += 3
                found[new] = Change(new, MODIFIED, old) if status[0] == "R" else Change(new, ADDED)
            else:
                path = parts[index + 1]
                index += 2
                kind = {"A": ADDED, "D": DELETED}.get(status[0], MODIFIED)
                found[path] = Change(path, kind)
        untracked = self._run("ls-files", "--others", "--exclude-standard", "-z") or ""
        for path in untracked.split("\0"):
            if path:
                # a file deleted at the base's path and written again is a modification
                found[path] = Change(path, MODIFIED if self.file_at(base, path) is not None else ADDED)
        return sorted(found.values(), key=lambda change: change.path)

    def file_at(self, commit: str, path: str) -> str | None:
        return self._run("show", f"{commit}:./{path}", check=False)

    # bondstone: REQ-DIF-009
    def changed_lines(self, base: str, change: Change) -> ChangedLines:
        paths = [change.old_path, change.path] if change.old_path else [change.path]
        diff = self._run("diff", "-U0", "-M", "--relative", base, "--", *paths) or ""
        new: set[int] = set()
        old: set[int] = set()
        for match in _HUNK.finditer(diff):
            old_start, old_count = int(match.group(1)), int(match.group(2) or 1)
            new_start, new_count = int(match.group(3)), int(match.group(4) or 1)
            # a hunk that only removes lines has no lines in the current file; the removed
            # lines are found in the file at the base
            old.update(range(old_start, old_start + old_count))
            new.update(range(new_start, new_start + new_count))
        return ChangedLines(frozenset(new), frozenset(old))

    # bondstone: REQ-DIF-011
    def trailers(self, base: str) -> list[Trailer]:
        out = self._run("log", "--format=%H%x1f%(trailers:only=true,unfold=true)%x1e", f"{base}..HEAD") or ""
        found = []
        for record in out.split("\x1e"):
            commit, _, block = record.strip().partition("\x1f")
            for line in block.splitlines():
                match = _TRAILER.match(line.strip())
                if commit and match:
                    found.append(Trailer(commit, match.group(1), match.group(2).strip()))
        return found

    def author(self, commit: str) -> str | None:
        out = self._run("log", "-1", "--format=%an", commit, check=False)
        return out.strip() or None if out else None
