---
id: CAP-cli
type: capability:Capability
title: Command line and output
status: active
owner: Adam Dworzyński
code: CLI
constrained_by: [ADR-001]
depends_on: [CAP-profiles, CAP-rules, CAP-views, CAP-diff-checks]
---

## Purpose

One program, `bondstone`, is what people, agents, git hooks and CI run. Its output is made to
be acted on: one line per problem for people, the same diagnostics as JSON for agents, and
exit codes that tell wrong work from a checker that could not run.

## Requirements

### REQ-CLI-001: Check a repository

`bondstone check` SHALL report every diagnostic of the repository's documents, links, rules,
code tags and views, after overrides and waivers. With `--base REF` it SHALL add the checks
that compare with a base commit, and `--no-exemptions` makes those ignore commit trailers.

#### Scenario: Clean repository

- Given a repository without violations
- When `bondstone check` runs
- Then it prints one summary line and exits with 0

### REQ-CLI-002: Regenerate views

`bondstone gen` SHALL write the views that are stale and list them.

#### Scenario: Stale view

- Given a repository with one stale view
- When `bondstone gen` runs
- Then it prints `wrote` and the view's path

### REQ-CLI-003: Check the configuration alone

`bondstone profile check` SHALL validate the profile, the packs and the bridges without
reading documents, and report configuration errors and configuration warnings.

#### Scenario: Unbridged packs

- Given a valid profile whose packs no bridge connects
- When `bondstone profile check` runs
- Then it prints the warning and exits with 0

### REQ-CLI-004: Record the baseline

`bondstone baseline [REF]` SHALL record the commit that REF names, HEAD by default, as the
profile's baseline and print it. With `--known` it records the current violations instead,
and with `--known --prune` it removes the recorded ones that no longer occur
([CAP-known-violations](known-violations.md)).

#### Scenario: Baseline at HEAD

- Given a git repository with a valid profile
- When `bondstone baseline` runs
- Then the profile has a `baseline` line with the id of HEAD

### REQ-CLI-005: Print diagnostics as text

With `--format text`, the default, bondstone SHALL print one line per diagnostic,
`path:line: severity rule: message`, followed by an indented hint when the diagnostic has
one, and a last line with the number of errors, warnings and nodes. Diagnostics are ordered by
path and line. A known violation is marked `[known]`, and the last line says how many of the
info diagnostics are known.

#### Scenario: Broken link

- Given a document with a broken link at line 6
- When `bondstone check` runs
- Then a line starts with the document's path, `:6: error bondstone/link-broken:`

### REQ-CLI-006: Print diagnostics as versioned JSON

With `--format json`, bondstone SHALL print one object with `version`, `summary` and
`diagnostics`. Each diagnostic has `rule`, `severity` and `message`, and `path`, `line`,
`node`, `hint`, `fix`, `exempted_by` and `known` when they apply. The summary has `known`
when there are known violations. With `--base` the object has `base`: the ref that was given,
the commit the working tree was compared with, and the files that differ, each with its path,
its kind and, when it was renamed, its old path. `version` MUST change when a key changes its
meaning or goes away.

#### Scenario: Fix command

- Given a stale view
- When `bondstone check --format json` runs
- Then the diagnostic has `"fix": {"command": ["bondstone", "gen"]}`

### REQ-CLI-007: Tell wrong work from a checker that could not run

Bondstone SHALL exit with 0 when no diagnostic reaches the `--fail-on` severity (`error` by
default, or `warn`), with 1 when one does, with 2 on a configuration error, and with 3 on an
environment error: no profile found, a root that is not a directory, `--base` or `baseline`
outside a git repository, or a ref that is not a commit. A command that refuses what it was
asked, such as explaining a rule that does not exist, MUST say why on standard error and exit
with 1.

#### Scenario: Unknown base ref

- Given a git repository without the ref `origin/main`
- When `bondstone check --base origin/main` runs
- Then nothing is printed to standard output and the exit code is 3

### REQ-CLI-008: Report where the documentation stands

`bondstone report` SHALL count the nodes by type and status; for every code-traceable type the
nodes in a status that needs code and how many of them are tagged; the waivers with their
state (`active`, `expiring` within 30 days, `expired`, `unused` or `invalid`); and the known
violations per rule and per type of their node. With `--base REF` it also counts the
exemptions used since REF per rule and per commit author. It prints text or JSON, and what it
counts never makes it fail: the exit code is 0 unless the configuration or the environment
stops it.

#### Scenario: Cleanup in progress

- Given a `known.json` with 40 entries for `bondstone/section-missing`, 38 of them on decisions
- When `bondstone report` runs
- Then it lists 40 for the rule and 38 for `adr:Decision`

#### Scenario: Violations do not fail the report

- Given a repository whose check reports errors
- When `bondstone report` runs
- Then the exit code is 0

### REQ-CLI-009: Say in JSON why a command stopped

With `--format json`, a command that refuses what it was asked or that cannot run SHALL print
`{"version": 1, "error": {"kind": K, "message": M}}` on standard output, with the kind
`refused` (exit code 1) or `environment` (exit code 3) and the message it prints on standard
error. The exit codes stay as they are, so a program tells a refused command from a check that
found violations by the `error` key. Text output is unchanged.

#### Scenario: Status of a node that does not exist

- Given no node `ADR-404`
- When `bondstone status ADR-404 accepted --format json` runs
- Then standard output has an `error` of kind `refused` and the exit code is 1
