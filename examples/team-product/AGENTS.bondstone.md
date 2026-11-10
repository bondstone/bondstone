<!-- bondstone:generated agent instructions; run `bondstone agent` to refresh -->
# Documentation rules (bondstone)

This repository's living documentation is validated by `bondstone`. Before finishing any task:

1. Create new documents with `bondstone new <Type> --title "..."` instead of by hand.
2. Keep frontmatter links (ids, not paths) accurate. To replace a document, run
   `bondstone supersede <ID> --title "..."` instead of editing it.
3. Run `bondstone gen` to refresh generated views.
4. Run `bondstone check --format json` (add `--base origin/main` on branches) and fix every error.
5. Never weaken `.bondstone/profile.yaml` (overrides, waivers) to make a check pass; ask instead.

Active packs and bridges: adr@1.0.0 (pack), ost@1.0.0 (pack), togaf-lite@0.1.0 (pack), ost-togaf-lite@0.1.0 (bridge), adr-togaf-lite@0.1.0 (bridge)

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

### `ost:Outcome`
A measurable outcome the product team is trying to move.
- location: `docs/discovery/outcomes/*.md`
- id: `^OUT-\d+$`
- required fields: title, metric
- required sections: Why it matters
- status: active | achieved | dropped
- transitions: active → achieved, dropped
- requires `owner`

### `ost:Opportunity`
A customer need, pain point or desire, phrased from the customer's perspective.
- location: `docs/discovery/opportunities/*.md`
- id: `^OPP-\d+$`
- required fields: title
- required sections: Customer need
- status: open | pursuing | parked | closed
- transitions: open → pursuing, parked, closed; pursuing → parked, closed; parked → open, pursuing, closed
- links: `serves` → ost:Outcome, ost:Opportunity (min 1) (max 1)

### `ost:Solution`
An idea that could address an opportunity.
- location: `docs/discovery/solutions/*.md`
- id: `^SOL-\d+$`
- required fields: title
- required sections: Idea, Assumptions
- status: idea | testing | committed | discarded
- transitions: idea → testing, committed, discarded; testing → committed, discarded, idea; committed → discarded
- links: `addresses` → ost:Opportunity (min 1); `specified_by` → togaf-lite:Requirement

### `ost:Experiment`
An assumption test for a solution.
- location: `docs/discovery/experiments/*.md`
- id: `^EXP-\d+$`
- required fields: title, assumption, success_criteria
- required sections: Method
- status: planned | running | concluded | abandoned
- transitions: planned → running, abandoned; running → concluded, abandoned
- links: `tests` → ost:Solution (min 1) (max 1)

### `togaf-lite:Principle`
A lasting rule that guides architecture choices.
- location: `docs/architecture/principles/*.md`
- id: `^PRIN-\d{2,}$`
- required fields: title
- required sections: Statement, Rationale, Implications
- status: draft | approved | retired
- transitions: draft → approved; approved → retired
- requires `owner`

### `togaf-lite:Requirement`
An architecture requirement - a function the system must offer, a quality it must have, or a constraint it must respect.
- location: `docs/architecture/requirements/*.md`
- id: `^AREQ-\d{3,}$`
- required fields: title, kind, priority
- required sections: Statement, Fit criterion
- status: draft | approved | satisfied | withdrawn
- transitions: draft → approved, withdrawn; approved → satisfied, withdrawn; satisfied → approved, withdrawn
- requires `owner`
- links: `motivated_by` → togaf-lite:Principle

### `togaf-lite:ArchitectureBlock`
What the architecture needs, independent of product or vendor (a TOGAF architecture building block).
- location: `docs/architecture/architecture-blocks/*.md`
- id: `^ABB-[a-z0-9]+(-[a-z0-9]+)*$`
- required fields: title, layer
- required sections: Responsibility, Interfaces
- status: draft | approved | retired
- transitions: draft → approved; approved → retired
- requires `owner`
- links: `satisfies` → togaf-lite:Requirement; `constrained_by` → adr:Decision

### `togaf-lite:SolutionBlock`
The concrete component that implements an architecture block (a TOGAF solution building block). Its code is tagged with its id.
- location: `docs/architecture/solution-blocks/*.md`
- id: `^SBB-[a-z0-9]+(-[a-z0-9]+)*$`
- required fields: title
- required sections: Responsibility, Interfaces, Operations
- status: planned | live | retiring | retired | cancelled
- transitions: planned → live, cancelled; live → retiring; retiring → retired
- requires `owner`
- reference it from code with a `bondstone: <id>` comment
- links: `realizes` → togaf-lite:ArchitectureBlock (min 1); `depends_on` → togaf-lite:SolutionBlock; `constrained_by` → adr:Decision

### `togaf-lite:WorkPackage`
A unit of change that creates or alters solution blocks.
- location: `docs/architecture/work-packages/*.md`
- id: `^WP-\d{3,}$`
- required fields: title
- required sections: Scope, Expected result
- status: planned | in-progress | done | cancelled
- transitions: planned → in-progress, cancelled; in-progress → done, cancelled
- requires `owner`
- immutable once done, cancelled: supersede instead of editing
- links: `delivers` → togaf-lite:SolutionBlock (min 1)

## Roles

- `intent`: ost:Opportunity
- `decision`: adr:Decision
- `living-spec`: togaf-lite:SolutionBlock

## Rules

- **`adr/alternatives-considered`** (warn): Accepted decisions record the alternatives that were considered. — _Add a "## Alternatives considered" section._
- **`ost/concluded-experiment-has-result`** (error): A concluded experiment records its result and whether it met the success criteria. — _Add a "## Result" section._
- **`ost/committed-solution-has-evidence`** (warn): A committed solution is backed by at least one concluded experiment.
- **`ost/active-outcome-has-opportunities`** (warn): An active outcome has at least one opportunity mapped under it.
- **`ost/no-solutions-for-closed-opportunities`** (error): Solutions in flight only address open or pursued opportunities.
- **`togaf-lite/approved-requirement-is-motivated`** (warn): An approved requirement follows from at least one approved principle. — _Add `motivated_by: [PRIN-NN]`._
- **`togaf-lite/satisfied-requirement-has-approved-block`** (error): A requirement marked satisfied is satisfied by an approved architecture block. — _Add `satisfies: [AREQ-NNN]` to the architecture block, or move the requirement back to approved._
- **`togaf-lite/approved-block-is-realized`** (warn): An approved architecture block is realized by a planned or running solution block. — _bondstone new togaf-lite:SolutionBlock --title '...' --set 'realizes=[ABB-...]'_
- **`togaf-lite/live-solution-realizes-approved-block`** (error): A live solution block only realizes approved architecture blocks. — _Approve the architecture block first, or point at the block that replaced it._
- **`togaf-lite/no-dependency-on-retired-blocks`** (error): A live solution block does not depend on retired or cancelled blocks.
- **`togaf-lite/done-work-package-delivered`** (error): A work package is done only when every block it delivers has gone live.
- **`ost-togaf-lite/committed-solution-is-specified`** (error): A committed solution is specified by at least one architecture requirement. — _bondstone new togaf-lite:Requirement --title '...' --set kind=functional --set priority=must, then add `specified_by: [AREQ-NNN]`._
- **`ost-togaf-lite/specified-by-agreed-requirements`** (warn): A committed solution is only specified by approved or satisfied requirements.
- **`ost-togaf-lite/functional-requirement-traces-to-discovery`** (warn): An approved functional requirement comes from a committed solution. — _Add `specified_by: [AREQ-NNN]` to the solution this requirement came from._
- **`adr-togaf-lite/constrained-by-live-decision`** (error): Building blocks are constrained only by proposed or accepted decisions. — _Point to the decision that superseded it._
- **`adr-togaf-lite/live-solution-block-has-decision`** (warn): A live solution block is backed by at least one accepted decision. — _bondstone new adr:Decision --title '...', then add `constrained_by: [ADR-NNN]`._
- **`profile/service-change-updates-solution-block`** (error): Changes to a service come with an update to the solution block that service implements.

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

## Guidance from `togaf-lite`

- Architecture is described in two layers: an `ArchitectureBlock` says what is needed, a
  `SolutionBlock` says what is built. Every solution block `realizes` at least one
  architecture block.
- Tag the code of a solution block with `bondstone: SBB-<name>` at the top of its entry
  module. When that code changes, update the solution block document in the same change.
- A requirement becomes `satisfied` only after an approved architecture block lists it
  under `satisfies`. Do not mark it satisfied because the code exists.
- Create documents as `draft` / `planned` and move them on in a later change.

## Guidance from `ost-togaf-lite`

- When a Solution becomes `committed`, write the architecture requirements it needs and
  list them under `specified_by: [AREQ-...]` before any building block is designed.
- A functional requirement that no committed solution points at needs a reason to exist:
  link it, or withdraw it.

## Guidance from `adr-togaf-lite`

- A new solution block, or a change of its technology, needs a decision: write the ADR
  and list it under the block's `constrained_by`.
- Links to decisions live on the building block, because accepted decisions cannot be edited.
