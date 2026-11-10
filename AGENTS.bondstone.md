<!-- bondstone:generated agent instructions; run `bondstone agent` to refresh -->
# Documentation rules (bondstone)

This repository's living documentation is validated by `bondstone`. Before finishing any task:

1. Create new documents with `bondstone new <Type> --title "..."` instead of by hand.
2. Keep frontmatter links (ids, not paths) accurate. To replace a document, run
   `bondstone supersede <ID> --title "..."` instead of editing it.
3. Run `bondstone gen` to refresh generated views.
4. Run `bondstone check --format json` (add `--base origin/main` on branches) and fix every error.
5. Never weaken `.bondstone/profile.yaml` (overrides, waivers) to make a check pass; ask instead.

Active packs and bridges: adr@1.0.0 (pack), capability@1.0.0 (pack), change@0.1.0 (pack), release@0.1.0 (pack), cli@0.1.0 (pack), adr-capability@1.0.0 (bridge), change-capability@0.2.0 (bridge), change-adr@0.1.0 (bridge), release-change@0.1.0 (bridge), cli-capability@0.1.0 (bridge)

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

### `change:Proposal`
A proposed change to the system, its motivation and scope.
- location: `docs/changes/*.md`
- id: `^CHG-\d{3,}$`
- required fields: title, kind
- required sections: Why, What changes, Out of scope
- status: draft | accepted | implemented | rejected | withdrawn
- transitions: draft → accepted, rejected, withdrawn; accepted → implemented, withdrawn
- requires `owner`
- immutable once implemented, rejected, withdrawn: supersede instead of editing
- links: `modifies` → capability:Capability; `delivers` → capability:Requirement; `decided_by` → adr:Decision

### `release:Release`
One published version.
- location: `docs/releases/*.md`
- id: `^v\d+\.\d+\.\d+$`
- required fields: title, version
- required sections: Highlights
- status: planned | released
- transitions: planned → released
- immutable once released: supersede instead of editing
- links: `includes` → change:Proposal

### `cli:Command`
One CLI command (a subcommand, or a nested one such as `profile check`).
- location: `docs/cli/*.md`
- id: `^CLI-[a-z]+(-[a-z]+)*$`
- required fields: title, synopsis
- required sections: Options, Exit codes, Examples
- status: draft | experimental | stable | deprecated
- transitions: draft → experimental, stable; experimental → stable, deprecated; stable → deprecated
- reference it from code with a `bondstone: <id>` comment
- links: `implements` → capability:Capability (min 1)

## Roles

- `decision`: adr:Decision
- `living-spec`: capability:Capability
- `change`: change:Proposal
- `interface`: cli:Command

## Rules

- **`adr/alternatives-considered`** (warn): Accepted decisions record the alternatives that were considered. — _Add a "## Alternatives considered" section._
- **`capability/requirement-has-scenario`** (error): Every requirement has at least one scenario. — _Add '#### Scenario: <name>' with Given/When/Then lines._
- **`capability/requirement-uses-normative-language`** (error): Requirements use SHALL or MUST.
- **`capability/active-capability-has-requirements`** (error): An active capability lists at least one requirement.
- **`change/breaking-change-has-migration`** (error): Breaking changes explain how users migrate.
- **`release/released-has-date`** (error): A released version records its release date.
- **`cli/json-output-is-documented`** (error): Stable commands with JSON output document its shape.
- **`adr-capability/constrained-by-live-decision`** (error): Capabilities are constrained only by accepted or proposed decisions. — _Point to the decision that superseded it._
- **`adr-capability/accepted-decision-is-applied`** (warn): An accepted decision constrains at least one capability (otherwise, is it still relevant?).
- **`change-capability/accepted-proposal-names-capabilities`** (error): Accepted behaviour changes name the capability specs they modify.
- **`change-capability/implemented-proposal-delivers-requirements`** (error): An implemented feature points at the requirements it delivered in the living spec. — _Add the requirement to the capability spec, then `delivers: [REQ-...]`._
- **`change-capability/delivered-requirements-are-implemented`** (error): Requirements delivered by an implemented proposal are tagged in code. — _Tag the implementing code with `bondstone: REQ-...`._
- **`change-adr/implemented-proposal-has-accepted-decisions`** (error): A proposal is implemented only on accepted decisions.
- **`release-change/release-includes-only-implemented`** (error): Releases include only implemented proposals.
- **`release-change/implemented-proposal-is-released`** (warn): Every implemented proposal is part of a (planned or published) release.
- **`cli-capability/stable-command-on-active-capability`** (error): Stable commands only expose active capabilities.
- **`profile/source-change-updates-traced-spec`** (error): Changes to bondstone's source update the capability specs the changed code implements.
- **`profile/source-change-has-proposal`** (warn): Changes to bondstone's source or library come with a change proposal.

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

## Guidance from `change`

- Before changing behaviour, create a proposal: `bondstone new change:Proposal --title "..." --set kind=feature`.
  It starts as `draft`; move it to `accepted` in a later change, after review.
- A proposal is `implemented` only when the living spec contains what it delivered.

## Guidance from `release`

- Plan a release with `bondstone new release:Release --title "..." --set version=X.Y.Z`.
- `CHANGELOG.md` is generated from releases and the proposals they include; never edit it.

## Guidance from `cli`

- Every command has a document in `docs/cli/`, and its implementation is tagged with
  `bondstone: CLI-<command>`. Adding or changing a command means updating its document.
- Changing a `stable` command's options, exit codes or JSON output is a breaking change.

## Guidance from `adr-capability`

- When a capability's behaviour depends on a decision, list it in `constrained_by`.
- When an ADR is superseded, move every `constrained_by` reference to the new ADR.

## Guidance from `change-capability`

- List the capabilities a proposal changes in `modifies`. Before setting it to `implemented`,
  write the requirements into those capability specs and list them in `delivers`.
