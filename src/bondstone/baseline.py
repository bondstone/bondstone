"""The baseline commit: the point from which a repository's documents count as adopted.

Against a base from before the adoption every document looks new, so lifecycle and
immutability checks would misfire. `bondstone baseline` records a commit in the profile; a
document that is absent at the base but present at the baseline is compared with its baseline
version."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .git import Repository
from .graph import build_graph
from .known import KNOWN_PATH, Entry, fingerprint
from .known import write as write_known
from .model import ERROR, PROFILE_PATH, WARN, EnvironmentProblem
from .rules import run_check

_BASELINE_LINE = re.compile(r"^baseline:.*$", re.M)
_FORMAT_LINE = re.compile(r"^bondstone:.*$", re.M)


# bondstone: REQ-DIF-010
def record_baseline(root: Path, repo: Repository, ref: str = "HEAD") -> str:
    """Write the commit `ref` names into the profile as `baseline`; returns the commit id.

    Only that one line of the profile changes, so comments and layout stay as they are."""
    commit = repo.commit(ref)
    if commit is None:
        raise EnvironmentProblem(f"baseline: '{ref}' is not a commit in this repository")
    path = root / PROFILE_PATH
    text = path.read_text(encoding="utf-8")
    line = f"baseline: '{commit}'"  # quoted: an id made of digits only would be read as a number
    if _BASELINE_LINE.search(text):
        text = _BASELINE_LINE.sub(line, text, count=1)
    elif _FORMAT_LINE.search(text):
        text = _FORMAT_LINE.sub(lambda match: f"{match.group(0)}\n{line}", text, count=1)
    else:
        text = f"{line}\n{text}"
    path.write_text(text, encoding="utf-8")
    return commit


# --------------------------------------------------------------------------- known violations


@dataclass
class Recorded:
    """What `bondstone baseline --known` did."""

    entries: int  # entries in the file now
    added: int = 0
    removed: int = 0
    refused: int = 0  # violations of rules that do not accept known violations
    deleted: bool = False  # the last entry went, and the file with it


# bondstone: REQ-KNV-001, REQ-KNV-005
def record_known(cfg: Config, prune: bool = False, today: dt.date | None = None) -> Recorded:
    """Write the repository's current violations to `known.json`, or with `prune` only drop what is fixed.

    Recording keeps the entries that still match and adds every other error and warning whose
    rule accepts known violations. Pruning never adds an entry. Checks that need a base commit
    are not run: a known violation is a state of the documents, not a change."""
    today = today or dt.date.today()
    diagnostics = run_check(cfg, build_graph(cfg), today=today)
    before = set(cfg.known.entries)
    matching = {fingerprint(d) for d in diagnostics if d.known}
    fresh: set[Entry] = set()
    refused = 0
    for diag in diagnostics:
        if diag.known or diag.severity not in (ERROR, WARN):
            continue
        if cfg.accepts_known(diag.rule):
            fresh.add(fingerprint(diag))
        elif diag.rule not in ("bondstone/known-stale", "bondstone/known-grew"):
            refused += 1
    entries = matching if prune else matching | fresh
    result = Recorded(len(entries), len(entries - before), len(before - entries), refused)
    path = cfg.root / KNOWN_PATH
    if entries:
        write_known(cfg.root, sorted(entries), cfg.known.created or today.isoformat())
    elif path.is_file():
        path.unlink()
        result.deleted = True
    return result
