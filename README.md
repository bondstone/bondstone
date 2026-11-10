# bondstone

**Living documentation, enforced.** Bondstone checks a repository's decisions,
capability specs, discovery artifacts and architecture docs against rules that live in
the repository itself. Coding agents run it to validate their own work; git hooks and CI
run it as a gate.

> Status: proof of concept (`POC` branch). See [docs/design.md](docs/design.md).

## Why

- Spec-driven tools leave per-change artifacts behind but no **living doc** of what is
  true today.
- Links and required content between documents are conventions nobody checks.

Bondstone turns both into deterministic checks.

## How it works

| Concept | What it is |
|---|---|
| **Pack** | One method: document types, fields, sections, links, lifecycles, rules, views, templates, agent guidance (`adr`, `ost`, `capability`, …) |
| **Bridge** | Everything that connects two or more packs: cross-pack links, hand-off rules, cross-pack views, role assignments. Packs never know about each other. |
| **Profile** | `.bondstone/profile.yaml`: which packs and bridges a repository uses, plus overrides, waivers and repository rules |
| **Trait** | Engine-defined behaviour a type opts into: `lifecycle`, `owned`, `supersedable`, `immutable`, `code-traceable`, `indexed` |
| **Role** | A name (`living-spec`, `decision`, …) mapped to types by bridges or the profile, so generic rules work across packs |
| **View** | Generated Markdown (indexes, trees) that `check` keeps in sync |

There is no shared ontology: packs stay independent, traits give mechanical behaviour,
and bridges or profiles give meaning.

## Install

```bash
uv tool install git+https://github.com/bondstone/bondstone@POC
# or: pip install git+https://github.com/bondstone/bondstone@POC
```

## Quick start

```bash
bondstone packs                                   # built-in packs and bridges
bondstone init --packs adr@1,ost@1,capability@1 \
               --bridges ost-capability@1,adr-capability@1
bondstone new adr:Decision --title "Store habits locally with SQLite"
bondstone new capability:Capability --title "Reminders" --set code=REM
bondstone supersede ADR-001 --title "Store habits with Drift"
bondstone gen                                     # regenerate views
bondstone check                                   # validate everything
bondstone check --base origin/main --format json  # + lifecycle, immutability, diff rules
bondstone agent --output AGENTS.bondstone.md      # instructions for coding agents
```

A complete example lives in [`examples/habit-tracker`](examples/habit-tracker): a solo
mobile app using Opportunity Solution Tree discovery, living capability specs and ADRs.

```text
$ bondstone check --base HEAD
app/lib/habits.dart:10: error bondstone/code-ref-unknown: code references unknown id 'REQ-HAB-009'
docs/adr/ADR-002-store-habits-locally-with-sqlite.md:1: error bondstone/immutable: ADR-002 was 'accepted' and may not be edited (only status may change)
    hint: Create a new document that supersedes it instead.
docs/discovery/solutions/SOL-2-streak-freeze.md:5: error bondstone/link-broken: addresses -> 'OPP-9': no such document
.bondstone/profile.yaml: warn profile/code-change-updates-living-spec: Changes to app code come with an update to a living spec. (...)
```

## Commands

| Command | Purpose |
|---|---|
| `check [--base REF] [--format json] [--fail-on warn]` | validate; exit 1 on failure |
| `gen` | regenerate views |
| `new TYPE --title T [--set k=v]` | scaffold a document with the next id |
| `supersede ID --title T` | replace a document: successor, `superseded` status, links moved |
| `init --packs … --bridges …` | create a profile and generate views |
| `profile check` | validate the profile, packs and bridges |
| `rules`, `explain RULE` | list / explain active rules |
| `agent [--output FILE]` | generate agent instructions |
| `graph` | export the document graph as JSON |
| `packs` | list built-in packs and bridges |
| `pack test DIR…` | run a pack's or bridge's fixtures |

## Built-in library

| Kind | Id | Contents |
|---|---|---|
| pack | `adr` | `Decision` with lifecycle, supersession, immutability |
| pack | `ost` | `Outcome`, `Opportunity`, `Solution`, `Experiment` |
| pack | `capability` | living `Capability` specs with embedded `Requirement` items (code-traceable) |
| bridge | `ost-capability` | committed solutions must be `realized_by` capabilities |
| bridge | `adr-capability` | capabilities are `constrained_by` live decisions |

Custom packs and bridges go in any directory listed under `sources:` in the profile
(default `.bondstone/packs`); see the [design doc](docs/design.md) for the formats.

## CI and hooks

GitHub Actions:

```yaml
- run: pip install git+https://github.com/bondstone/bondstone@POC
- run: bondstone check --base origin/${{ github.base_ref }}
```

[pre-commit](https://pre-commit.com):

```yaml
repos:
  - repo: https://github.com/bondstone/bondstone
    rev: POC
    hooks: [{id: bondstone-check}]
```

## Development

```bash
pip install -e '.[dev]'
pytest
bondstone pack test src/bondstone/library/packs/* src/bondstone/library/bridges/*
```

## License

MIT
