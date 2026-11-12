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

Active packs, bridges and presets: adr@1.0.0 (pack), capability@1.0.0 (pack), speckit@1.0.0 (pack), cli@1.0.0 (pack), release@1.0.0 (pack), adr-capability@1.0.0 (bridge), speckit-capability@1.0.0 (bridge), speckit-adr@1.0.0 (bridge), cli-capability@1.0.0 (bridge), release-speckit@1.0.0 (bridge), starter@1.0.0 (preset), starter-speckit@1.0.0 (preset)

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
- immutable once accepted, rejected, deprecated, superseded: only status, owner may change; supersede it instead of editing it
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

### `speckit:Feature`

One change planned with Spec Kit: the folder `specs/NNN-name/` with `spec.md`, `plan.md` and `tasks.md`. `spec.md` starts with a frontmatter block that names the feature; Spec Kit's commands write everything else.

- location: `specs/{id}/spec.md`
- id: `{n:03d}-{slug}`
- create: `bondstone new speckit:Feature --title "..."`
- fields: title (required)
- status: taken from the files in the document's folder, never written in frontmatter; the first that holds: `implemented` when every task in `tasks.md` is ticked; `planned` when `plan.md` exists; `specified` when `spec.md` exists
- links: `modifies` → capability:Capability; `delivers` → capability:Requirement; `decided_by` → adr:Decision

### `cli:Command`

One command of a command-line tool: a subcommand, or a nested one such as `profile check`. The document is the reference for that command.

- location: `docs/cli/{slug}.md`
- id: `CLI-{slug}`
- create: `bondstone new cli:Command --title "..." --set synopsis=...`
- fields: title (required), synopsis (required), json_output
- required sections: Options, Exit codes, Examples
- status: experimental | stable | deprecated (new ones start as `experimental`)
- allowed status changes: experimental → stable, deprecated; stable → deprecated
- tag the code that implements it with a comment `bondstone: <ID>`
- links: `implements` → capability:Capability

### `release:Release`

One version of the product, planned or published.

- location: `docs/releases/{id}.md`
- id: `v{version}`
- create: `bondstone new release:Release --title "..." --set version=...`
- fields: title (required), version (required), date
- required sections: Highlights
- status: planned | released (new ones start as `planned`)
- allowed status changes: planned → released
- immutable once released: only status may change; supersede it instead of editing it
- links: `includes` → speckit:Feature

## Roles

Rules name roles so that they work across packs.

- `decision`: adr:Decision
- `living-spec`: capability:Capability
- `change`: speckit:Feature
- `interface`: cli:Command

## Rules

Severities are the effective ones, after this repository's overrides.

- **`adr/alternatives-considered`** (warn): Accepted decisions record the alternatives that were considered. _Add a "## Alternatives considered" section._
- **`capability/requirement-has-scenario`** (error): Every requirement has at least one scenario. _Add '#### Scenario: <name>' with Given/When/Then lines._
- **`capability/requirement-uses-normative-language`** (error): Requirements use SHALL or MUST.
- **`capability/active-capability-has-requirements`** (error): An active capability lists at least one requirement.
- **`cli/stable-command-is-implemented`** (error): A stable command is tagged in the code that implements it. _Tag the command's handler or its parser with `bondstone: {id}`._
- **`cli/json-output-is-documented`** (error): A stable command with JSON output documents its shape. _Add a "## JSON output" section with an example._
- **`release/released-has-date`** (error): A released version records the day it was published. _Add `date:` before the release is marked as released._
- **`adr-capability/constrained-by-live-decision`** (error): Capabilities are constrained only by accepted or proposed decisions. _Point to the decision that superseded it._
- **`adr-capability/accepted-decision-is-applied`** (warn): An accepted decision constrains at least one capability (otherwise, is it still relevant?).
- **`speckit-capability/implemented-feature-delivers-covered-requirements`** (error): An implemented feature delivers only requirements that are active and tagged in code. _Tag the code with `bondstone: REQ-...`, and remove `Status: planned` from the requirement with `bondstone status REQ-... active`._
- **`speckit-capability/implemented-feature-is-folded-in`** (warn): An implemented feature names the capabilities it modifies or the requirements it delivers. _List the capabilities under `modifies` or the requirements under `delivers` in the frontmatter of spec.md._
- **`speckit-adr/implemented-feature-rests-on-accepted-decisions`** (error): An implemented feature rests only on accepted decisions. _Accept the decision with `bondstone status ADR-... accepted` before the last task is ticked, or point to the decision that replaced it._
- **`cli-capability/stable-command-implements-capability`** (error): A stable command implements at least one capability. _List the capabilities the command exposes under `implements`._
- **`cli-capability/stable-command-on-active-capability`** (error): A stable command exposes only active capabilities. _Activate the capability, or keep the command experimental until it is._
- **`release-speckit/release-includes-only-implemented`** (error): A released version includes only implemented features. _Finish the feature's tasks, or move the feature to the next release._
- **`release-speckit/implemented-feature-is-released`** (warn): An implemented feature is part of a planned or published release. _List the feature under `includes` in the release it ships with._
- **`starter/code-change-updates-living-spec`** (error): A change to code updates the living specs that code implements. _Update the capability, or add the commit trailer "Spec-Impact: none (<reason>)" when no behaviour changed._
- **`starter-speckit/source-change-has-feature`** (error): A change to code comes with a Spec Kit feature. _Plan the change as a feature under specs/ (`/speckit.specify`), or tick the tasks of the feature it belongs to. A change with no effect on behaviour may carry the commit trailer "Spec-Impact: none (<reason>)"._

The engine's own rules (`bondstone/...`) check structure: ids, fields, sections, links, code tags and stale views. `bondstone rules` lists them all.

## Generated files

`bondstone gen` writes these. Do not edit them.

- `docs/generated/decisions.md` (adr/decision-log)
- `docs/generated/capabilities.md` (capability/index)
- `docs/generated/requirements.md` (capability/requirements)
- `docs/generated/features.md` (speckit/features)
- `docs/generated/cli-reference.md` (cli/reference)
- `CHANGELOG.md` (release/changelog)
- `docs/generated/delivery.md` (speckit-capability/delivery)
- `docs/generated/feature-decisions.md` (speckit-adr/decisions-by-feature)
- `docs/generated/commands-by-capability.md` (cli-capability/commands-by-capability)
- `docs/generated/release-contents.md` (release-speckit/release-contents)
- `docs/generated/decisions-applied.md` (profile/decisions-applied)
- `docs/generated/decision-usage.md` (profile/decision-usage)

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

## Guidance from `speckit`

- Plan a change as a Spec Kit feature: `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`,
  then `/speckit.implement`. Each feature is a folder `specs/NNN-name/`. Do not create one
  with `bondstone new`; Spec Kit's commands number the folder and write the files.
- `spec.md` starts with a frontmatter block: `id` is the folder's name, `type` is
  `speckit:Feature`, `title` is the feature's name. Keep the block at the top of the file.
- A feature has no `status` field. It is `specified` when `spec.md` exists, `planned` when
  `plan.md` exists, and `implemented` when every task in `tasks.md` is ticked. Tick a task
  only when it is done: rules for implemented features apply from the last tick.

## Guidance from `cli`

- Every command of the command-line tool has a document in `docs/cli/`. When you add, change
  or remove an option, update that command's document in the same change.
- Tag the code that defines or handles a command with a comment `bondstone: CLI-<name>`.
- A new command starts as `experimental`. Move it to `stable` with
  `bondstone status CLI-<name> stable` once its interface is meant to stay.

## Guidance from `release`

- A version is planned in `docs/releases/v<version>.md` before it ships. Create it with
  `bondstone new release:Release --title "..." --set version=1.2.0`.
- When the version is published, add `date:` and run `bondstone status v<version> released`.
  A released document can no longer be edited.
- `CHANGELOG.md` is generated from the release documents. Never edit it.

## Guidance from `adr-capability`

- When a capability's behaviour depends on a decision, list it in `constrained_by`.
- When an ADR is superseded, move every `constrained_by` reference to the new ADR.

## Guidance from `speckit-capability`

- A feature is the record of one change; the capabilities are what stays true afterwards.
  When a feature changes behaviour, update the capability in the same change and list it
  under `modifies` in the feature's frontmatter.
- A requirement the feature will implement is added to its capability with `Status: planned`
  and listed under `delivers`. When the code is there and tagged, run
  `bondstone status REQ-... active`.
- Before you tick the last task of a feature, check that every requirement under `delivers`
  is active and tagged in code: from that tick on the feature is `implemented`.

## Guidance from `speckit-adr`

- When planning a feature makes a decision that deserves an ADR, write the ADR and list it
  under `decided_by` in the feature's frontmatter.
- A decision a feature rests on must be accepted before the feature's last task is ticked.

## Guidance from `cli-capability`

- List the capabilities a command exposes under `implements` in its document.
- A command becomes `stable` only when every capability it implements is `active`.

## Guidance from `release-speckit`

- List every feature a version ships under `includes` in its release document.
- A version is marked `released` only when every feature it includes is implemented.

## Guidance from `starter`

- Code is traced to requirements by `bondstone: REQ-...` comments. When you change code under
  such a comment, update the capability that holds the requirement in the same change.
  `bondstone context --for <paths>` lists the capabilities a file is traced to.
- A change that alters no behaviour, such as a rename or a reformat, may carry the commit
  trailer `Spec-Impact: none (<reason>)` instead. Add it only when the user asks for it.

## Guidance from `starter-speckit`

- Every change to code belongs to a Spec Kit feature under `specs/`. Start one with
  `/speckit.specify` before you write code, or continue the feature the change belongs to and
  tick its tasks as you finish them.
