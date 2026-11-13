---
id: CAP-pack-tooling
type: capability:Capability
title: Pack tooling
status: draft
owner: Adam Dworzyński
code: PKT
depends_on: [CAP-profiles, CAP-rules]
constrained_by: [ADR-012]
---

## Purpose

Packs and bridges are written by many hands: the library, an organisation, one repository.
Their authors need to know that the rules fire where they should and stay silent where they
should, and users need to see what is available before they name it in a profile.

## Requirements

### REQ-PKT-001: Run the fixtures of a pack or a bridge

`bondstone pack test DIR...` SHALL run every fixture of the pack or bridge in each folder. A
fixture is a small repository in `fixtures/<case>/` with its own profile, checked like any
other repository. The component under test and the components next to it MUST be found before
any other copy with the same id. The exit code is 0 when every fixture passes and 1 otherwise;
a folder that holds no pack and no bridge is an environment error.

#### Scenario: A bridge fixture

- Given the bridge `adr-capability` in a folder next to the packs `adr` and `capability`
- When `bondstone pack test` runs on the bridge's folder
- Then its fixtures are checked with those three components

#### Scenario: A component without fixtures

- Given a pack folder without `fixtures/`
- When `bondstone pack test` runs on it
- Then the run fails and says where to add a fixture

### REQ-PKT-002: Compare a fixture with what it expects

Bondstone SHALL compare the errors and warnings of a fixture with the rule ids its
`expected.yaml` lists under `errors` and `warnings`, counting repeated rules. A fixture MUST
fail when an expected rule is not reported, when a rule is reported that is not expected,
when its configuration has an error, or when `expected.yaml` is missing or malformed. Each
failure names the rule, and for an unexpected one the place and the message.

#### Scenario: A rule that no longer fires

- Given a fixture whose `expected.yaml` lists the error `adr/alternatives-considered`
- When the check of that fixture reports no such error
- Then the fixture fails with "expected error adr/alternatives-considered was not reported"

### REQ-PKT-003: List the packs and bridges that are available

`bondstone packs` SHALL list every pack and bridge in the profile's sources and in installed
packages, with its kind, id, version, source and description, and mark the ones the profile
uses. Copies of one component are listed in the order in which they are searched. Without a
profile, it lists what a new profile in that folder could use.

#### Scenario: A local copy hides the library's

- Given a pack `adr` in `.bondstone/packs` and in bondstone-library, and a profile that names it
- When `bondstone packs` runs
- Then both copies are listed and only the local one is marked as in use
