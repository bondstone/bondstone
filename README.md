# bondstone

**Living documentation, enforced.** Bondstone checks a repository's documents against rules
that live in the same repository. Coding agents run it to validate their own work; git hooks
and CI run it as a gate.

> Status: v1 under construction. The design is [docs/design.md](docs/design.md). Phases 1
> to 4 are in place: the core check, the checks that compare with a base commit, the
> commands that agents work with, and the pack library with presets and the Spec Kit adapter.

## How it works

A profile (`.bondstone/profile.yaml`) names the packs and bridges a repository uses. Packs
define document types, links, rules and views; bridges connect packs. Bondstone reads the
documents and the code tags into one graph and checks the rules against it. A profile can also
extend presets, which bring packs, bridges and rules shared by several repositories.

The engine ships no packs. A profile finds its packs and bridges in two places, in this order:

1. the folders it lists under `sources` (default `.bondstone/packs`), for packs that live in
   the repository;
2. installed packages that register a folder of packs, such as
   [`bondstone-library`](library/README.md): decisions, capability specs, the Spec Kit
   adapter, command references, releases and the presets `starter` and `starter-speckit`.

[`examples/habit-tracker`](examples/habit-tracker) is a complete setup with three local packs
(`adr`, `capability`, `ost`) and two bridges. Bondstone's own documentation runs on the
library package, and its own changes are planned as Spec Kit features under [`specs/`](specs).

## Commands

| Command | Purpose |
| --- | --- |
| `bondstone check [--format text\|json\|sarif] [--fail-on warn]` | Validate documents, links, rules, code tags and views. |
| `bondstone check --base REF [--no-exemptions]` | Also check the changes since REF: lifecycles, immutability and diff rules. |
| `bondstone gen` | Regenerate views. |
| `bondstone baseline [REF]` | Record the commit whose documents count as already adopted. |
| `bondstone baseline --known [--prune]` | Record the current violations, so that only new ones fail; `--prune` removes the fixed ones. |
| `bondstone waive RULE [NODE] --reason R --expires D` | Add a waiver to the profile: one exception with a reason and an end. |
| `bondstone report [--base REF] [--format text\|json]` | Count nodes, coverage, waivers, known violations and exemptions. |
| `bondstone update [NAME ...] [--locked]` | Fetch the git sources of packs and pin them in the lock file. |
| `bondstone profile check [--format text\|json]` | Validate the profile, packs and bridges. |
| `bondstone new TYPE --title T [--set k=v] [--dry-run]` | Scaffold a document with the next id at the right path. |
| `bondstone status ID STATUS` | Change the status of a document or an item, if its lifecycle allows the step. |
| `bondstone supersede ID --title T` | Create a successor, mark the old document superseded, move the links to it. |
| `bondstone context --for PATH... \| --base REF` | List what to read before editing, and the diff rules that will fire. |
| `bondstone rules`, `bondstone explain RULE` | List the active rules with their effective severity; explain one. |
| `bondstone agent [--format md\|skill] [--output F]` | Write the instructions for coding agents. |
| `bondstone graph [--format json\|mermaid] [--type T]` | Export the graph of documents, links and code tags. |
| `bondstone init [--preset NAME]` | Create a profile in the current folder, empty or extending a preset. |
| `bondstone packs [--format text\|json]` | List the packs, bridges and presets available to the repository, and which ones its profile uses. |
| `bondstone pack test DIR... [--format text\|json]` | Run the fixtures of packs, bridges and presets. |

Every command takes `--root DIR`; without it, bondstone uses the nearest folder that has a
`.bondstone/profile.yaml`. Each command has a reference document in [`docs/cli`](docs/cli); the
table in [`docs/generated/cli-reference.md`](docs/generated/cli-reference.md) lists them.

```text
$ bondstone --root examples/habit-tracker check
✓ 0 error(s), 0 warning(s), 15 nodes
```

| Exit code | Meaning |
| --- | --- |
| 0 | No violations at or above `--fail-on` |
| 1 | Violations found, or a command refused what it was asked |
| 2 | Configuration error: invalid profile, pack or bridge |
| 3 | Environment error: no profile found, the root is not a directory, `--base` outside a git repository, a ref that is not a commit, or `pack test` on a folder that is no pack |

JSON output has a `version`, a `summary` and one entry per diagnostic with `rule`, `severity`,
`path`, `line`, `node`, `message`, `hint` and, when one command resolves it, `fix.command`.

## Views

A view is a generated Markdown file, declared by a pack, a bridge or the profile. `bondstone
gen` writes it, and `check` fails when a committed view no longer matches the documents.

```yaml
views:
  - id: decision-usage               # a table: one row per selected node
    output: docs/generated/decision-usage.md
    select: {type: "adr:Decision"}
    columns: [id, title, status, "<-constrained_by"]   # a link column lists linked ids
  - id: decisions-applied            # a matrix: a mark where the links connect row and column
    output: docs/generated/decisions-applied.md
    render: matrix
    rows: {type: "capability:Capability"}
    cols: {type: "adr:Decision"}
    via: [constrained_by]            # a path of links; `<-name` follows a link backwards
  - id: tree                         # a tree: the selected nodes, then what the links lead to
    output: docs/generated/tree.md
    render: tree
    select: {type: "ost:Outcome"}
    levels: [{incoming: serves}, {incoming: addresses}]
```

## Presets

A preset is a partial profile in a `preset.yaml`, found in the same places as packs. A profile
names the presets it builds on under `extends`:

```yaml
# .bondstone/profile.yaml
bondstone: 1
extends: [starter@1]
code:
  include: ["src/**/*.py"]
```

```yaml
# preset.yaml of an organisation
id: acme
version: 1.0.0
extends: [starter@1]                 # applied before this preset
packs: [runbooks@1]                  # added to the packs of `starter` and of the profile
overrides:
  adr/alternatives-considered: error
lock: [adr/alternatives-considered, bondstone/immutable]
rules:
  - id: code-change-has-decision     # reported as acme/code-change-has-decision
    description: New source files come with a decision.
    on_change: {code: true, kinds: [added]}
    require: [{changed: {type: "adr:Decision"}, min: 1}]
```

- Severities apply in layers: a rule's default, then each preset in the order it is applied,
  then the profile. `bondstone rules` says which layer set a severity.
- A rule under `lock` keeps at least the severity it has after that preset. A later preset or
  the profile can raise it; lowering it or waiving it is a configuration error.
- `on_change: {code: true}` fires on the files the profile lists under `code`, so a preset
  can ship a diff rule without knowing a repository's paths.

`bondstone init --preset starter` creates a profile that extends the library's `starter`
preset: decisions, living capability specs, and the rule that a change to tagged code updates
the capability it implements.

## Sharing packs through git

A team that shares packs, bridges or presets between repositories keeps them in a git
repository and names it under `sources`, as `host/org/repo//path@ref`:

```yaml
# .bondstone/profile.yaml
sources:
  - github.com/acme/bondstone-packs//packs@v1.2.0
extends: [acme-standard@1]
```

`bondstone update` fetches each source, and writes `.bondstone/bondstone.lock` with the commit
its ref stood for and a SHA-256 of every component. Commit the lock. From then on `check`
reads only the lock and a cache outside the repository, so it never uses the network and
gives the same result on every machine:

- A source that the lock does not pin is a configuration error; run `bondstone update`.
- A machine whose cache does not hold the pinned commit, such as a fresh CI runner, stops
  with exit code 3; run `bondstone update --locked`, which fetches exactly what the lock pins
  and never changes it.
- `bondstone update` resolves every ref again, so a source written with a branch moves.
  `bondstone update NAME` moves only the source that holds that pack, bridge or preset.

The resolver searches the repository's own folders first, then git sources, then installed
packages such as bondstone-library, so a local copy always wins. A preset may name git sources
of its own, which is how an organisation's preset brings its packs with it. The cache is
`$BONDSTONE_CACHE`, or `bondstone` in the user's cache folder. Git fetches
`https://host/org/repo`; use git's `url.<base>.insteadOf` for SSH.

Private repositories need no setup in bondstone: it uses the credentials git has, from a
credential helper on your machine or a token in CI. [`docs/cli/update.md`](docs/cli/update.md)
shows both.

## Spec Kit

The library's `speckit` pack reads each [Spec Kit](https://github.com/github/spec-kit) feature
folder `specs/NNN-name/` as one document, with a status taken from its files: `specified`
with `spec.md`, `planned` with `plan.md`, `implemented` when every task in `tasks.md` is
ticked. Two bridges then ask of an implemented feature that the requirements it delivers are
active and tagged in code, and that the decisions it rests on are accepted.

```bash
specify init --here                      # Spec Kit 1.4.0
specify preset add --dev "$(python -c 'import bondstone_library; print(bondstone_library.speckit_preset())')"
bondstone init --preset starter-speckit
```

The Spec Kit preset adds the frontmatter block bondstone reads to every new `spec.md`. The
bondstone preset adds a rule that a change to code comes with a changed feature; it is a
warning until a profile raises it. See the [pack's README](library/src/bondstone_library/packs/speckit/README.md).

## Testing a pack

A pack or bridge keeps its fixtures next to its manifest. Each fixture is a small repository
with a profile, a few documents and an `expected.yaml` that lists the rule of every error and
warning the check must report there:

```text
adr/
  pack.yaml
  fixtures/
    valid/      .bondstone/profile.yaml, docs/..., expected.yaml (errors: [], warnings: [])
    invalid/    .bondstone/profile.yaml, docs/..., expected.yaml (errors: [adr/..., ...])
```

`bondstone pack test adr` checks every fixture and fails when a rule is missing or unexpected.
The pack under test and the packs in the same folder are used before any other copy.

## Working with agents

`bondstone agent` writes `AGENTS.bondstone.md` from the active profile: the workflow, every
type, every rule with the severity `check` applies, and each pack's guidance. `AGENTS.md` or
`CLAUDE.md` only needs one line that points at it. `--format skill` writes the same content as
a Claude Code skill.

An agent's loop then looks like this:

```bash
bondstone context --for app/lib/reminders.dart   # what to read, which rules will fire
bondstone new adr:Decision --title "Snooze with one more local notification"
bondstone status REQ-REM-003 active
bondstone check --base origin/main --format json # fix until exit 0; run each fix.command
```

The scaffolding commands refuse what `check` would report afterwards, regenerate stale views,
and print JSON with `--format json`. `tests/test_walkthrough.py` plays such a task on the
example from start to finish.

## Changes over time

`check --base REF` compares the working tree, committed or not, with the commit where the
current branch left REF. Three kinds of checks need that:

- **Lifecycles.** A new document or item starts in its lifecycle's `initial` status, and a
  status only changes along the lifecycle's `transitions`.
- **Immutability.** A document that was in an immutable status, such as an accepted decision,
  only changes in the fields its type allows.
- **Diff rules.** A rule with `on_change` fires when matching files changed. With
  `traced: true` it asks for an update of exactly the documents that are tagged in the changed
  regions of code. A clause `link_changed: modifies` asks that every document a changed node
  names under that link changed too.

A diff rule that declares `exempt: {trailer: Spec-Impact}` can be skipped for one change by a
commit trailer with a reason. The exemption stays visible as `bondstone/exemption-used`:

```text
Move reminder scheduling into its own module

Spec-Impact: none (pure move, no behaviour change)
```

`Spec-Impact: none [CAP-reminders] (rename only)` limits the exemption to the listed nodes, and
`check --no-exemptions` ignores every trailer.

When a repository adopts bondstone, its existing documents look new against an older base.
`bondstone baseline` records the adoption commit in the profile, and documents that are absent
at the base are compared with their version at that commit. CI needs the full history for
this: `fetch-depth: 0` with `actions/checkout`.

## Adopting with existing problems

Old documents break rules. Fixing them all first blocks adoption, and lowering a severity also
removes the gate for new work. `bondstone baseline --known` records the current violations in
`.bondstone/known.json` instead:

```json
{
  "bondstone": 1,
  "created": "2026-11-13",
  "entries": [
    {"rule": "bondstone/section-missing", "node": "ADR-004", "key": "Alternatives considered"},
    {"rule": "bondstone/untyped-document", "path": "docs/notes.md"}
  ]
}
```

An entry is the rule, the node (or the file, when there is no node) and a key that names the
problem. It has no line number, so editing the document elsewhere does not break the match.

- A violation that matches an entry is reported as `info`, marked `[known]`, and does not fail.
  Any other violation fails, also in a document that has known ones.
- An entry whose problem is fixed is reported as `bondstone/known-stale` until
  `bondstone baseline --known --prune` removes it. `--prune` never adds an entry.
- With `--base`, entries added since the base are `bondstone/known-grew`, an error: recording
  a new violation cannot hide it. The change that adds the profile itself is exempt, so a
  repository adopts bondstone in one commit. A deliberate reset overrides that rule in the
  profile in the same change.
- Rules about a change (diff rules, lifecycles, immutability) are never recorded. A rule can
  refuse known violations with `allow_known: false`, and a preset can lock one that way:
  `lock: [{rule: adr/alternatives-considered, allow_known: false}]`.

The generated agent instructions tell agents never to create or extend the file.

## In CI

`check` never touches the network, and its exit code is the gate: 0 passes, 1 means violations,
2 a broken configuration and 3 an environment the checker could not run in.

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0          # --base and the baseline read older commits
- run: bondstone update --locked   # only with git sources: fetch exactly what the lock pins
- run: bondstone check --base origin/${{ github.base_ref }}
```

`bondstone check --format sarif` prints the same diagnostics as SARIF 2.1.0, which code-scanning
tools read. On GitHub, uploading the file shows the diagnostics as annotations on the pull
request (the job needs the `security-events: write` permission):

```yaml
- run: bondstone check --base origin/${{ github.base_ref }} --format sarif > bondstone.sarif
  continue-on-error: true   # the gate is the step above; this one only reports
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: bondstone.sarif
```

Known violations and exempted changes are in the file as suppressed results, so they do not
show up as open alerts.

## Bondstone on bondstone

This repository documents itself with bondstone. [`.bondstone/profile.yaml`](.bondstone/profile.yaml)
uses the `adr` and `capability` packs of the example until the library package exists.

| Where | What |
| --- | --- |
| [`docs/adr`](docs/adr) | The decisions of the design (D1 to D14) and later ones, as immutable records. |
| [`docs/capabilities`](docs/capabilities) | One living spec per engine area. Every requirement is tagged in `src/bondstone` with a `bondstone: REQ-...` comment. |
| [`docs/generated`](docs/generated) | The decision log, the capability index and the requirement list, written by `bondstone gen`. |
| [`AGENTS.bondstone.md`](AGENTS.bondstone.md) | The instructions for coding agents, written by `bondstone agent`. |

A change to tagged code must update the capability that code implements, or say why not with a
`Spec-Impact` trailer. CI runs `bondstone check --base` on every pull request.

## Development

```bash
uv sync
uv run pytest
uv run bondstone --root examples/habit-tracker check
uv run bondstone check --base origin/v1    # bondstone's own documentation, as CI checks it
```

Golden files for CLI output are in `tests/golden`; `BONDSTONE_UPDATE_GOLDEN=1 uv run pytest`
rewrites them.

## License

MIT
