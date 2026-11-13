---
name: bondstone
description: Rules for this repository's living documentation, enforced by bondstone. Use before creating or editing documents in docs/adr/, docs/capabilities/, docs/discovery/experiments/, docs/discovery/opportunities/, docs/discovery/outcomes/, docs/discovery/solutions/, before changing code that carries `bondstone:` comments, and before finishing a task, to run `bondstone check`.
---

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
9. Never create `.bondstone/known.json`, add an entry to it or run `bondstone baseline --known` yourself: the file lists the violations a repository had when it adopted a rule, and it may only shrink. After you fix a known violation, run `bondstone baseline --known --prune`, which only removes entries.

Active packs and bridges: adr@1.0.0 (pack), ost@1.0.0 (pack), capability@1.0.0 (pack), ost-capability@1.0.0 (bridge), adr-capability@1.0.0 (bridge)

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

### `ost:Outcome`

A measurable outcome the product team is trying to move.

- location: `docs/discovery/outcomes/{id}-{slug}.md`
- id: `OUT-{n}`
- create: `bondstone new ost:Outcome --title "..." --set metric=...`
- fields: title (required), metric (required), target
- required sections: Why it matters
- status: active | achieved | dropped (new ones start as `active`)
- allowed status changes: active → achieved, dropped
- needs an `owner`

### `ost:Opportunity`

A customer need, pain point or desire, phrased from the customer's perspective.

- location: `docs/discovery/opportunities/{id}-{slug}.md`
- id: `OPP-{n}`
- create: `bondstone new ost:Opportunity --title "..." --set serves=...`
- fields: title (required), evidence
- required sections: Customer need
- status: open | pursuing | parked | closed (new ones start as `open`)
- allowed status changes: open → pursuing, parked, closed; pursuing → parked, closed; parked → open, pursuing, closed
- links: `serves` → ost:Outcome, ost:Opportunity (at least 1) (at most 1)

### `ost:Solution`

An idea that could address an opportunity.

- location: `docs/discovery/solutions/{id}-{slug}.md`
- id: `SOL-{n}`
- create: `bondstone new ost:Solution --title "..." --set addresses=...`
- fields: title (required)
- required sections: Idea, Assumptions
- status: idea | testing | committed | discarded (new ones start as `idea`)
- allowed status changes: idea → testing, committed, discarded; testing → committed, discarded, idea; committed → discarded
- links: `addresses` → ost:Opportunity (at least 1); `realized_by` → capability:Capability

### `ost:Experiment`

An assumption test for a solution.

- location: `docs/discovery/experiments/{id}-{slug}.md`
- id: `EXP-{n}`
- create: `bondstone new ost:Experiment --title "..." --set assumption=... --set success_criteria=... --set tests=...`
- fields: title (required), assumption (required), success_criteria (required)
- required sections: Method
- status: planned | running | concluded | abandoned (new ones start as `planned`)
- allowed status changes: planned → running, abandoned; running → concluded, abandoned
- links: `tests` → ost:Solution (at least 1) (at most 1)

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

- `intent`: ost:Opportunity
- `living-spec`: capability:Capability
- `decision`: adr:Decision

## Rules

Severities are the effective ones, after this repository's overrides.

- **`adr/alternatives-considered`** (warn): Accepted decisions record the alternatives that were considered. _Add a "## Alternatives considered" section._
- **`ost/concluded-experiment-has-result`** (error): A concluded experiment records its result and whether it met the success criteria. _Add a "## Result" section._
- **`ost/committed-solution-has-evidence`** (warn): A committed solution is backed by at least one concluded experiment.
- **`ost/active-outcome-has-opportunities`** (warn): An active outcome has at least one opportunity mapped under it.
- **`ost/no-solutions-for-closed-opportunities`** (error): Solutions in flight only address open or pursued opportunities.
- **`capability/requirement-has-scenario`** (error): Every requirement has at least one scenario. _Add '#### Scenario: <name>' with Given/When/Then lines._
- **`capability/requirement-uses-normative-language`** (error): Requirements use SHALL or MUST.
- **`capability/active-capability-has-requirements`** (error): An active capability lists at least one requirement.
- **`ost-capability/committed-solution-is-realized`** (error): A committed solution names the capability spec(s) that describe it. _Add `realized_by: [CAP-...]` and update that capability's requirements._
- **`ost-capability/realized-capability-is-not-draft`** (warn): A solution is only realized by capabilities that are active.
- **`ost-capability/capability-traces-to-discovery`** (warn): An active capability traces back to at least one committed solution.
- **`adr-capability/constrained-by-live-decision`** (error): Capabilities are constrained only by accepted or proposed decisions. _Point to the decision that superseded it._
- **`adr-capability/accepted-decision-is-applied`** (warn): An accepted decision constrains at least one capability (otherwise, is it still relevant?).
- **`profile/code-change-updates-living-spec`** (warn): Changes to app code come with an update to the living specs they implement.

The engine's own rules (`bondstone/...`) check structure: ids, fields, sections, links, code tags and stale views. `bondstone rules` lists them all.

## Generated files

`bondstone gen` writes these. Do not edit them.

- `docs/generated/decisions.md` (adr/decision-log)
- `docs/generated/opportunity-solution-tree.md` (ost/tree)
- `docs/generated/capabilities.md` (capability/index)
- `docs/generated/requirements.md` (capability/requirements)
- `docs/generated/outcome-to-capability.md` (ost-capability/outcome-to-capability)

## Guidance from `adr`

- Write an ADR when a change makes a decision that future readers would not understand
  from the code alone: a new dependency, a storage or protocol choice, a structural pattern.
- Once an ADR is accepted, do not edit it. Run `bondstone supersede ADR-xxx --title "..."`:
  it creates the successor, marks the old one `superseded` and moves links to the new one.
- Create ADRs as `proposed` and accept them in a later change.

## Guidance from `ost`

- Discovery lives in `docs/discovery/`: Outcome ← Opportunity (`serves`) ← Solution
  (`addresses`) ← Experiment (`tests`).
- Phrase opportunities as customer needs, not features.
- Do not mark a Solution `committed` without a concluded Experiment, unless the profile
  says otherwise.

## Guidance from `capability`

- `docs/capabilities/` describes what the system does **today**. When a change alters
  behaviour, update the affected capability in the same change; do not leave it for later.
- Add requirements as `### REQ-<CODE>-NNN: title` under `## Requirements`, never renumber
  existing ones, and remove requirements that no longer hold.
- Mark the code that implements a requirement with a comment `bondstone: REQ-<CODE>-NNN`.
- A requirement whose code arrives in the same change is active: write no `Status:` line.
  Write `Status: planned` under the heading only when the requirement has no code yet, and
  `Status: removed` when it no longer holds but its code is still there.

## Guidance from `ost-capability`

- When a Solution becomes `committed`, add `realized_by: [CAP-...]` and write or update the
  requirements in that capability spec before implementing.

## Guidance from `adr-capability`

- When a capability's behaviour depends on a decision, list it in `constrained_by`.
- When an ADR is superseded, move every `constrained_by` reference to the new ADR.
