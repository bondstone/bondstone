---
id: CAP-library
type: capability:Capability
title: Library
status: active
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

### REQ-LIB-006: Record decisions with the adr pack

The `adr` pack SHALL define `adr:Decision` at `docs/adr/ADR-NNN-<slug>.md` with the sections
Context, Decision and Consequences, a lifecycle from `proposed` to `accepted`, `rejected`,
`deprecated` or `superseded`, and an owner. An accepted decision MUST NOT be edited except
for its status and owner, and is replaced with `bondstone supersede`.

#### Scenario: Editing an accepted decision

- Given an accepted decision whose Decision section changed since the base commit
- When `bondstone check --base` runs
- Then `bondstone/immutable` is an error that suggests `bondstone supersede`

### REQ-LIB-007: Keep living capability specs with the capability pack

The `capability` pack SHALL define `capability:Capability` at `docs/capabilities/<slug>.md`
with Requirement items `### REQ-<CODE>-NNN: title`, each with SHALL or MUST wording and at
least one scenario. An active requirement MUST be tagged in code; a planned one need not be.

#### Scenario: A requirement without a scenario

- Given a requirement heading followed by text but no `#### Scenario:`
- When `bondstone check` runs
- Then `capability/requirement-has-scenario` is an error

### REQ-LIB-008: Tie capabilities to decisions

The bridge `adr-capability` SHALL let a capability name the decisions it is `constrained_by`.
A capability MUST point only at proposed or accepted decisions, and an accepted decision that
constrains no capability is warned about.

#### Scenario: A superseded decision

- Given a capability with `constrained_by: [ADR-002]` and ADR-002 in status `superseded`
- When `bondstone check` runs
- Then `adr-capability/constrained-by-live-decision` is an error

### REQ-LIB-009: Start a repository with the starter preset

The preset `starter` SHALL bring `adr`, `capability` and `adr-capability`, and a diff rule
that a change to code tagged for a requirement updates that requirement's capability in the
same change, exemptible with a `Spec-Impact` commit trailer.

#### Scenario: Code changed without its spec

- Given a profile that extends `starter`, and a change inside code tagged `REQ-AA-001`
- When `bondstone check --base` runs and CAP-a did not change
- Then `starter/code-change-updates-living-spec` is an error
