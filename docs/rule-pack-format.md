# Rule-pack format

Two file kinds: a **project file** (`bondstone.yaml`, one per repository) and
**pack files** (`pack.yaml`, one per pack). Both have JSON Schemas in
[`schema/`](../schema/), and every file in [`examples/`](../examples/) validates
against them.

## 1. Document model

A **document** is a Markdown file with YAML frontmatter. Every document has:

- an `id` in frontmatter, unique in the repository and never reused;
- exactly one **type**, decided by which type's `path` pattern the file matches
  (matching two types, or none inside a scanned folder, is an error);
- **fields** (the rest of the frontmatter), **sections** (its headings), and
  **links** (frontmatter keys whose values are lists of ids).

A document may contain **items**: sub-nodes introduced by a heading such as
`### REQ-REM-001: Remind at the chosen time`. Items have an id and a title, and can
be the target of links and code tags.

Type names are namespaced by pack: `adr/decision`, `ost/solution`. Inside its own
pack a type is referred to by its short name.

```markdown
---
id: ADR-0003
title: Store habits locally with SQLite
status: accepted
date: 2026-11-02
supersedes: [ADR-0001]
---
## Context
...
```

## 2. Project file: `bondstone.yaml`

```yaml
bondstone: 1                  # format version
profile: solo                 # severity profile; packs define what it means
packs:
  - source: ./packs/adr                               # a folder in this repository
  - source: github.com/acme/bondstone-packs//ost@v1.2.0   # git repo // subfolder @ tag
docs: ["docs/**/*.md"]        # folders bondstone owns; unknown files here are errors
code: ["lib/**", "test/**"]   # where anchors and code tags are resolved
overrides:                    # change a rule's severity: error | warn | advisory | ignore
  adr/decision-states-alternatives: warn
rules: []                     # repository-local rules, same grammar as pack rules
waivers:
  - rule: solo-app/requirement-is-tagged
    target: REQ-REM-004
    reason: Covered by a manual test until the notification mock lands.
    expires: 2027-01-31       # a waiver without an expiry date is invalid
baseline: .bondstone/baseline.json   # violations that existed at adoption time
```

Remote packs are pinned in `bondstone.lock` (resolved commit and content hash), so
CI and agents always check against the same rules.

## 3. Pack file: `pack.yaml`

```yaml
pack: adr                 # name, and the namespace of everything it defines
version: 1.0.0
bondstone: ">=0.1"        # engine versions this pack works with
description: Architecture decision records.
requires: {}              # other packs: {name: version range}

types: {}                 # section 3.1
links: {}                 # section 3.2
rules: []                 # section 3.3
views: []                 # section 3.4
profiles: {}              # section 3.5
agent: {guidance: agent.md}   # prose added to generated agent instructions
```

A **bridge** is a pack with `requires` and no `types`: it adds links, rules and
views between types owned by other packs. Packs never reference each other
directly unless they `require` each other, so `ost` and `togaf-lite` stay
independent and `ost-togaf` holds everything that connects them.

### 3.1 Types

```yaml
types:
  decision:
    description: One architecture decision.
    path: "docs/adr/{id}-{slug}.md"
    id: "ADR-{seq:4}"                 # {seq:N} = next number, zero-padded to N
    frontmatter:                      # JSON Schema (2020-12) for the frontmatter
      required: [title, status, date]
      properties:
        title: {type: string, minLength: 5}
        date: {type: string, format: date}
    sections:                         # required, in this order
      - heading: Context
        min_words: 15
      - heading: Decision
      - heading: Alternatives considered
      - heading: Consequences
      - heading: Notes
        optional: true
    extra_sections: forbid            # allow | forbid
    lifecycle:
      field: status
      initial: proposed
      transitions:
        proposed: [accepted, rejected]
        accepted: [superseded, deprecated]
      frozen: [accepted, rejected, superseded, deprecated]
    anchors: {field: code, tag: "@spec"}   # optional, see below
    items: {}                              # optional, see below
    template: templates/decision.md
```

| Key | Meaning |
|---|---|
| `path` | Where documents of this type live. `{id}` and `{slug}` are derived from the id and title. A path with no placeholder defines a singleton (`docs/architecture.md`). |
| `id` | Id template. Tokens: `{seq:N}`, `{slug}`, `{key}` (a short code from the `key` field). |
| `frontmatter` | A JSON Schema object. `id`, link keys and the lifecycle field are added by the engine. |
| `sections` | Required level-2 headings in order. `min_words` rejects empty shells; `optional: true` allows omission. |
| `lifecycle` | Legal statuses and transitions. Once a document reaches a `frozen` status, only the lifecycle field and link keys may change. Transition and freeze checks need `--base`. |
| `anchors` | Ties documents to code. `field` names a frontmatter list of globs, each of which must match at least one file. `tag` is a marker searched for in `code:` files (`// @spec REQ-REM-001`); every tag must resolve to an existing id. |
| `items` | Sub-nodes: `{requirement: {heading: "### {id}: {title}", id: "REQ-{key}-{seq:3}"}}`. |
| `template` | The file `bondstone new` starts from. Without one, a skeleton is generated from `sections`. |

### 3.2 Links

```yaml
links:
  supersedes:
    description: The decision this one replaces.
    from: decision
    to: decision
    max: 1
    inverse: superseded_by
    acyclic: true
```

Links are authored once, in the frontmatter of the `from` document, as a list of
ids. The `inverse` name is never authored; it exists for rules and views. Link
names are namespaced like types: another pack refers to `ost/addressed_by`.

| Key | Meaning |
|---|---|
| `from`, `to` | A type, or a list of types. Cross-pack types are written `pack/type` and need `requires`. Item types are allowed as `to`. |
| `min`, `max` | Cardinality that always holds. Conditional cardinality belongs in a rule. |
| `to_status` | Statuses the target must be in when the link is created. |
| `acyclic` | Reject cycles through this link. |

### 3.3 Rules

A rule selects something and requires something of it. Every rule has an `id`, a
`description`, a `severity` and a `fix`; the fix text is what a person or an agent
is told to do, and may use `{id}` for the offending node. There are two kinds.

In a selector, `where` compares fields: a scalar must equal the field, a list means
"any of" (`status: [selected, delivered]`), and `parent: {...}` matches the
document that contains an item.

**State rules** look at the repository as it is:

```yaml
rules:
  - id: superseded-has-successor
    description: A superseded decision names the decision that replaced it.
    severity: error
    select: {type: decision, where: {status: superseded}}
    require:
      incoming: {link: supersedes, min: 1}
    fix: "bondstone new adr/decision --link supersedes={id}"
```

**Change rules** look at a diff and only run with `--base`:

```yaml
  - id: code-change-updates-capability
    description: Changing code updates the capability spec that code is anchored to.
    severity: error
    on_change: {paths: ["lib/**"]}
    require:
      touched: {type: capability, anchored: true, min: 1}
    unless:
      trailer: "Spec-Impact: none"
    fix: "Update the capability doc, or add the commit trailer 'Spec-Impact: none (<reason>)'."
```

`on_change.paths` are globs over changed files; an optional `change` list narrows
the rule to `added`, `modified` or `deleted` files. `unless.trailer` is the escape hatch: a commit trailer in the checked range, with a
reason in parentheses. It is visible in history and countable, which a silent skip
is not.

Requirement vocabulary:

| Key | Holds when |
|---|---|
| `fields` | The frontmatter matches this JSON Schema fragment. |
| `sections` | These additional sections exist (same shape as type sections). |
| `outgoing`, `incoming` | `{link, min, max, where}`: the count of links, optionally only those whose other end matches `where`. |
| `anchors` | `{min}`: at least this many anchor globs resolve to files. |
| `items` | `{type, min}`: the document contains at least this many items of a type. |
| `tagged` | `{min, in}`: at least this many code tags point at the node, optionally only in paths matching `in` (for example tests). |
| `touched` | Change rules only. `{type, where, min, anchored}`: documents added or modified in the diff. `anchored: true` counts only documents anchored to the changed files. |
| `all`, `any` | Combine requirements. |
| `exec` | Run an external command that receives the selected nodes as JSON on stdin and prints diagnostics. This is the place for LLM-judged checks; such rules should use severity `advisory`. |

Severities: `error` fails the run, `warn` is reported, `advisory` is reported
separately and never fails. Profiles and overrides can also set `ignore`, which
disables a rule. (The word is `ignore` because YAML reads a bare `off` as `false`.) Rule ids are namespaced by pack
(`adr/superseded-has-successor`); repository-local rules use `local/`.

**Engine rules** are always on and need no declaration:

| Id | Checks |
|---|---|
| `core/id-unique`, `core/id-format` | Ids are unique and match the type's template. |
| `core/unknown-document` | Every file under `docs:` belongs to a type. |
| `core/frontmatter-schema` | Frontmatter matches the type's schema. |
| `core/section-missing`, `core/section-order`, `core/section-thin` | Section rules, including `min_words`. |
| `core/link-broken`, `core/link-type`, `core/link-cardinality`, `core/link-cycle` | Link integrity. |
| `core/lifecycle-transition`, `core/frozen-edited` | Lifecycle rules (need `--base`). |
| `core/anchor-broken`, `core/tag-broken` | Anchors and code tags resolve. |
| `core/view-stale` | Generated views match what `render` would write. |
| `core/waiver-expired` | No waiver is past its expiry date. |

### 3.4 Views

```yaml
views:
  - id: decision-log
    title: Decision log
    output: docs/adr/README.md
    layout: table                 # table | tree | matrix
    select: {type: decision}
    columns: [id, title, status, date, superseded_by]
    sort: [id]
```

| Layout | Extra keys |
|---|---|
| `table` | `columns` (fields, link names, inverse link names), `sort` |
| `tree` | `follow`: link names walked from the selected roots |
| `matrix` | `rows`, `cols` (selectors), `via` (link names connecting them) |

Views are written by `bondstone render` with a "generated, do not edit" header and
checked by `core/view-stale`. View outputs are exempt from type matching, so an
index can sit in the folder it describes. This is how the decision log, capability map and
traceability matrix stay current without anyone maintaining them.

### 3.5 Profiles

```yaml
profiles:
  solo:
    decision-states-alternatives: warn
    superseded-has-successor: error
  team: {}
```

A profile is a named set of severity changes. The project file picks one name and
every pack applies its own definition of it, if it has one. Severity is resolved in
this order: project `overrides`, then the pack's profile, then the rule's own
`severity`.

## 4. Composition

- **Namespaces.** Everything a pack defines is prefixed with its name, so two packs
  can both have a `requirement` type.
- **Bridges, not shared ontologies.** Packs do not have to agree on a common
  vocabulary. A bridge states the exact link between two types and the rules
  for the hand-off (see [`ost-togaf`](../examples/packs/ost-togaf/pack.yaml)).
- **Versions.** `requires` takes semver ranges; the lockfile pins what was resolved.
  A major version bump of a pack may ship a `migrations/` folder that
  `bondstone pack migrate` applies to existing documents.
- **Scaling up or down.** Solo, team and organisation setups differ in which packs
  are loaded and which profile is active, not in the engine.

## 5. Adoption

- `bondstone baseline` records current violations in the baseline file. Baselined
  violations are reported as `advisory` until fixed, and new ones fail normally.
- Waivers silence one rule for one target, with a reason and an expiry date.

## 6. Open questions

1. **Merging deltas.** Should bondstone fold per-change deltas into living docs
   itself (as OpenSpec's archive step does), or only verify that the living doc was
   touched? This sketch only verifies.
2. **Item metadata.** Items carry only id and title. Requirements may need status
   or priority, which means a syntax for per-item fields.
3. **Portfolio level.** Cross-repository links need `bondstone graph` exports
   aggregated somewhere, and ids that are unique across repositories.
4. **Path conflicts.** Two packs claiming the same folder is an error today; an
   explicit remapping in the project file may be needed.
5. **Change scope.** Change rules treat `--base..HEAD` as one change. Stacked or
   long-lived branches may need rules evaluated per commit.
