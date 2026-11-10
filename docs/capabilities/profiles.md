---
id: CAP-profiles
type: capability:Capability
title: Profiles, packs and bridges
status: active
owner: dworek
code: PRF
constrained_by: [ADR-002, ADR-003, ADR-012]
---

## Purpose

A repository says in `.bondstone/profile.yaml` which packs and bridges it uses and how strict
their rules are. Bondstone turns that into one effective configuration, and refuses to check
anything when the configuration is inconsistent.

## Requirements

### REQ-PRF-001: Validate manifests against their schemas

Bondstone SHALL validate `profile.yaml`, every `pack.yaml` and every `bridge.yaml` against the
JSON Schema it ships for that kind, and report each violation with the file, the location
inside it and what was expected.

#### Scenario: Unknown key in a pack

- Given a `pack.yaml` with the key `typs`
- When the configuration is loaded
- Then a `bondstone/profile` error names `typs` and lists the allowed keys

### REQ-PRF-002: Reject a YAML boolean used as a severity

Bondstone SHALL reject a YAML boolean where a severity is expected, with a message that names
the severity to write instead.

#### Scenario: An override written as off

- Given the override `adr/alternatives-considered: off`, which YAML reads as `false`
- When the configuration is loaded
- Then the error says the value is the YAML boolean false and to write `ignore`

### REQ-PRF-003: Find the repository root

Bondstone SHALL use the folder given with `--root`, and without it the nearest folder at or
above the current one that contains `.bondstone/profile.yaml`.

#### Scenario: Run from a subfolder

- Given a repository with a profile, and the current folder `docs/adr`
- When `bondstone check` runs without `--root`
- Then the repository root is checked

### REQ-PRF-004: Resolve packs and bridges from local sources

Bondstone SHALL find each pack and bridge the profile names in the folders listed under
`sources` (default `.bondstone/packs`) and choose the highest version that satisfies the
requested range. `adr@1` and `^1` mean any 1.x; comparators such as `>=1.0` are combined with
AND. A component that is missing, or present only in other versions, MUST be a configuration
error. The engine ships no packs of its own.

#### Scenario: Version out of range

- Given a profile that names `capability@2` and a source folder with `capability` 1.0.0
- When the configuration is loaded
- Then a `bondstone/profile` error names the version that was found

### REQ-PRF-005: Check what a bridge requires

Bondstone SHALL report a bridge whose `requires` names a pack that the profile does not use,
or uses in a version outside the required range.

#### Scenario: Bridge without its pack

- Given a profile with the bridge `adr-capability` and without the pack `capability`
- When the configuration is loaded
- Then a `bondstone/profile` error says the bridge requires `capability`

### REQ-PRF-006: Check what a schema cannot express

Bondstone SHALL report references that lead nowhere: a link or a role that names an unknown
type, a rule that selects an unknown type, link or role, a view that walks an unknown link or
writes outside the repository, a trait that names a status its lifecycle does not declare, and
a malformed id or path template.

#### Scenario: Rule on an unknown type

- Given a rule with `when: {type: Decison}`
- When the configuration is loaded
- Then a `bondstone/profile` error names the unknown type and the rule

### REQ-PRF-007: Apply overrides and respect locked rules

Bondstone SHALL give every rule the severity the profile's `overrides` set for its qualified
id, and its default otherwise. A rule overridden to `ignore` reports nothing. An override for
an unknown rule id, and an override that lowers the severity of a `locked` rule, MUST be
configuration errors.

#### Scenario: Loosening a locked rule

- Given a rule with `locked: true` and severity `error`, and an override that sets it to `warn`
- When the configuration is loaded
- Then a `bondstone/profile` error says the rule is locked

### REQ-PRF-008: Apply waivers that have a reason and an expiry date

Bondstone SHALL drop the diagnostics of a rule that a waiver names, for the waiver's node or
for every node when it names none, up to and including its `expires` date. A waiver without
`rule`, `reason` or `expires`, for an unknown rule or for a locked rule MUST be reported as
`bondstone/waiver-invalid`, an expired one as `bondstone/waiver-expired`, and one that matches
nothing as `bondstone/waiver-unused`.

#### Scenario: Expired waiver

- Given a waiver whose `expires` date was yesterday
- When `bondstone check` runs
- Then the waived diagnostic is reported again, together with `bondstone/waiver-expired`

### REQ-PRF-009: Warn about packs that no bridge connects

Bondstone SHALL warn with `bondstone/unbridged-packs` when the profile's packs form groups
that no bridge connects.

#### Scenario: Two packs, no bridge

- Given a profile with the packs `adr` and `capability` and no bridges
- When `bondstone profile check` runs
- Then it warns that the two packs are not connected

### REQ-PRF-010: Stop on a configuration error

Bondstone SHALL read no documents when the configuration has an error. It MUST print the
errors as `bondstone/profile` diagnostics, which no override or waiver can silence.

#### Scenario: Check with a broken profile

- Given a profile that names a pack that does not exist
- When `bondstone check` runs
- Then only configuration errors are printed and the exit code is 2
