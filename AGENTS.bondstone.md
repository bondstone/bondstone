<!-- bondstone:generated agent instructions; do not edit, run `bondstone agent` -->
# Documentation rules (bondstone)

`bondstone` checks this repository's living documentation. The rules below are the ones it enforces.

## Workflow

1. Before you edit code or documents, run `bondstone context --for <paths>`. It lists the documents to read first and the rules that will fire.
2. Create a document with `bondstone new <Type> --title "..."`, never by hand. It picks the id, the path and the frontmatter. Some types are items: headings inside a document, which you add by hand. The type's entry below gives the heading and the id to use.
3. Change a status with `bondstone status <ID> <STATUS>`. Replace a document that may no longer be edited with `bondstone supersede <ID> --title "..."`.
4. Write links as ids in frontmatter, never as paths.
5. Put a comment `bondstone: <ID>` above the code that implements a node, and update that node's document when you change the code.
6. After you edit documents by hand, run `bondstone gen`. It rewrites the generated files listed below. Never edit those files or this one yourself.
7. Before you finish, run `bondstone check --base <upstream branch> --format json` and fix every error. It compares your working tree, committed or not, with that branch. When a diagnostic has `fix.command`, run that command. `bondstone explain <rule>` says what a rule wants.
8. Never weaken `.bondstone/profile.yaml` (overrides, waivers) to make a check pass. Ask the user instead.
9. Do not add an exemption trailer (`Spec-Impact`) to a commit unless the user asked for one.

Active packs and bridges: adr@1.0.0 (pack), capability@1.0.0 (pack), adr-capability@1.0.0 (bridge)

## Document types

### `adr:Decision`

One architecturally significant decision and its rationale.

- location: `docs/adr/{id}-{slug}.md`
- id: `ADR-{n:03d}`
- create: `bondstone new adr:Decision --title "..."`
- fields: title (required), date (required), deciders, tags
- required sections: Context, Decision, Consequences
- status: proposed | accepted | rejected | deprecated | superseded (new ones start as `proposed`)
- allowed status changes: proposed → accepted, rejected; accepted → deprecated, superseded; deprecated → superseded
- needs an `owner`
- immutable once accepted, rejected, deprecated, superseded: only status may change; supersede it instead of editing it
- links: `supersedes` → adr:Decision (at most 1)

### `capability:Capability`

The living specification of one capability. It describes current behaviour and is updated whenever that behaviour changes.

- location: `docs/capabilities/{slug}.md`
- id: `CAP-{slug}`
- create: `bondstone new capability:Capability --title "..." --set code=...`
- fields: title (required), code (required)
- required sections: Purpose, Requirements
- status: draft | active | deprecated (new ones start as `draft`)
- allowed status changes: draft → active, deprecated; active → deprecated
- needs an `owner`
- links: `depends_on` → capability:Capability; `constrained_by` → adr:Decision

### `capability:Requirement`

One requirement inside a capability, written as a level-3 heading `### REQ-<CODE>-001: <title>` under `## Requirements`, with SHALL/MUST wording and at least one `#### Scenario:`. A line `Status: planned` or `Status: removed` under the heading sets its status; without it the requirement is active.

- add one by hand inside a `capability:Capability` document, as a heading `### {id}: {title}` under `## Requirements`
- id: `REQ-{code}-{n:03d}` (`{code}` is that document's `code` field; `{n}` is the next free number in that document)
- status: planned | active | removed (`active` without a `Status:` line under the heading)
- allowed status changes: planned → active, removed; active → removed
- tag the code that implements it with a comment `bondstone: <ID>`; one without a tag in status active is reported (warn); remove the tag in status removed

## Roles

Rules name roles so that they work across packs.

- `decision`: adr:Decision
- `living-spec`: capability:Capability

## Rules

Severities are the effective ones, after this repository's overrides.

- **`adr/alternatives-considered`** (warn): Accepted decisions record the alternatives that were considered. _Add a "## Alternatives considered" section._
- **`capability/requirement-has-scenario`** (error): Every requirement has at least one scenario. _Add '#### Scenario: <name>' with Given/When/Then lines._
- **`capability/requirement-uses-normative-language`** (error): Requirements use SHALL or MUST.
- **`capability/active-capability-has-requirements`** (error): An active capability lists at least one requirement.
- **`adr-capability/constrained-by-live-decision`** (error): Capabilities are constrained only by accepted or proposed decisions. _Point to the decision that superseded it._
- **`adr-capability/accepted-decision-is-applied`** (warn): An accepted decision constrains at least one capability (otherwise, is it still relevant?).
- **`profile/source-change-updates-traced-spec`** (error): A change to bondstone's source updates the capability specs the changed code implements. _Update the capability, or add the commit trailer "Spec-Impact: none (<reason>)" when no behaviour changed._

The engine's own rules (`bondstone/...`) check structure: ids, fields, sections, links, code tags and stale views. `bondstone rules` lists them all.

## Generated files

`bondstone gen` writes these. Do not edit them.

- `docs/generated/decisions.md` (adr/decision-log)
- `docs/generated/capabilities.md` (capability/index)
- `docs/generated/requirements.md` (capability/requirements)

## Guidance from `adr`

- Write an ADR when a change makes a decision that future readers would not understand
  from the code alone: a new dependency, a storage or protocol choice, a structural pattern.
- Once an ADR is accepted, do not edit it. Run `bondstone supersede ADR-xxx --title "..."`:
  it creates the successor, marks the old one `superseded` and moves links to the new one.
- Create ADRs as `proposed` and accept them in a later change.

## Guidance from `capability`

- `docs/capabilities/` describes what the system does **today**. When a change alters
  behaviour, update the affected capability in the same change; do not leave it for later.
- Add requirements as `### REQ-<CODE>-NNN: title` under `## Requirements`, never renumber
  existing ones, and remove requirements that no longer hold.
- Mark the code that implements a requirement with a comment `bondstone: REQ-<CODE>-NNN`.
- A requirement whose code arrives in the same change is active: write no `Status:` line.
  Write `Status: planned` under the heading only when the requirement has no code yet, and
  `Status: removed` when it no longer holds but its code is still there.

## Guidance from `adr-capability`

- When a capability's behaviour depends on a decision, list it in `constrained_by`.
- When an ADR is superseded, move every `constrained_by` reference to the new ADR.
