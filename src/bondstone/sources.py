"""Git sources of packs: their syntax, the lock file that pins them and the cache that holds them.

A git source is written `host/org/repo//path@ref`. `bondstone update` resolves the ref to a
commit, puts the files of that commit into a cache outside the repository, and records the
commit and a SHA-256 of every component in `.bondstone/bondstone.lock`. Everything else reads
the lock and the cache only, so a check never touches the network."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .manifest import MANIFEST_NAMES, ManifestError, load_yaml, validate
from .model import EnvironmentProblem

LOCK_PATH = ".bondstone/bondstone.lock"
LOCK_FORMAT = 1
CACHE_ENV = "BONDSTONE_CACHE"
EXAMPLE = "github.com/acme/bondstone-packs//packs@v1.2.0"

_GIT_SOURCE = re.compile(
    r"(?P<repo>[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z0-9-]+(?:/[A-Za-z0-9._-]+)+?)"
    r"(?://(?P<path>[A-Za-z0-9._/-]*))?"
    r"@(?P<ref>[A-Za-z0-9][A-Za-z0-9._/+-]*)")  # never starts with `-`: it is passed to git


# bondstone: REQ-PRF-017
@dataclass(frozen=True)
class GitSource:
    """One git source as a profile or a preset writes it."""

    spec: str  # the whole text, which is also its key in the lock
    repo: str  # host/org/repo
    path: str  # folder inside the repository; empty for its root
    ref: str  # a tag, a branch or a commit

    @property
    def url(self) -> str:
        return f"https://{self.repo}"


def parse_git_source(text: str) -> GitSource | None:
    """A git source, or None when the text is not one (it is then a local folder)."""
    match = _GIT_SOURCE.fullmatch(text.strip())
    if match is None:
        return None
    path = (match.group("path") or "").strip("/")
    if any(part in ("", ".", "..") for part in path.split("/")) and path:
        return None
    return GitSource(text.strip(), match.group("repo"), path, match.group("ref"))


def looks_remote(text: str) -> bool:
    """Whether an entry of `sources` was meant as a git source: it has `//` or `@`."""
    return "//" in text or "@" in text


# --------------------------------------------------------------------------- components in a folder


def component_folders(folder: Path) -> list[tuple[str, Path]]:
    """(kind, folder) of the components a source folder holds.

    The folder is one component when it has a manifest itself, and otherwise one component
    per subfolder with a manifest."""
    own = [(kind, folder) for kind, name in MANIFEST_NAMES.items() if (folder / name).is_file()]
    if own:
        return own
    return [(kind, manifest.parent) for kind, name in MANIFEST_NAMES.items()
            for manifest in sorted(folder.glob(f"*/{name}"))]


# bondstone: REQ-PRF-018
def hash_folder(folder: Path) -> str:
    """SHA-256 over the relative path and the bytes of every file in a folder, in a fixed order."""
    digest = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        digest.update(path.relative_to(folder).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def describe_components(folder: Path) -> list[dict[str, str]]:
    """What the lock records for each component of a source folder: kind, id, version and hash."""
    found = []
    for kind, directory in component_folders(folder):
        try:
            data = load_yaml(directory / MANIFEST_NAMES[kind])
        except ManifestError:
            data = None
        data = data if isinstance(data, dict) else {}
        cid = data.get("id") if isinstance(data.get("id"), str) else directory.name
        found.append({"kind": kind, "id": cid, "version": str(data.get("version", "")),
                      "sha256": hash_folder(directory)})
    return sorted(found, key=lambda item: (item["kind"], item["id"]))


# --------------------------------------------------------------------------- the lock file


@dataclass
class Locked:
    """What the lock pins for one source."""

    source: str
    commit: str
    components: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "commit": self.commit, "components": self.components}


_HEADER = ("# Written by `bondstone update`; do not edit. It pins the git sources that the profile and\n"
           "# its presets name: the commit of each, and a SHA-256 of the files of each component.\n")


# bondstone: REQ-PRF-018
def read_lock(root: Path) -> tuple[dict[str, Locked], list[str]]:
    """The lock by source, and what is wrong with the file; empty when there is none."""
    path = root / LOCK_PATH
    if not path.is_file():
        return {}, []
    try:
        data = load_yaml(path)
    except ManifestError as exc:
        return {}, [str(exc)]
    problems = validate("lock", data if data is not None else {})
    if problems:
        return {}, problems
    return {item["source"]: Locked(item["source"], item["commit"], list(item.get("components") or []))
            for item in data.get("sources") or []}, []


def render_lock(entries: list[Locked]) -> str:
    data = {"bondstone": LOCK_FORMAT, "sources": [entry.to_dict() for entry in sorted(entries, key=lambda e: e.source)]}
    return _HEADER + yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True, width=200)


def write_lock(root: Path, entries: list[Locked]) -> bool:
    """Write the lock, or delete it when nothing is pinned; returns whether the file changed."""
    path = root / LOCK_PATH
    before = path.read_text(encoding="utf-8") if path.is_file() else None
    if not entries:
        if before is not None:
            path.unlink()
        return before is not None
    text = render_lock(entries)
    if text == before:
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


# --------------------------------------------------------------------------- the cache


def cache_dir() -> Path:
    """Where fetched sources are kept: `$BONDSTONE_CACHE`, else the user's cache folder."""
    if os.environ.get(CACHE_ENV):
        return Path(os.environ[CACHE_ENV])
    base = os.environ.get("XDG_CACHE_HOME")
    return (Path(base) if base else Path.home() / ".cache") / "bondstone"


def tree_dir(source: GitSource, commit: str) -> Path:
    """The folder that holds the files of one commit of a source's repository."""
    return cache_dir() / "trees" / source.repo / commit


def source_dir(source: GitSource, commit: str) -> Path:
    """The folder of a source inside the cache: what a local `sources` folder is for local packs."""
    return tree_dir(source, commit) / source.path if source.path else tree_dir(source, commit)


# bondstone: REQ-PRF-019
def verify(source: GitSource, locked: Locked) -> str | None:
    """Why the cache does not hold what the lock pins for a source, or None when it does."""
    folder = source_dir(source, locked.commit)
    if not folder.is_dir():
        return f"commit {locked.commit[:12]} is not in the cache ({cache_dir()})"
    found = describe_components(folder)
    if found != locked.components:
        changed = sorted({f"{item['kind']} {item['id']}" for item in found + locked.components
                          if item not in found or item not in locked.components})
        return (f"the cached files of commit {locked.commit[:12]} do not match the lock "
                f"({', '.join(changed)})")
    return None


# --------------------------------------------------------------------------- git


def _git(*args: str, cwd: Path | None = None, check: bool = True) -> str | None:
    """Run git for a fetch. It never asks for a password: a prompt would hang a CI job."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", env=env)
    except FileNotFoundError:
        raise EnvironmentProblem("the `git` command was not found") from None
    if result.returncode != 0:
        if check:
            detail = (result.stderr.strip().splitlines() or [f"git {args[0]} failed"])[-1]
            raise EnvironmentProblem(detail)
        return None
    return result.stdout


def _mirror(source: GitSource) -> Path:
    """A bare repository in the cache that fetches of one remote repository go into."""
    path = cache_dir() / "repos" / f"{source.repo}.git"
    if not (path / "HEAD").is_file():
        path.mkdir(parents=True, exist_ok=True)
        _git("init", "--quiet", "--bare", str(path))
    return path


# bondstone: REQ-PRF-020
def fetch(source: GitSource, commit: str | None = None) -> str:
    """Bring a source into the cache and return its commit.

    Without `commit` the source's ref is resolved at the remote. With one, exactly that commit
    is fetched; when the remote does not serve single commits, the ref is fetched instead and
    must contain it."""
    mirror = _mirror(source)
    if commit is None:
        if _git("fetch", "--quiet", "--depth", "1", source.url, source.ref, cwd=mirror, check=False) is None:
            # a second try without the shortcut gives git's own error message
            try:
                _git("fetch", "--quiet", source.url, source.ref, cwd=mirror)
            except EnvironmentProblem as exc:
                raise EnvironmentProblem(f"cannot fetch '{source.ref}' from {source.url}: {exc}") from None
        commit = (_git("rev-parse", "--verify", "FETCH_HEAD^{commit}", cwd=mirror) or "").strip()
    elif _git("cat-file", "-e", f"{commit}^{{commit}}", cwd=mirror, check=False) is None:
        if _git("fetch", "--quiet", "--depth", "1", source.url, commit, cwd=mirror, check=False) is None:
            _git("fetch", "--quiet", source.url, source.ref, cwd=mirror, check=False)
        if _git("cat-file", "-e", f"{commit}^{{commit}}", cwd=mirror, check=False) is None:
            raise EnvironmentProblem(
                f"cannot fetch commit {commit[:12]} of {source.url}: the remote does not have it at '{source.ref}'")
    target = tree_dir(source, commit)
    if source_dir(source, commit).is_dir():
        shutil.rmtree(source_dir(source, commit))  # a fresh copy: nothing left over from an earlier fetch
    target.mkdir(parents=True, exist_ok=True)
    listed = _git("ls-tree", "-d", "--name-only", commit, "--", source.path or ".", cwd=mirror) or ""
    if source.path and not listed.strip():
        raise EnvironmentProblem(f"{source.spec}: commit {commit[:12]} has no folder '{source.path}'")
    # symbolic links are written as plain files, so a source cannot point outside its folder
    _git("-c", "core.symlinks=false", f"--work-tree={target}", "checkout", "--quiet", "--force", commit, "--",
         source.path or ".", cwd=mirror)
    return commit
