---
# bondstone reads this block. Keep it at the very top of the file.
id: "006-git-sources"   # the name of this feature's folder under specs/
type: speckit:Feature
title: "Git sources"
modifies: [CAP-profiles, CAP-agent-guidance]     # capabilities this feature changes
delivers: [REQ-PRF-017, REQ-PRF-018, REQ-PRF-019, REQ-PRF-020]     # requirements this feature implements
decided_by: [ADR-011, ADR-004]   # decisions this feature rests on
---

# Feature Specification: Git sources

**Feature Branch**: `v1-phase-5-git-sources`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Take packs from git sources pinned in a lock file"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Share packs between repositories (Priority: P1)

An organisation keeps its packs, bridges and presets in one git repository. A team names that
repository in its profile, runs `bondstone update` once, and commits the lock.

**Why this priority**: Copies in each repository drift; presets are of little use without a
way to fetch them.

**Independent Test**: Name a git source, run `bondstone update`, then `bondstone check`.

**Acceptance Scenarios**:

1. **Given** a profile with `sources: [host/org/repo//path@ref]`, **When** `bondstone update` runs, **Then** the source is in the cache and `.bondstone/bondstone.lock` has its commit and a hash of each component.
2. **Given** that lock, **When** `bondstone check` runs, **Then** the packs of the source are used.
3. **Given** a preset from a git source that names another git source, **When** `bondstone update` runs, **Then** both are pinned.

---

### User Story 2 - The check stays deterministic (Priority: P1)

`check` gives the same result on every machine and never waits for a network: it reads the
lock and the cache, nothing else.

**Why this priority**: A gate that depends on the state of a remote is not a gate.

**Independent Test**: Delete the remote after `update` and run `check`; delete the cache and
run it again.

**Acceptance Scenarios**:

1. **Given** a pinned source whose remote is gone, **When** `bondstone check` runs, **Then** it passes.
2. **Given** an empty cache, **When** `bondstone check` runs, **Then** it exits with 3 and says to run `bondstone update --locked`.
3. **Given** a source the lock does not pin, **When** `bondstone check` runs, **Then** it exits with 2 and says to run `bondstone update`.
4. **Given** a branch or a tag that moved, **When** `bondstone update --locked` runs, **Then** the pinned commit is fetched and the lock is unchanged.

---

### User Story 3 - Move one pin (Priority: P2)

A maintainer takes the new version of one pack without moving everything else.

**Why this priority**: A convenience on top of the first two stories.

**Independent Test**: Two sources on branches, both with new commits; run `bondstone update NAME`.

**Acceptance Scenarios**:

1. **Given** two pinned sources, **When** `bondstone update architecture` runs, **Then** only the source that holds `architecture` gets a new commit.

### Edge Cases

- A source's folder may be one component or hold one per subfolder.
- A profile that names only git sources keeps the default folder `.bondstone/packs`.
- Local folders win over git sources, and git sources over installed packages.
- Cached files that were changed are noticed by their hash and replaced by `update --locked`.
- Symbolic links in a source are written as plain files, so a source cannot point outside its folder.
- A preset may name git sources only, never folders.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Profiles and presets MUST accept git sources (REQ-PRF-017).
- **FR-002**: The lock MUST pin a commit per source and a hash per component (REQ-PRF-018).
- **FR-003**: Every command except `update` MUST work from the lock and the cache without the network (REQ-PRF-019).
- **FR-004**: `bondstone update` MUST fetch and pin; `--locked` MUST fetch what is pinned and change nothing (REQ-PRF-020).

### Key Entities

- **Git source**: repository, folder, ref.
- **Lock entry**: source, commit, components with their hashes.
- **Cache**: the folder of each source at its pinned commit, outside the repository.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After `update`, `check` passes with the remote removed.
- **SC-002**: A CI job on a fresh machine needs one extra step, `bondstone update --locked`.
- **SC-003**: The tests fetch from a repository in a temporary folder and never use the network.

## Assumptions

- Components of installed packages are not in the lock: the Python lock file pins those.
- Sources are fetched over HTTPS; other transports are configured in git.
