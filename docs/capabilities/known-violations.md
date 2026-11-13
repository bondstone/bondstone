---
id: CAP-known-violations
type: capability:Capability
title: Known violations
status: draft
owner: Adam Dworzyński
code: KNV
depends_on: [CAP-rules, CAP-profiles, CAP-diff-checks]
constrained_by: [ADR-006]
---

## Purpose

A repository with years of documents breaks many rules on the day it adopts bondstone, or on
the day it adopts a stricter rule. Known violations put those problems on record in
`.bondstone/known.json`, so that the gate holds for new work from the first commit and the old
problems are fixed over time. The file can only shrink.

## Requirements

### REQ-KNV-001: Record the current violations

`bondstone baseline --known` SHALL write every current error and warning whose rule accepts
known violations to `.bondstone/known.json`, as the format version, the day the file was
first written and a sorted list with one entry per line. Recording again keeps that day and
the entries that still match. It MUST say how many violations it recorded, how many of them
are new, and how many it could not record. It MUST write no file when there is nothing to
record, and it takes no commit.

#### Scenario: A decision without a required section

- Given ADR-001 without the section `Consequences` that its type requires
- When `bondstone baseline --known` runs
- Then `known.json` has the entry `bondstone/section-missing`, `ADR-001`, `Consequences`

#### Scenario: Nothing to record

- Given a repository whose check reports nothing
- When `bondstone baseline --known` runs
- Then it prints `no violations to record` and writes no file

### REQ-KNV-002: Identify a violation without line numbers

An entry SHALL identify a violation by its rule, its node and a key that names the problem,
such as the missing section, the unknown field or the target of a broken link. A violation
that concerns a file and no node, such as a file that is no document, is identified by its
path instead of a node. For a declared rule the key says what the failed clause asks for; for
a link clause with `all: true` it lists the targets that are not allowed. The key MUST NOT
contain line numbers or counts.

#### Scenario: Text added above the problem

- Given a known violation in ADR-001
- When a section is added at the top of ADR-001
- Then the violation still matches its entry

#### Scenario: A file that is no document

- Given `docs/notes.md`, which is at no type's path
- When `bondstone baseline --known` runs
- Then the entry has `path: docs/notes.md` and no `node`

### REQ-KNV-003: Report a known violation as info

`check` SHALL report a violation that matches an entry with the severity `info`, marked
`[known]` in text and `known: true` in JSON, and count it in the summary. Such a violation
does not fail the run, also with `--fail-on warn`. A violation that matches no entry keeps its
severity, whether it is in a new document or in one that has known violations already.
Waivers are applied first.

#### Scenario: A second problem in the same document

- Given ADR-001 with a known missing section
- When a link to a document that does not exist is added to ADR-001
- Then `bondstone/link-broken` is an error and the missing section stays info

### REQ-KNV-004: Report entries that match nothing

`check` SHALL report every entry that no violation matched as `bondstone/known-stale`, a
warning at the entry's line of `known.json`, and say why: the violation no longer occurs, the
rule does not exist, or the rule does not accept known violations.

#### Scenario: The problem was fixed

- Given a known missing section in ADR-001
- When the section is added
- Then `bondstone/known-stale` names the entry and suggests `bondstone baseline --known --prune`

### REQ-KNV-005: Prune without adding

`bondstone baseline --known --prune` SHALL remove the entries that match nothing and MUST NOT
add an entry. When the last entry goes it deletes the file. `--prune` without `--known` is
refused.

#### Scenario: One fixed, one new

- Given two known violations, one of them fixed, and one violation that is not recorded
- When `bondstone baseline --known --prune` runs
- Then the file has one entry and the unrecorded violation is still an error

### REQ-KNV-006: Catch a file that grew

With `--base`, `check` SHALL report the entries that `known.json` did not have at the merge
base as one `bondstone/known-grew` error that says how many there are and names the first
ones. A file that did not exist at the base had no entries. The change that adds the profile
itself is the adoption: its entries MUST NOT be reported. A deliberate reset is an override of
`bondstone/known-grew` in the same change.

#### Scenario: Recording a new violation

- Given a repository with a committed `known.json`
- When a new document breaks a rule and `bondstone baseline --known` runs again
- Then `check --base` fails with `bondstone/known-grew`

#### Scenario: The adoption commit

- Given a repository without a profile at the base
- When one change adds the profile, the documents and `known.json`
- Then `check --base` reports the known violations as info and no `bondstone/known-grew`

### REQ-KNV-007: Let a rule refuse known violations

A rule declared with `allow_known: false`, and a rule that a preset locks with the entry
`{rule: ID, allow_known: false}`, SHALL keep its severity for every violation: `baseline
--known` does not record it and an entry for it is stale. The same holds for rules that are
about a change or about the configuration and not about the state of a document: diff rules,
the checks of lifecycles and immutability, stale views, waivers, exemptions and the two rules
about `known.json` itself. A locked rule accepts known violations unless it says otherwise.
`bondstone rules` and `bondstone explain` MUST say when a rule was declared or locked without
known violations.

#### Scenario: An organisation's rule from day one

- Given a preset with `lock: [{rule: bondstone/section-missing, allow_known: false}]`
- When `bondstone baseline --known` runs in a repository with a missing section
- Then nothing is recorded for that rule and `check` reports the error

### REQ-KNV-008: Reject a malformed file

A `known.json` that is not valid JSON, does not match the schema shipped with bondstone, or
has an entry without exactly one of `node` and `path` MUST be a configuration error at that
file.

#### Scenario: An entry without a node

- Given an entry `{"rule": "adr/alternatives-considered"}`
- When `bondstone check` runs
- Then it stops with exit code 2 and names `.bondstone/known.json`
