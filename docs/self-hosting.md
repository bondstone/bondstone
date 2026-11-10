# Bondstone on bondstone: self-hosting profile

Status: phases 1–3 implemented · Applies to: this repository

This document designs the packs and bridges bondstone uses to document **itself**. The
goal is to dogfood every part of the engine on a real project and to find out what the
engine is missing.

## What bondstone needs to keep alive

| Knowledge | Today | Risk if it drifts |
|---|---|---|
| Why the engine works this way | `docs/design.md` (one long doc) | decisions get re-litigated |
| What each feature does today | code + README | agents re-implement or break behaviour |
| What is being changed and why | commit messages | no review point before code |
| What shipped in which version | git tags (none yet) | no changelog |
| CLI surface (commands, options, exit codes, JSON shape) | `--help` | breaking changes go unnoticed |
| Engine rule ids (`bondstone/immutable`, …) | string literals in `checks.py` | `explain` can't explain them; users can't override with confidence |
| Built-in packs and bridges | `pack.yaml` + fixtures | undocumented library, version drift |

## Overview

```text
                         adr-capability (existing)
   adr:Decision  <──────────── capability:Capability ──┬── capability:Requirement (items)
        ^ decided_by                ^ modifies        │          ^ delivers
        │                           │                 │          │
        └────── change:Proposal ────┴─────────────────┼──────────┘
                    ^ includes                        │
              release:Release                         │ implements
                                                      │
   cli:Command ───────────────────────────────────────┘
   library:Component  (one per built-in pack / bridge)
   engine:Rule        (items in docs/engine/rules.md)
```

| Component | Kind | Source | Status |
|---|---|---|---|
| `adr` | pack | built-in | exists |
| `capability` | pack | built-in | exists |
| `adr-capability` | bridge | built-in | exists |
| `change` | pack | built-in library (promoted in phase 3) | done |
| `release` | pack | built-in library (promoted in phase 3) | done |
| `change-capability` | bridge | `.bondstone/packs` | new, works with today's engine |
| `change-adr` | bridge | `.bondstone/packs` | new, works with today's engine |
| `release-change` | bridge | `.bondstone/packs` | new, works with today's engine |
| `cli` | pack | `.bondstone/packs` (bondstone-specific) | new, phase 2 |
| `cli-capability` | bridge | `.bondstone/packs` | new, phase 2 |
| `library` | pack | `.bondstone/packs` (bondstone-specific) | new, needs engine features |
| `engine` | pack | `.bondstone/packs` (bondstone-specific) | new, needs engine features |

`change` and `release` are generic. If they work here, they go into the built-in library;
`change` + `change-capability` is bondstone's own version of OpenSpec's "proposal → living
spec" flow. `cli`, `library` and `engine` stay local to this repository.

## Layout

```text
docs/
  adr/ADR-001-*.md                 adr:Decision
  capabilities/<area>.md           capability:Capability, requirements as items
  changes/CHG-001-*.md             change:Proposal
  releases/v0.2.0.md               release:Release
  cli/<command>.md                 cli:Command
  engine/rules.md                  engine:RuleCatalog, engine:Rule items
  generated/                       views (never edited)
src/bondstone/library/packs/<id>/README.md      library:Component
src/bondstone/library/bridges/<id>/README.md    library:Component
```

Initial capabilities, one per engine area: `profiles` (loading, versions, overrides,
waivers), `graph` (documents, types, items, links), `rules` (selectors, clauses, traits),
`diff-checks`, `code-traceability`, `views`, `scaffolding`, `agent-instructions`,
`pack-testing`. Each gets a short `code` (`PRF`, `GRA`, `RUL`, `DIF`, `TRC`, `VIE`, `SCF`,
`AGT`, `PKT`) for requirement ids.

## Pack: `change`

A proposal is reviewed before the code changes, and it can't be marked `implemented`
until the living spec says what it delivered. This is the step that keeps capability
specs current.

```yaml
id: change
version: 0.1.0
types:
  Proposal:
    id_format: "CHG-{n:03d}"
    id_pattern: "^CHG-\\d{3,}$"
    paths: ["docs/changes/*.md"]
    filename: "{id}-{slug}.md"
    fields:
      title: {type: string, minLength: 5}
      kind: {enum: [feature, fix, refactor, docs, breaking]}
    required_fields: [title, kind]
    sections: [Why, What changes, Out of scope]
    traits:
      lifecycle:
        statuses: [draft, accepted, implemented, rejected, withdrawn]
        initial: draft
        transitions:
          draft: [accepted, rejected, withdrawn]
          accepted: [implemented, withdrawn]
      owned: {}
      immutable: {when: [implemented, rejected, withdrawn]}
      indexed: {}
rules:
  - id: breaking-change-has-migration
    when: {type: Proposal, where: {kind: breaking}}
    require: [{section: Migration}]
views:
  - {id: open, title: Open proposals, output: docs/generated/changes-open.md,
     select: {type: Proposal, status: [draft, accepted]}, columns: [id, title, kind, status, owner]}
  - {id: done, title: Implemented proposals, output: docs/generated/changes-done.md,
     select: {type: Proposal, status: implemented}, columns: [id, title, kind]}
```

## Pack: `release`

```yaml
id: release
version: 0.1.0
types:
  Release:
    id_format: "v{version}"            # bondstone new release:Release --set version=0.2.0
    id_pattern: "^v\\d+\\.\\d+\\.\\d+$"
    paths: ["docs/releases/*.md"]
    filename: "{id}.md"
    fields:
      title: {type: string}
      date: {type: string, format: date}
    required_fields: [title]
    sections: [Highlights]
    traits:
      lifecycle:
        statuses: [planned, released]
        initial: planned
        transitions: {planned: [released]}
      immutable: {when: [released]}
      indexed: {}
rules:
  - id: released-has-date
    when: {type: Release, status: released}
    require: [{field: date}]
views:
  - {id: changelog, title: Changelog, output: CHANGELOG.md, render: tree,
     select: {type: Release}, levels: [{link: includes}]}
```

The changelog is a generated view, so it can't drift from the proposals.

## Bridges

### `change-capability`: the fold into the living spec

```yaml
requires: {change: "^0.1", capability: "^1"}
links:
  modifies: {from: change:Proposal, to: capability:Capability}
  delivers: {from: change:Proposal, to: capability:Requirement}
roles:
  change: [change:Proposal]
  living-spec: [capability:Capability]
rules:
  - id: accepted-proposal-names-capabilities
    when: {type: change:Proposal, status: [accepted, implemented], where: {kind: [feature, fix, breaking]}}
    require: [{link: modifies, min: 1}]
  - id: implemented-proposal-delivers-requirements
    description: The living spec contains what the proposal delivered.
    when: {type: change:Proposal, status: implemented, where: {kind: [feature, breaking]}}
    require: [{link: delivers, min: 1}]
  - id: delivered-requirements-belong-to-modified-capabilities
    when: {type: change:Proposal, status: implemented}
    require: [{link: delivers, all: true, to: {type: capability:Requirement}}]
```

`delivers` points at requirement **items** (`REQ-SCF-004`), and broken links are already
errors. So "implemented" can't be set until those requirement headings exist in the
capability spec. No new engine feature is needed for that.

### `change-adr`

```yaml
requires: {change: "^0.1", adr: "^1"}
links:
  decided_by: {from: change:Proposal, to: adr:Decision}
rules:
  - id: implemented-proposal-has-accepted-decisions
    when: {type: change:Proposal, status: implemented}
    require: [{link: decided_by, all: true, to: {type: adr:Decision, status: accepted}}]
```

### `release-change`

```yaml
requires: {release: "^0.1", change: "^0.1"}
links:
  includes: {from: release:Release, to: change:Proposal}
rules:
  - id: release-includes-only-implemented
    when: {type: release:Release}
    require: [{link: includes, all: true, to: {status: implemented}}]
  - id: implemented-proposal-is-released
    severity: warn
    when: {type: change:Proposal, status: implemented}
    require: [{incoming: includes, min: 1}]
```

## Pack: `cli` (phase 2)

One document per command in `docs/cli/<command>.md`, with id `CLI-<COMMAND>` (for example
`CLI-CHECK`, `CLI-SUPERSEDE`):

- fields: `title`, `synopsis`, `stability: {enum: [experimental, stable, deprecated]}`
- sections: `Options`, `Exit codes`, `Output`, `Examples`
- traits: `code-traceable: {coverage: error}`, so every command doc must be tagged in
  `cli.py` (`# bondstone: CLI-CHECK` above `cmd_check`)
- rule: `stable` commands with JSON output include a `JSON schema` section
- view: `docs/generated/cli-reference.md` (table: command, synopsis, stability)

Bridge `cli-capability`: `implements: {from: cli:Command, to: capability:Capability, min: 1}`.

## Pack: `library` (needs engine features)

A `README.md` next to every built-in `pack.yaml` / `bridge.yaml`, type `library:Component`,
id `PACK-<id>` / `BRIDGE-<id>`. Fields `kind` and `version`. Sections `Purpose`, `Types`,
`Rules`, `Example`. Link `requires` (bridge → packs). View: `docs/generated/library.md`.

The rules that matter here aren't expressible today: "`version` equals the manifest's
`version`" and "every manifest has a README". See engine features 1 and 2 below.

## Pack: `engine` (needs engine features)

`docs/engine/rules.md` lists every engine diagnostic as an item:
`### ENG-012: bondstone/immutable`, with *When it fires*, *Why*, *How to fix* and *Can be
overridden* sections. The `Rule` type is `code-traceable: {coverage: error}`, and every
`Diagnostic("bondstone/…")` in `checks.py` gets a `# bondstone: ENG-012` tag. After that,
`bondstone explain bondstone/immutable` can serve these docs (engine feature 3).

## Profile

```yaml
# .bondstone/profile.yaml (bondstone repository)
bondstone: 0.1
packs: [adr@1, capability@1, change@0.1, release@0.1, cli@0.1]
bridges: [adr-capability@1, change-capability@0.1, change-adr@0.1, release-change@0.1, cli-capability@0.1]
sources: [.bondstone/packs]
scan: ["docs/**/*.md"]
code:
  include: ["src/bondstone/**/*.py"]
  exclude: ["src/bondstone/library/**/fixtures/**"]

rules:
  - id: source-change-updates-traced-spec
    severity: error
    on_change: {paths: ["src/bondstone/**/*.py"]}
    require:
      - {changed: {role: living-spec}, traced: true, min: 1}
  - id: source-change-has-proposal
    severity: warn            # small fixes may skip a proposal
    on_change: {paths: ["src/bondstone/**/*.py", "src/bondstone/library/**"]}
    require:
      - {changed: {role: change}, min: 1}
  - id: library-change-has-fixtures
    on_change: {paths: ["src/bondstone/library/*/*/pack.yaml", "src/bondstone/library/*/*/bridge.yaml"]}
    require:
      - {changed: {type: library:Component}, min: 1}     # phase 3
```

`bondstone/status-initial` stays strict: new documents start as `proposed` / `draft` and
move on in a later change. The phase 1 bootstrap therefore takes three pushes, each
checked against the previous one: create everything in its initial status, then
accept and activate, then mark the bootstrap proposal implemented and plan a release.

CI runs `bondstone check --base origin/main` on every PR, alongside `pytest` and
`bondstone pack test`. A pre-commit hook runs `bondstone check`.

## Workflow for a change (example: lock file)

1. `bondstone new change:Proposal --title "Lock file for pack versions" --set kind=feature --set 'modifies=[CAP-profiles]'`
2. If it makes an architectural choice, `bondstone new adr:Decision …` and link it with `decided_by`.
3. Review, then set the proposal to `accepted`.
4. Implement. Add `### REQ-PRF-008: …` to `docs/capabilities/profiles.md` and tag the code with `# bondstone: REQ-PRF-008`.
5. Set `delivers: [REQ-PRF-008]` and `status: implemented`. The check fails if the requirement isn't in the spec yet.
6. At release time, `bondstone new release:Release --set version=0.2.0 --set 'includes=[CHG-…]'`, then `bondstone gen` updates `CHANGELOG.md`.

## Engine features this design needs

Ordered by value. Each one is useful well beyond bondstone itself.

| # | Feature | Needed by | Sketch |
|---|---|---|---|
| 1 | ~~**File-field clause**~~ (done in phase 3): compare a field with a value in another file | `library` | `require: [{file_field: {path: "{dir}/pack.yaml", key: version, equals: version}}]` |
| 2 | ~~**Existence rules**~~ (done in phase 3): every file matching a glob has a document | `library`, `cli` | top-level `expect: {for_each: "src/bondstone/library/*/*/pack.yaml", document: "{dir}/README.md", type: library:Component}` |
| 3 | ~~**`explain` for engine rules**~~ (done in phase 3) from a rule catalog | `engine` | `explain` falls back to `engine:Rule` items whose title is the rule id |
| 4 | ~~**`covered` selector**~~ (done in phase 2): node is tagged in code | `change-capability` | `to: {type: capability:Requirement, covered: true}`, so delivered requirements must be implemented |
| 5 | ~~**`id_format` placeholders from `--set`**~~ | `release` | done in phase 1: `v{version}` |
| 6 | **Views outside `docs/`** with a custom header | `release` (`CHANGELOG.md`) | already works; check the header renders well on GitHub |

Features 1 and 2 also unblock the portfolio idea, which checks repositories against
manifests. Feature 4 turns `traced` diff rules and `delivers` into a full chain: proposal →
requirement → code.

## Phasing

1. **Phase 1, today's engine.** `adr` + `capability` + `adr-capability`, plus local packs `change`
   and `release` with their three bridges. Write the nine capability specs for current
   behaviour and tag the code. Backfill ADRs for the decisions in `design.md`: Markdown +
   frontmatter, no core types, bridges own links, traits vs roles, deterministic gate.
2. **Phase 2.** `cli` + `cli-capability`; engine features 4 and 5.
3. **Phase 3.** Engine features 1–3; `library` and `engine` packs; promote `change`, `release`
   and their bridges into the built-in library with fixtures.

## What not to model

Some invariants are better as tests than as documentation rules. Example: "every argparse
subcommand has a `cli:Command` doc" is one `pytest` that introspects `build_parser()`. Use
bondstone for knowledge people and agents read and change. Use tests for facts the code can
check about itself.
