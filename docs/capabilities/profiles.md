---
id: CAP-profiles
type: capability:Capability
title: Profiles, packs and bridges
status: active
owner: Adam Dworzyński
code: PRF
constrained_by: [ADR-002, ADR-003, ADR-004, ADR-011, ADR-012]
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
`sources` (default `.bondstone/packs`) and choose the first copy, in the order in which the
sources are searched, whose version satisfies the requested range, so that a repository can
override a pack with its own copy. Folders are searched before git sources, whatever the
order they are written in, and git sources before installed packages. `adr@1` and `^1` mean any 1.x; comparators such as
`>=1.0` are combined with AND. A component that is missing, or present only in other versions, MUST be a configuration
error. The engine ships no packs of its own.

#### Scenario: A local copy before a newer one

- Given `adr` 1.0.0 in `.bondstone/packs` and `adr` 1.2.0 in an installed package
- When a profile names `adr@1`
- Then the local 1.0.0 is used

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
type, a rule that selects an unknown type, link or role, a view that walks an unknown link in
its levels, its link columns or its matrix path, that selects an unknown type for its rows or
columns, or that writes outside the repository, a trait that names a status its lifecycle
does not declare, and a malformed id or path template. It SHALL also report a view whose keys
do not fit its layout, such as a matrix without `rows`, `cols` and `via`, and a type whose
`derived-status` trait is combined with `lifecycle`, sits on an embedded type or names a file
outside the document's folder. A malformed `.bondstone/known.json` is reported the same way.

#### Scenario: Rule on an unknown type

- Given a rule with `when: {type: Decison}`
- When the configuration is loaded
- Then a `bondstone/profile` error names the unknown type and the rule

### REQ-PRF-007: Apply overrides and respect locked rules

Bondstone SHALL give every rule the severity that `overrides` set for its qualified id, and
its default otherwise. A rule overridden to `ignore` reports nothing. An override for an
unknown rule id, and an override that lowers the severity of a `locked` rule, MUST be
configuration errors.

#### Scenario: Loosening a locked rule

- Given a rule with `locked: true` and severity `error`, and an override that sets it to `warn`
- When the configuration is loaded
- Then a `bondstone/profile` error says the rule is locked

### REQ-PRF-008: Apply waivers that have a reason and an expiry date

Bondstone SHALL drop the diagnostics of a rule that a waiver names, for the waiver's node or
for every node when it names none, up to and including its `expires` date. A waiver without
`rule`, `reason` or `expires`, for an unknown rule or for a locked rule (locked where it is
declared, or by a preset) MUST be reported as
`bondstone/waiver-invalid`, an expired one as `bondstone/waiver-expired`, and one that matches
nothing as `bondstone/waiver-unused`. Waivers are applied before known violations.

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
errors as `bondstone/profile` diagnostics, in the output format that was asked for, which no
override or waiver can silence.

#### Scenario: Check with a broken profile

- Given a profile that names a pack that does not exist
- When `bondstone check` runs
- Then only configuration errors are printed and the exit code is 2

### REQ-PRF-011: Resolve packs and bridges from installed packages

Bondstone SHALL search, after the profile's `sources`, every folder that an installed Python
package registers under the entry point group `bondstone.sources`, such as bondstone-library.
A component in the profile's own sources MUST win over one with the same id in an installed
package, and nothing from an installed package is loaded unless the profile names it. A
registered source that cannot be loaded MUST be a configuration error that names the package.

#### Scenario: A pack from the library

- Given bondstone-library is installed and a profile names `adr@1` without having it locally
- When the configuration is loaded
- Then the pack `adr` is read from the library's folder

#### Scenario: A local pack with the same id

- Given a pack `adr` in `.bondstone/packs` and another in an installed package
- When the configuration is loaded
- Then the local pack is used

### REQ-PRF-012: Create a profile

`bondstone init` SHALL create `.bondstone/profile.yaml` in the folder given with `--root`, or
in the current folder, as a valid profile without packs. With `--preset NAME` the profile
extends that preset, in the major version that is available; a preset that is not available
MUST be refused. It MUST refuse to overwrite an existing profile.

#### Scenario: A profile exists already

- Given a folder with `.bondstone/profile.yaml`
- When `bondstone init` runs there
- Then the command fails with exit code 1 and the file is unchanged

#### Scenario: Start from a preset

- Given bondstone-library is installed
- When `bondstone init --preset starter` runs in an empty folder
- Then the new profile has `extends: [starter@1]` and passes `bondstone profile check`

### REQ-PRF-013: Extend presets

Bondstone SHALL load every preset a profile names under `extends`, found in the same sources
as packs, as a `preset.yaml` validated against its schema. A preset may name git sources of
its own under `sources`, where its packs, its bridges and the presets it extends are found; a
folder there MUST be a configuration error. A preset may extend other presets;
those are applied before it, and a preset reached more than once is applied once. The packs
and bridges of the presets are used together with the profile's own, and a component named
more than once MUST satisfy every range asked for. The rules a preset defines are qualified
with its id. A preset that is missing, that extends itself, or whose version does not satisfy
a range MUST be a configuration error.

#### Scenario: A profile that only extends

- Given a preset `starter` with the packs `adr` and `capability` and their bridge
- When a profile has `extends: [starter@1]` and no packs of its own
- Then the two packs and the bridge are active, and the preset's rule is `starter/<rule id>`

#### Scenario: A preset built on another

- Given a preset `team` with `extends: [starter@1]`
- When a profile extends `team`
- Then `starter` is applied first, then `team`, then the profile

### REQ-PRF-014: Apply severities in layers

Bondstone SHALL apply `overrides` in this order: the rule's default, then each preset in the
order it is applied, then the profile, so that a later layer wins. `bondstone rules` and
`bondstone explain` MUST say which layer set the effective severity.

#### Scenario: The profile is stricter than its preset

- Given a preset that sets `adr/alternatives-considered: info` and a profile that sets it to `error`
- When the configuration is loaded
- Then the rule is an error, set by the profile

### REQ-PRF-015: Let a preset lock rules

Bondstone SHALL treat every rule a preset lists under `lock` as locked at the severity in
force after that preset, whether a pack, a bridge, a preset or the engine defines the rule. A
later preset or the profile may raise the severity of a locked rule; lowering it or waiving it
MUST be a configuration error or an invalid waiver. A `lock` entry for an unknown rule MUST be
a configuration error. An entry is a rule id, or `{rule: ID, allow_known: false}` for a rule
that must also hold for existing documents ([CAP-known-violations](known-violations.md)).

#### Scenario: An organisation's rule

- Given a preset with `overrides: {bondstone/immutable: error}` and `lock: [bondstone/immutable]`
- When a profile that extends it sets `bondstone/immutable: warn`
- Then a `bondstone/profile` error says the rule is locked by that preset

### REQ-PRF-016: Add a waiver from the command line

`bondstone waive RULE [NODE] --reason R --expires D` SHALL add a waiver to the profile as one
line under `waivers`, leaving every other line as it is, and without NODE the waiver covers
every node. It MUST refuse, and change nothing, when the rule is unknown, is locked or is
`bondstone/profile`, when the node does not exist, when the reason is empty, when the date is
malformed or in the past, and when the same rule and node are waived already.

#### Scenario: A decision from before the rule

- Given ADR-004, an accepted decision without alternatives
- When `bondstone waive adr/alternatives-considered ADR-004 --reason "..." --expires 2027-06-30` runs
- Then the profile has that waiver and `bondstone check` no longer reports the rule for ADR-004

#### Scenario: A locked rule

- Given a preset that locks `adr/alternatives-considered`
- When `bondstone waive adr/alternatives-considered ADR-004 ...` runs
- Then it exits with 1, says which preset locks the rule, and the profile is unchanged

### REQ-PRF-017: Name git sources

A profile's `sources` and a preset's `sources` SHALL accept git sources written
`host/org/repo//path@ref`: a repository, a folder in it (the root when left out) and a tag, a
branch or a commit. The folder holds one component per subfolder, or is one component itself.
A profile that names no folder keeps the default folder next to its git sources. An entry
with `//` or `@` that is not a git source MUST be a configuration error.

#### Scenario: Packs of an organisation

- Given the profile entry `github.com/acme/bondstone-packs//packs@v1.2.0`
- When the configuration is loaded
- Then the packs in the folder `packs` of that repository at `v1.2.0` can be named under `packs`

### REQ-PRF-018: Pin git sources in a lock file

`.bondstone/bondstone.lock` SHALL record for every git source that the profile and its
presets reach the commit its ref stood for and, for each pack, bridge and preset in it, the
kind, id, version and a SHA-256 over the paths and contents of its files. The file is written
by `bondstone update`, sorted by source, and is deleted when nothing is pinned. A lock that
does not match its schema MUST be a configuration error.

#### Scenario: A branch that moved

- Given a source written with `@main`, pinned last week
- When `bondstone check` runs after the branch got new commits
- Then the pinned commit is used

### REQ-PRF-019: Read git sources from the lock and the cache only

Every command except `update` SHALL read a git source from a cache outside the repository
(`$BONDSTONE_CACHE`, else `bondstone` in the user's cache folder), at the commit the lock
pins, and MUST NOT use the network. A source that the lock does not pin is a configuration
error that says to run `bondstone update`. A source whose commit is not in the cache, or
whose cached files do not have the hashes of the lock, is an environment error (exit code 3)
that says to run `bondstone update --locked`. Neither is followed by reports of the
components the source would hold. Diagnostics name a manifest from a git source by the
source and the path inside it, not by its place in the cache.

#### Scenario: A fresh clone in CI

- Given a repository with a lock and a machine with an empty cache
- When `bondstone check` runs
- Then it exits with 3 and says to run `bondstone update --locked`

#### Scenario: A source added without updating

- Given a profile with a new git source and a lock from before
- When `bondstone check` runs
- Then a `bondstone/profile` error says the source is not in the lock, and the exit code is 2

### REQ-PRF-020: Fetch and pin with update

`bondstone update` SHALL fetch every git source the profile reaches, also through presets
that name sources of their own, resolve each ref to a commit, put the source's folder at that
commit into the cache and rewrite the lock; a source that nothing names any more leaves it.
With names, only the sources that hold a component of that name move, and the others keep
their commit. `bondstone update --locked` SHALL fetch exactly the pinned commits, replace
cached files that differ and leave the lock as it is; it MUST refuse a lock that does not pin
a source or whose hashes the pinned commit does not have. A source without components MUST be
refused, and a ref or a repository that cannot be fetched is an environment error. Git is
never asked for a password, so a job cannot hang. Private repositories are read with the
credentials git already has, from a credential helper or a URL rewritten with
`url.<base>.insteadOf`; bondstone keeps no credentials of its own. When git cannot read a
repository, the message says that it does not exist or that git has no credentials for it,
and a user name or password that a URL carries MUST NOT appear in a message, in the lock or
in the cache.

#### Scenario: A private repository without credentials

- Given a git source in a private repository and no credential helper
- When `bondstone update` runs
- Then it exits with 3 at once, and says that the repository does not exist or that git has no credentials for it

#### Scenario: A moved tag does not move the lock

- Given a lock that pins `v1` at a commit, and a remote where `v1` now names another commit
- When `bondstone update --locked` runs with an empty cache
- Then the pinned commit is fetched and the lock is unchanged

#### Scenario: One pack moves

- Given two sources written with `@main` that both got new commits
- When `bondstone update architecture` runs
- Then only the source that holds `architecture` gets a new commit in the lock
