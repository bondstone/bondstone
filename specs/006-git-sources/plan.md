# Implementation Plan: Git sources

**Branch**: `v1-phase-5-git-sources` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-git-sources/spec.md`

## Summary

`sources.py` knows the syntax, the lock file, the cache and the two git operations (fetch a
ref or a commit, write a folder of a commit into the cache). The resolver reads a git source
through the lock and the cache and lists what it could not read. `update.py` fetches what is
listed, round by round, because a preset may name further sources.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: git on the command line (as for `--base`); PyYAML for the lock

**Storage**: `.bondstone/bondstone.lock` in the repository; a cache in the user's cache folder

**Testing**: pytest; the remote is a repository in a temporary folder that git reads through `url.<base>.insteadOf`

**Target Platform**: any platform with Python and git

**Project Type**: cli with a companion library package

**Performance Goals**: `check` hashes the files of the pinned sources, which are a few YAML and Markdown files

**Constraints**: only `update` uses the network (ADR-011); `check` is deterministic; no password prompts

**Scale/Scope**: two modules, one command, changes to the resolver

## Constitution Check

ADR-011 decides git sources with a lock file; ADR-004 decides that presets carry shared
standards, which is why a preset may name sources.

## Project Structure

### Documentation (this feature)

```text
specs/006-git-sources/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
src/bondstone/
├── sources.py                 # syntax, lock, cache, fetch
├── update.py                  # `bondstone update`
├── resolve.py                 # git sources between folders and installed packages
├── schemas/lock.schema.json
├── schemas/preset.schema.json, profile.schema.json
├── cli.py                     # the command
└── agent.py                   # a note about the lock in the instructions

docs/cli/update.md
tests/test_sources.py
```

**Structure Decision**: The resolver must not fetch, so everything that runs git for a remote
is in `sources.py` and only `update.py` calls it.

## Complexity Tracking

| Choice | Why | Alternative rejected |
| --- | --- | --- |
| The lock covers git sources only | Installed packages are pinned by the Python lock file | Hashing installed packages too |
| The lock is YAML | Like every other file in `.bondstone/` that people read in a diff | JSON or TOML |
| A source not in the lock is exit code 2, a cache that is behind is exit code 3 | The first is wrong in the repository, the second on this machine | One code for both |
| One hash per component, over paths and contents | The design asks for a hash per component | One hash per source |
| Local folders always come before git sources | A repository overrides a shared pack with its own copy | The order as written |
| `update NAME` moves whole sources | A commit pins a source, not a component | Pinning components one by one |
| HTTPS URLs, other transports through git's `insteadOf` | No transport options to invent; this is also how the tests get a local remote | A `url` key per source |
| A fetch of a pinned commit falls back to fetching the ref | Not every server serves single commits | Failing on such servers |
