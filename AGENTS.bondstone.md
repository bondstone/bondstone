<!-- bondstone:generated agent instructions; run `bondstone agent` to refresh -->
# Documentation rules (bondstone)

This repository's living documentation is validated by `bondstone`. Before finishing any task:

1. Create new documents with `bondstone new <Type> --title "..."` instead of by hand.
2. Keep frontmatter links (ids, not paths) accurate.
3. Run `bondstone gen` to refresh generated views.
4. Run `bondstone check --format json` (add `--base origin/main` on branches) and fix every error.
5. Never weaken `.bondstone/profile.yaml` (overrides, waivers) to make a check pass; ask instead.

Active packs and bridges: adr@1.0.0 (pack), capability@1.0.0 (pack), adr-capability@1.0.0 (bridge)

## Document types

### `adr:Decision`
One architecturally significant decision and its rationale.
- location: `docs/adr/*.md`
- id: `^ADR-\d{3,}$`
- required fields: title, date
- required sections: Context, Decision, Consequences
- status: proposed | accepted | rejected | deprecated | superseded
- transitions: proposed → accepted, rejected; accepted → deprecated, superseded; deprecated → superseded
- requires `owner`
- immutable once accepted, rejected, deprecated, superseded: supersede instead of editing
- links: `supersedes` → adr:Decision (max 1)

### `capability:Capability`
The living specification of one capability. It describes current behaviour and is updated whenever that behaviour changes.
- location: `docs/capabilities/*.md`
- id: `^CAP-[a-z0-9]+(-[a-z0-9]+)*$`
- required fields: title, code
- required sections: Purpose, Requirements
- status: draft | active | deprecated
- transitions: draft → active, deprecated; active → deprecated
- requires `owner`
- links: `depends_on` → capability:Capability; `constrained_by` → adr:Decision

### `capability:Requirement`
One requirement inside a capability, written as a level-3 heading `### REQ-<CODE>-001: <title>` under `## Requirements`, with SHALL/MUST wording and at least one `#### Scenario:`.
- written as headings inside its parent document
- id: `^REQ-[A-Z0-9]+-\d{3}$`
- reference it from code with a `bondstone: <id>` comment

## Roles

- `decision`: adr:Decision
- `living-spec`: capability:Capability

## Rules

- **`adr/alternatives-considered`** (warn): Accepted decisions record the alternatives that were considered. — _Add a "## Alternatives considered" section._
- **`capability/requirement-has-scenario`** (error): Every requirement has at least one scenario. — _Add '#### Scenario: <name>' with Given/When/Then lines._
- **`capability/requirement-uses-normative-language`** (error): Requirements use SHALL or MUST.
- **`capability/active-capability-has-requirements`** (error): An active capability lists at least one requirement.
- **`adr-capability/constrained-by-live-decision`** (error): Capabilities are constrained only by accepted or proposed decisions. — _Point to the decision that superseded it._
- **`adr-capability/accepted-decision-is-applied`** (warn): An accepted decision constrains at least one capability (otherwise, is it still relevant?).
- **`profile/code-change-updates-living-spec`** (warn): Changes to bondstone's source come with an update to a capability spec.

## Guidance from `adr`

- Write an ADR when a change makes a decision that future readers would not understand
  from the code alone: a new dependency, a storage or protocol choice, a structural pattern.
- Once an ADR is accepted, do not edit it. Create a new ADR with `supersedes: ADR-xxx` and
  set the old one's status to `superseded`.

## Guidance from `capability`

- `docs/capabilities/` describes what the system does **today**. When a change alters
  behaviour, update the affected capability in the same change; do not leave it for later.
- Add requirements as `### REQ-<CODE>-NNN: title` under `## Requirements`, never renumber
  existing ones, and remove requirements that no longer hold.
- Mark the code that implements a requirement with a comment `bondstone: REQ-<CODE>-NNN`.

## Guidance from `adr-capability`

- When a capability's behaviour depends on a decision, list it in `constrained_by`.
- When an ADR is superseded, move every `constrained_by` reference to the new ADR.
