# Bondstone — design

Status: POC · Branch: `POC`

Bondstone is a CLI that enforces a repository's **living documentation** — decisions,
capabilities, discovery artifacts, architecture — against rules that are themselves
stored in the repository. It is meant to be run by coding agents (to validate their own
work), by git hooks, and by CI.

## Problems it addresses

1. **No living doc.** Spec-driven tools produce per-change artifacts that are written once
   and never folded back into a description of what is true today.
2. **Loose format and links.** Documents reference each other with free-text links that
   nothing validates; required content is a convention, not a check.

## Principles

- **The engine knows no methodology.** It never mentions "ADR" or "TOGAF". It loads
  documents into a typed graph and evaluates rules.
- **Methods are packs.** A pack defines document types, fields, sections, links,
  lifecycles, rules, views, templates and agent instructions for one method
  (ADR, Opportunity Solution Tree, TOGAF-lite, …).
- **Packs never know about each other.** Everything that connects two packs lives in a
  **bridge**: cross-pack link types, hand-off rules, cross-pack views, role assignments.
- **No shared ontology.** There are no abstract "core types". Generic behaviour comes from
  **traits** (mechanical, engine-defined) and generic meaning from **roles** (assigned by
  bridges or profiles, where packs are combined).
- **Deterministic gate.** `bondstone check` is deterministic. LLM-based quality review, if
  any, is a separate, non-blocking concern.
- **Agent-first ergonomics.** Machine-readable output, rule explanations, scaffolding and
  generated agent instructions, so agents get it right the first time.

## Concepts

### Documents and nodes

A document is a Markdown file with YAML frontmatter. Its type comes from the type's
`paths` globs or from an explicit `type:` key (`type: adr:Decision`). Each document is
one **node**; a type may also declare **items** — headings inside the document that
become child nodes (e.g. requirements inside a capability spec), linked to their parent
with the built-in `bondstone:part_of` link.

```markdown
---
id: ADR-002
title: Store habits locally with SQLite
status: accepted
owner: dawid
date: 2026-11-09
supersedes: ADR-001
---
## Context
...
```

Reserved frontmatter keys: `id`, `type`. Trait keys: `status` (lifecycle), `owner`
(owned). Any other key must be either a declared field or a link name; unknown keys are
errors (strict by default; a type may set `additional_fields: true`).

### Packs (`pack.yaml`)

```yaml
id: adr
version: 1.0.0
types:
  Decision:
    id_format: "ADR-{n:03d}"         # used by `bondstone new`
    id_pattern: "^ADR-\\d{3,}$"
    paths: ["docs/adr/*.md"]
    dir: docs/adr
    filename: "{id}-{slug}.md"
    template: templates/decision.md
    fields:                           # JSON Schema properties for frontmatter
      title: {type: string, minLength: 3}
      date: {type: string, format: date}
    required_fields: [title, date]
    sections: [Context, Decision, Consequences]
    traits:
      lifecycle:
        statuses: [proposed, accepted, rejected, deprecated, superseded]
        initial: proposed
        transitions: {proposed: [accepted, rejected], accepted: [deprecated, superseded]}
      owned: {}
      supersedable: {link: supersedes}
      immutable: {when: [accepted], allow_fields: [status]}
      indexed: {}
links:
  supersedes: {from: Decision, to: Decision, max: 1}
rules: [...]
views: [...]
instructions: instructions.md
```

Inside a pack, type names are unqualified; everywhere else they are qualified
(`adr:Decision`). Rule ids are qualified as `<owner>/<id>` (`adr/…`, `ost-capability/…`,
`profile/…`, engine rules `bondstone/…`).

### Bridges (`bridge.yaml`)

A bridge depends on two or more packs and owns what connects them.

```yaml
id: ost-capability
version: 1.0.0
requires: {ost: "^1", capability: "^1"}
links:
  realized_by: {from: ost:Solution, to: capability:Capability}
roles:
  living-spec: [capability:Capability]
rules:
  - id: committed-solution-is-realized
    when: {type: ost:Solution, status: committed}
    require: [{link: realized_by, min: 1}]
views: [...]
```

### Profiles (`.bondstone/profile.yaml`)

What a repository actually uses.

```yaml
bondstone: 0.1
packs: [adr@1, ost@1, capability@1]
bridges: [ost-capability@1, adr-capability@1]
sources: [.bondstone/packs]          # extra pack/bridge directories (searched first)
scan: ["docs/**/*.md"]                # files that may declare `type:` explicitly
roles: {}                             # extra role assignments
code: {include: ["src/**/*"], exclude: []}
overrides:
  ost/committed-solution-has-evidence: {severity: off}
waivers:
  - {rule: adr-capability/accepted-decision-is-applied, node: ADR-001,
     reason: "org-wide decision", expires: 2027-01-01}
rules: [...]                          # profile-level rules (incl. diff rules)
```

Version specs: `adr@1` = any 1.x; `adr@1.2` = `>=1.2,<2`. Bridges use PEP 440-style or
caret ranges (`^1`). Pack resolution order: profile `sources`, then the built-in library.

### Traits (engine-defined, mechanical)

| Trait | Config | Enforced |
|---|---|---|
| `lifecycle` | `statuses`, `initial`, `transitions`, `create_as` | `status` present and valid; with `--base`, status changes follow `transitions` and new documents start in `create_as` (default: `initial`) |
| `owned` | – | `owner` present |
| `supersedable` | `link` | a superseded target has status `superseded`; superseded at most once; no cycles |
| `immutable` | `when`, `allow_fields` | with `--base`, a node whose previous status is in `when` may only change `allow_fields` |
| `code-traceable` | `coverage: off\|warn\|error` | code may reference it via `bondstone: ID`; uncovered nodes reported |
| `indexed` | – | node appears in generic views (`select: {trait: indexed}`) |

Traits carry no domain meaning, so packs can adopt them without agreeing on a model.

### Roles

Roles are names (`living-spec`, `decision`, `change`, …) mapped to types by **bridges or
the profile** — never by packs. Rules and views can select by role, so a generic rule
("code changes require a living-spec update") works for any combination of packs.

### Rules

```yaml
- id: concluded-experiment-has-result
  description: A concluded experiment records its result.
  severity: error            # error | warn
  locked: false              # true: profiles may not loosen it
  when: {type: Experiment, status: concluded}
  require:
    - section: Result
  hint: Add a "## Result" section.
```

Selectors (`when`, `to`, `from`) combine with AND: `type`, `role`, `trait`, `status`,
`where: {field: value}`, `covered: true|false` (tagged in code). Requirement clauses:

| Clause | Meaning |
|---|---|
| `link: NAME, to: SEL, min: N` | at least N outgoing NAME links to nodes matching SEL |
| `link: NAME, to: SEL, all: true` | every outgoing NAME link targets a node matching SEL |
| `incoming: NAME, from: SEL, min: N` | at least N incoming NAME links |
| `field: NAME` | field present and non-empty |
| `section: TITLE` | heading present |
| `contains: REGEX` | node body matches |
| `file_field: {path, key, equals \| value}` | a value in a YAML/JSON file (path built from `{dir}` and fields, dotted `key`) equals a field or a literal |
| `changed: SEL, min: N` | (diff rules) N changed nodes match SEL |
| `exists: SEL, min: N` | (diff rules) N nodes match SEL, changed or not |
| `any: [clause, ...]` | at least one alternative passes (node and diff rules; no `traced` inside) |
| `changed: SEL, traced: true` | (diff rules) every document matching SEL that is tagged in a changed code region must change; a tag's region is the block of code below it; untagged code falls back to `min` |

Diff rules use `on_change: {paths: [globs]}` instead of `when` and only run with
`bondstone check --base REF`.

Existence rules use `for_each: {glob, document, type}` instead of `when`: every file
matching the glob must have a document of the type at `document` (built from `{dir}`,
`{name}` and `{path}` of the file).

Engine rules (`bondstone/...`) are documented in `src/bondstone/engine_rules.md`, which
ships with the package; `bondstone explain bondstone/<rule>` reads it.

### Views

Generated Markdown, never hand-edited. `bondstone gen` writes them; `bondstone check`
fails when one is stale.

```yaml
views:
  - id: decision-log
    title: Decision log
    output: docs/generated/decisions.md
    render: table                     # table | tree
    select: {type: Decision}
    columns: [id, title, status, date]
```

`tree` views walk links from root nodes: `children: [{incoming: addresses}, {link: realized_by}]`.

### Code traceability

Code references nodes with tags such as `# bondstone: REQ-HAB-001, REQ-HAB-002`.
Unknown ids and ids of types without `code-traceable` are errors; uncovered
`code-traceable` nodes are reported per the trait's `coverage`.

### Overrides and waivers

Profiles may change a rule's severity (`error`, `warn`, `off`) unless the rule is
`locked`. Waivers silence one rule for one node and require a `reason`; an `expires`
date in the past turns the waiver into an error.

## CLI

| Command | Purpose |
|---|---|
| `bondstone init --packs adr,ost` | create `.bondstone/profile.yaml` and generate views |
| `bondstone check [--base REF] [--format json] [--fail-on warn]` | validate everything; exit 1 on failure |
| `bondstone gen` | regenerate views |
| `bondstone new TYPE --title T [--set k=v]` | scaffold a valid document with the next id |
| `bondstone baseline [REF]` | record the adoption commit for diff checks |
| `bondstone supersede ID --title T [--no-repoint]` | create a successor, mark the old one superseded, move incoming links (skipping immutable sources), regenerate views |
| `bondstone profile check` | validate the profile itself: versions, bridges, references, unbridged packs |
| `bondstone rules` / `bondstone explain RULE` | list / explain active rules |
| `bondstone agent [--output FILE]` | generate agent instructions from the active profile |
| `bondstone graph` | export the graph as JSON (basis for portfolio aggregation) |
| `bondstone pack test DIR` | run a pack's or bridge's fixtures |

Text output is `path:line: severity rule: message`; JSON output carries the same plus
`node` and `hint`.

## Pack testing

A pack or bridge ships `fixtures/<case>/` directories, each a small repository with its
own `.bondstone/profile.yaml` and an `expected.yaml`:

```yaml
errors: [ost/committed-solution-is-realized]
warnings: []
```

`bondstone pack test` runs `check` on every case and compares the rule ids found.

## Integrations

- **Git hooks / CI:** `bondstone check --base origin/main --format json`.
- **Agents:** `bondstone agent --output AGENTS.bondstone.md`, then reference it from
  `AGENTS.md`/`CLAUDE.md`; agents run `bondstone new` and `bondstone check`.
- **Spec Kit (planned):** an adapter pack that parses `specs/NNN-*/` without frontmatter,
  bridges to living-spec packs, and a Spec Kit extension using `after_specify`,
  `after_plan` and `after_implement` hooks. CI remains the hard gate.

## POC scope

In: engine, traits, roles, rules, diff rules (`--base`), views, overrides, waivers,
code tags, scaffolding, agent instructions, pack tests; packs `adr`, `ost`,
`capability`; bridges `ost-capability`, `adr-capability`; an example project.

### Baseline

When bondstone is adopted in an existing repository, or a long-lived branch is merged,
every document looks new against the target branch. `bondstone baseline [REF]` records a
commit in the profile (`baseline: '<sha>'`); a document missing at the base but present
at the baseline is compared with its baseline version (transitions, immutability)
instead of being treated as new. Move the baseline forward when merging a long-lived
branch. CI needs full history (`fetch-depth: 0`).

Renames are followed when comparing with `--base` (git rename detection, or a deleted
file at the base with the same id).

Out (roadmap): lock file and pack migrations; remote (git/URL) pack sources; cross-repo
references and portfolio aggregation; Spec Kit / OpenSpec adapters; `--fix`;
incremental checking; TOGAF-lite and portfolio packs.
