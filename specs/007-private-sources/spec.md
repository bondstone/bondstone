---
# bondstone reads this block. Keep it at the very top of the file.
id: "007-private-sources"   # the name of this feature's folder under specs/
type: speckit:Feature
title: "Private git sources"
modifies: [CAP-profiles]     # capabilities this feature changes
delivers: [REQ-PRF-020]     # requirements this feature implements
decided_by: [ADR-011]   # decisions this feature rests on
---

# Feature Specification: Private git sources

**Feature Branch**: `v1-private-sources`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Explain unreadable git sources and keep credentials out of messages"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Use packs from a private repository (Priority: P1)

A team keeps its packs in a private repository. On a laptop git authenticates with a
credential helper; in CI with a token. Bondstone uses whatever git has.

**Why this priority**: Most organisations keep shared standards private.

**Independent Test**: Run `bondstone update` against a private repository with and without credentials.

**Acceptance Scenarios**:

1. **Given** a private source and a credential helper, **When** `bondstone update` runs, **Then** the source is pinned and `check` passes.
2. **Given** a private source and no credentials, **When** `bondstone update` runs, **Then** it exits with 3 at once and says the repository does not exist or git has no credentials for it.
3. **Given** a token in a URL rewritten with `url.<base>.insteadOf`, **When** `update`, `check` and failing fetches run, **Then** the token appears in no message, not in the lock and not in the cache.

### Edge Cases

- A host answers the same for a missing and a private repository, so the message names both.
- With `update --locked`, a pinned commit that cannot be fetched says why instead of "the remote does not have it".
- Git's advice after its error line is left out; the reason is on the line that starts with `fatal:` or `error:`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A failed fetch of an unreadable repository MUST say that it does not exist or that git has no credentials for it (REQ-PRF-020).
- **FR-002**: A user name or password in a URL MUST NOT appear in a message (REQ-PRF-020).
- **FR-003**: `docs/cli/update.md` MUST show how to set up credentials on a machine and in CI.

### Key Entities

- **Git message**: the reason line of git's standard error, without credentials.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Against a private GitHub repository, `update` works with a credential helper and fails at once without one.
- **SC-002**: A token in the URL is found in none of the outputs, the lock or the cache.

## Assumptions

- Bondstone keeps no credentials; authentication is git's job.
