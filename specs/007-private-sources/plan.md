# Implementation Plan: Private git sources

**Branch**: `v1-private-sources` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-private-sources/spec.md`

## Summary

Authentication already works through git. This change makes failures readable and keeps
credentials out of messages: git's reason line is taken instead of its last line of advice,
user names and passwords are removed from it, and a repository git cannot read is explained.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: git on the command line

**Storage**: none new

**Testing**: pytest with the local remote of `tests/test_sources.py`; a manual run against a private GitHub repository

**Target Platform**: any platform with Python and git

**Project Type**: cli with a companion library package

**Performance Goals**: not applicable

**Constraints**: no credentials stored or handled by bondstone

**Scale/Scope**: three functions in `src/bondstone/sources.py`, documentation

## Constitution Check

ADR-011 decides git sources; authentication stays with git.

## Project Structure

### Documentation (this feature)

```text
specs/007-private-sources/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
src/bondstone/sources.py   # scrub, explain, the reason line of git's error
tests/test_sources.py
docs/cli/update.md, README.md
```

**Structure Decision**: Everything stays in `sources.py`, the only module that runs git against a remote.

## Complexity Tracking

| Choice | Why | Alternative rejected |
| --- | --- | --- |
| No credential option in bondstone | Git's helpers and `insteadOf` already cover machines and CI | A token setting in the profile or the environment |
| Credentials are removed from messages although git redacts them today | Older git versions and other hosts may not | Relying on git |
| The hint names both causes | A host answers the same for a missing and a private repository | Guessing one |
