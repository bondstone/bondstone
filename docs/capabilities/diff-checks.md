---
id: CAP-diff-checks
type: capability:Capability
title: Checks against a base commit
status: active
owner: dworek
code: DIF
constrained_by: [ADR-005]
depends_on: [CAP-graph, CAP-rules, CAP-code-traceability]
---

## Purpose

With `check --base REF`, bondstone also checks how the repository changed: whether statuses
moved the way their lifecycle allows, whether decided documents were left alone, and whether
the documents that a change to code affects changed with it. These checks read git history
and nothing else, so they give the same result locally and in CI.

## Requirements

### REQ-DIF-001: Read history through git only

Bondstone SHALL read history by running `git` in the repository and MUST NOT use the network.
The rules reach git through one interface, so they can be tested without a repository.

#### Scenario: Offline check

- Given a clone with no network access
- When `bondstone check --base origin/main` runs
- Then it completes from the local history

### REQ-DIF-002: Compare with the merge base

Bondstone SHALL compare the working tree with the commit where HEAD left the base ref, not
with the tip of that ref. Commits added to the base after the branch started MUST NOT count as
changes of the branch.

#### Scenario: The base branch moved on

- Given a branch created from `main`, and a later commit on `main` that deprecates ADR-002
- When `bondstone check --base main` runs on the branch
- Then no status change is reported for ADR-002

### REQ-DIF-003: See committed, uncommitted and renamed changes

Bondstone SHALL treat as changed every file that differs between the merge base and the
working tree: committed, staged, unstaged and untracked files, except files git ignores. Each
change is `added`, `modified` or `deleted`; a renamed file is `modified`. A document's earlier
version MUST be found at its path, at the path it was renamed from, or among the deleted files
by its id.

#### Scenario: Renamed and edited decision

- Given an accepted decision that was renamed with `git mv` and then edited
- When `bondstone check --base HEAD` runs
- Then it is compared with the file at its old path and `bondstone/immutable` is reported

### REQ-DIF-004: Require new nodes to start in the initial status

Bondstone SHALL report a new document or item whose status is not its lifecycle's `initial`
as `bondstone/status-initial`. A lifecycle without `initial` MUST NOT be checked.

#### Scenario: Decision born accepted

- Given a lifecycle with `initial: proposed`
- When a change adds a decision with `status: accepted`
- Then `bondstone/status-initial` is reported at the line of `status`

### REQ-DIF-005: Require status changes to follow the lifecycle

Bondstone SHALL report a document or an item whose status changed in a way its lifecycle's
`transitions` do not list as `bondstone/status-transition`, naming the allowed statuses. A
status without outgoing transitions is final. A lifecycle without `transitions` MUST NOT be
checked. An item's earlier status is its `Status:` line in the earlier version of the
document, or the lifecycle's `default`.

#### Scenario: Requirement moved back to planned

- Given a requirement lifecycle with `transitions: {planned: [active, removed], active: [removed]}`
- When a change adds `Status: planned` to an active requirement
- Then `bondstone/status-transition` is reported for the requirement

### REQ-DIF-006: Protect immutable documents

For a type with the `immutable` trait, bondstone SHALL report a document as
`bondstone/immutable` when its earlier status is listed in the trait's `when` and anything
changed other than the frontmatter keys listed in `allow` (default: `status`). Without
`when`, the document MUST be immutable in every status. Whitespace around the body is not a
change.

#### Scenario: Editing an accepted decision

- Given a decision type that is immutable when accepted
- When a change edits the body of an accepted decision
- Then `bondstone/immutable` is reported with the hint to supersede it

### REQ-DIF-007: Trigger diff rules on changed paths and kinds

Bondstone SHALL evaluate a rule with `on_change` when a changed file matches one of its
`paths` globs and the change's kind is listed in `kinds` (default: added, modified and
deleted). A renamed file matches by its old or its new path. A rule overridden to `ignore`
MUST NOT be evaluated.

#### Scenario: Only new files

- Given a rule with `on_change: {paths: ["src/**"], kinds: [added]}`
- When a change only modifies `src/a.py`
- Then the rule is not evaluated

### REQ-DIF-008: Evaluate changed, exists and any clauses

For a triggered diff rule, bondstone SHALL report a `changed` clause when fewer than `min`
changed documents match its selector, an `exists` clause when fewer than `min` documents match
at all, and an `any` clause when none of its alternatives holds. The message MUST name the
changed files, at most five of them.

#### Scenario: Code changed, no spec changed

- Given a rule that requires one changed `living-spec` document when `src/**` changes
- When a change edits `src/a.py` and no capability
- Then the rule is reported and names `src/a.py`

### REQ-DIF-009: Trace changed code regions to documents

For a `changed` clause with `traced: true`, bondstone SHALL find the tags whose region
contains a changed line, in the current file for added and changed lines and in the file at
the merge base for removed lines, and require the document of every such tag that matches the
selector to have changed. A tag on an item counts for the item's document. A change to a tag
line itself MUST NOT count. A new or a deleted file traces every tag in it. When nothing is
traced, the clause holds unless it also has `min`.

#### Scenario: One function of two

- Given a file where one function is tagged for CAP-a and another for CAP-b
- When a change edits only the first function
- Then the rule is reported for CAP-a and not for CAP-b

### REQ-DIF-010: Compare with the baseline when a document is new at the base

Bondstone SHALL compare a document that did not exist at the merge base with its version at
the profile's `baseline` commit, when it existed there with the same id. `bondstone baseline`
MUST write that commit into the profile and change no other line. A baseline that the clone
does not contain is `bondstone/baseline-missing`.

#### Scenario: First check after adoption

- Given accepted decisions that were added in the commit the baseline names
- When `bondstone check --base` runs against a commit from before the adoption
- Then no `bondstone/status-initial` is reported for them

### REQ-DIF-011: Let a commit trailer exempt a change

Bondstone SHALL mark a violation of a diff rule as exempted when the rule declares
`exempt: {trailer: NAME}` and a commit between the merge base and HEAD has a trailer
`NAME: none (<reason>)`. A trailer `NAME: none [ID, ...] (<reason>)` MUST only exempt
violations on the listed nodes. An exempted violation that no waiver removes is reported as
`bondstone/exemption-used` with severity `info`, naming the commit, the rule and the reason,
and JSON output carries `exempted_by` with the commit, the trailer and the reason. A rule
without `exempt` MUST NOT be exempted.

#### Scenario: Pure move

- Given a traced diff rule with `exempt: {trailer: Spec-Impact}`
- When a commit that moves tagged code has the trailer `Spec-Impact: none (pure move)`
- Then the violation is listed as `bondstone/exemption-used` and the run does not fail

### REQ-DIF-012: Reject malformed exemptions and allow strict runs

Bondstone SHALL report a trailer that has the name of a declared exemption and a value that
is not `none (<reason>)` or `none [ID, ...] (<reason>)` as `bondstone/exemption-invalid`, and
MUST NOT exempt anything with it. With `--no-exemptions`, it SHALL ignore every trailer.

#### Scenario: Trailer without a reason

- Given a commit with the trailer `Spec-Impact: none`
- When `bondstone check --base` runs
- Then `bondstone/exemption-invalid` names the commit, and the violation is still reported
