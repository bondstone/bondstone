---
id: CAP-profiles
title: Profiles, packs and bridges
status: draft
owner: dworek
code: PRF
constrained_by: [ADR-002, ADR-003, ADR-004]
---

## Purpose

Load a repository's profile and resolve the packs and bridges it uses, with overrides and waivers.

## Requirements

### REQ-PRF-001: Resolve packs and bridges by version

Bondstone SHALL resolve each `id@spec` in the profile from the profile's sources first and the built-in library last, choosing the first version that satisfies the spec.

#### Scenario: Major version spec

- Given the library has adr 1.0.0
- When the profile asks for `adr@1`
- Then adr 1.0.0 is loaded

### REQ-PRF-002: Validate bridge requirements

Bondstone SHALL report an error when a bridge requires a pack that is missing from the profile or whose version does not match.

#### Scenario: Missing pack

- Given a profile with bridge adr-capability and only pack adr
- When the profile is loaded
- Then an error says the bridge requires pack capability

### REQ-PRF-003: Override severities except locked rules

Bondstone SHALL apply profile overrides (`error`, `warn`, `off`) to rule severities and MUST NOT loosen a rule marked `locked`.

#### Scenario: Loosening a locked rule

- Given a locked rule
- When the profile sets it to `off`
- Then the override is ignored and reported

### REQ-PRF-004: Waive diagnostics with a reason

Bondstone SHALL silence a rule for a node only through a waiver with a `reason`; a waiver past its `expires` date SHALL be an error and an unused waiver a warning.

#### Scenario: Expired waiver

- Given a waiver that expired yesterday
- When check runs
- Then `bondstone/waiver-expired` is reported

### REQ-PRF-005: Warn about unbridged packs

Bondstone SHALL warn when the profile's packs form groups that no bridge connects.

#### Scenario: Two unrelated packs

- Given a profile with adr and ost and no bridges
- When check runs
- Then `bondstone/unbridged-packs` is reported

### REQ-PRF-006: Assign roles only in bridges and profiles

Bondstone SHALL take role assignments from bridges and the profile only, and SHALL report packs that declare roles.

#### Scenario: Role from a bridge

- Given bridge adr-capability assigns living-spec
- When the profile is loaded
- Then capability:Capability has the living-spec role
