"""The baseline commit: the point from which a repository's documents count as adopted.

Against a base from before the adoption every document looks new, so lifecycle and
immutability checks would misfire. `bondstone baseline` records a commit in the profile; a
document that is absent at the base but present at the baseline is compared with its baseline
version."""

from __future__ import annotations

import re
from pathlib import Path

from .git import Repository
from .model import PROFILE_PATH, EnvironmentProblem

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
