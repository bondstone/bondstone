---
id: CAP-library
type: capability:Capability
title: Library
status: draft
owner: Adam Dworzyński
code: LIB
depends_on: [CAP-profiles, CAP-pack-tooling, CAP-spec-kit-adapter]
constrained_by: [ADR-012]
---

## Purpose

`bondstone-library` is the set of packs, bridges and presets that bondstone documents itself
with, offered to every repository that installs the package. Nothing in it is special to the
engine: each component is a folder with a manifest and fixtures, as a team's own would be.
The Spec Kit components are described in [CAP-spec-kit-adapter](spec-kit-adapter.md).

## Requirements

### REQ-LIB-001: Document commands with the cli pack

The `cli` pack SHALL define `cli:Command`, one document per command at `docs/cli/<name>.md`
with a synopsis and the sections Options, Exit codes and Examples. A stable command MUST be
tagged in code, and a stable command with JSON output MUST document its shape.

#### Scenario: A stable command without a tag

- Given a `cli:Command` in status `stable` whose id appears in no code tag
- When `bondstone check` runs
- Then `cli/stable-command-is-implemented` is an error

### REQ-LIB-002: Tie commands to capabilities

The bridge `cli-capability` SHALL let a command name the capabilities it `implements`. A
stable command MUST implement at least one capability, and only active ones.

#### Scenario: A stable command on a draft capability

- Given a stable command with `implements: [CAP-a]` and CAP-a in status `draft`
- When `bondstone check` runs
- Then `cli-capability/stable-command-on-active-capability` is an error

### REQ-LIB-003: Record releases and generate the changelog

The `release` pack SHALL define `release:Release` at `docs/releases/v<version>.md` and
generate `CHANGELOG.md` from the release documents. A released version MUST have a date and
can no longer be edited.

#### Scenario: Released without a date

- Given a release in status `released` without `date`
- When `bondstone check` runs
- Then `release/released-has-date` is an error

### REQ-LIB-004: Tie releases to features

The bridge `release-speckit` SHALL let a release name the features it `includes`. A released
version MUST include only implemented features, and an implemented feature that no release
includes is warned about.

#### Scenario: Released with an open feature

- Given a released version that includes a feature with an unticked task
- When `bondstone check` runs
- Then `release-speckit/release-includes-only-implemented` is an error

### REQ-LIB-005: Ship every component with fixtures

Every pack and bridge of the library SHALL have a fixture that passes without diagnostics and
one that breaks its rules, and every preset a fixture that passes. The library's tests MUST
run them all.

#### Scenario: A new pack without an invalid fixture

- Given a pack folder in the library with only `fixtures/valid`
- When the library's tests run
- Then they fail and name the pack
