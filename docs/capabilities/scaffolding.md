---
id: CAP-scaffolding
type: capability:Capability
title: Scaffolding and edits
status: active
owner: Adam Dworzyński
code: SCF
depends_on: [CAP-graph, CAP-rules, CAP-views]
---

## Purpose

Ids, paths, statuses and supersede links are the parts of a document that rules check
mechanically, so commands write them. A command either leaves the repository valid or refuses
and changes nothing, and it tells the caller what it wrote.

## Requirements

### REQ-SCF-001: Scaffold a document at the right id and path

`bondstone new TYPE --title T` SHALL create a document of the type with the next id from the
type's `id` template and at the path from its `path` template. `{n}` is one more than the
highest number an existing id of the type carries, `{slug}` comes from the title, and any
other placeholder is a field given with `--set`. The type may be named without its pack when
only one pack has it. An embedded type, an id that is taken and a file that exists MUST be
refused.

#### Scenario: Third decision

- Given decisions ADR-001 and ADR-002 and the template `docs/adr/{id}-{slug}.md`
- When `bondstone new adr:Decision --title "Use a queue"` runs
- Then `docs/adr/ADR-003-use-a-queue.md` is created

### REQ-SCF-002: Write a document that passes the check

A scaffolded document SHALL have `id`, `type`, `title`, the lifecycle's `initial` status, the
git user name as owner, or the profile's `defaults.owner` when git has none, today's date in
required date fields, the fields and links given with `--set KEY=VALUE`, and the type's template as its
body, or else its required sections. Bondstone MUST refuse, naming the `--set` to add, when a
required field or a required link is missing, when a key is neither a field nor a link of the
type, and when a link names a node that does not exist. `check` on the result reports only
leftover placeholders.

#### Scenario: Capability without its code

- Given a capability type that requires `code`
- When `bondstone new Capability --title "Sync"` runs
- Then it exits with 1 and says to pass `--set code=...`, and no file is written

### REQ-SCF-003: Change a status within the lifecycle

`bondstone status ID STATUS` SHALL set the status of a document in its frontmatter, and the
status of an item in the `Status:` line under its heading, which it adds when the item has
none. It MUST write the line for the lifecycle's `default` status too. It MUST refuse a status the lifecycle does not have, a
step the lifecycle's `transitions` do not allow, and a document that is immutable in its
current status without `status` among the fields that may change.

#### Scenario: Back to proposed

- Given an accepted decision whose lifecycle allows `accepted` to become `deprecated` or `superseded`
- When `bondstone status ADR-002 proposed` runs
- Then it exits with 1, names the allowed statuses and leaves the file as it was

### REQ-SCF-004: Supersede a document

`bondstone supersede ID --title T` SHALL create a successor of the same type that links to the
old document with the type's supersede link, set the old document's status to `superseded`,
and replace the old id with the new one in every other link that pointed at it. Links of
documents that are immutable in their current status MUST stay as they are and be listed as
skipped. A document that is not supersedable, is already superseded, or whose lifecycle does
not allow `superseded` from its status MUST be refused before anything is written.

#### Scenario: Capability constrained by the old decision

- Given a capability with `constrained_by: [ADR-002]`
- When `bondstone supersede ADR-002 --title "Do it better"` creates ADR-003
- Then the capability has `constrained_by: [ADR-003]` and ADR-002 is `superseded`

### REQ-SCF-005: Edit only the lines that change

When a command changes an existing document, bondstone SHALL rewrite only the lines of the
frontmatter key or the `Status:` line it changes. Comments, key order and the body MUST stay
as they are. Frontmatter written as one `{...}` mapping is rewritten with one key per line
first.

#### Scenario: Comment next to another key

- Given frontmatter with a comment line above `id`
- When `bondstone status` changes the document's status
- Then the comment and every other line are unchanged

### REQ-SCF-006: Regenerate views after an edit

After `new`, `status` and `supersede`, bondstone SHALL regenerate the views that the edit made
stale and list them. With `--format json` each command prints one object with what it created
or changed and the views it wrote.

#### Scenario: New decision and the decision log

- Given a decision log view
- When `bondstone new adr:Decision --title "Use a queue"` runs
- Then the output lists the decision log as written, and `check` reports no stale view
