# bondstone

**Living documentation, enforced.** Bondstone checks a repository's documents against rules
that live in the same repository. Coding agents run it to validate their own work; git hooks
and CI run it as a gate.

> Status: v1 under construction. The design is [docs/design.md](docs/design.md). Phases 1
> and 2 are in place: the core check, and the checks that compare with a base commit.

## How it works

A profile (`.bondstone/profile.yaml`) names the packs and bridges a repository uses. Packs
define document types, links, rules and views; bridges connect packs. Bondstone reads the
documents and the code tags into one graph and checks the rules against it.

The engine ships no packs. For now, packs and bridges live in the repository, in the folders
the profile lists under `sources` (default `.bondstone/packs`).
[`examples/habit-tracker`](examples/habit-tracker) is a complete setup with three packs
(`adr`, `capability`, `ost`) and two bridges.

## Commands

| Command | Purpose |
| --- | --- |
| `bondstone check [--format text\|json] [--fail-on warn]` | Validate documents, links, rules, code tags and views. |
| `bondstone check --base REF [--no-exemptions]` | Also check the changes since REF: lifecycles, immutability and diff rules. |
| `bondstone gen` | Regenerate views. |
| `bondstone baseline [REF]` | Record the commit whose documents count as already adopted. |
| `bondstone profile check [--format text\|json]` | Validate the profile, packs and bridges. |

Every command takes `--root DIR`; without it, bondstone uses the nearest folder that has a
`.bondstone/profile.yaml`.

```text
$ bondstone --root examples/habit-tracker check
✓ 0 error(s), 0 warning(s), 15 nodes
```

| Exit code | Meaning |
| --- | --- |
| 0 | No violations at or above `--fail-on` |
| 1 | Violations found |
| 2 | Configuration error: invalid profile, pack or bridge |
| 3 | Environment error: no profile found, the root is not a directory, `--base` outside a git repository, or a ref that is not a commit |

JSON output has a `version`, a `summary` and one entry per diagnostic with `rule`, `severity`,
`path`, `line`, `node`, `message`, `hint` and, when one command resolves it, `fix.command`.

## Changes over time

`check --base REF` compares the working tree, committed or not, with the commit where the
current branch left REF. Three kinds of checks need that:

- **Lifecycles.** A new document or item starts in its lifecycle's `initial` status, and a
  status only changes along the lifecycle's `transitions`.
- **Immutability.** A document that was in an immutable status, such as an accepted decision,
  only changes in the fields its type allows.
- **Diff rules.** A rule with `on_change` fires when matching files changed. With
  `traced: true` it asks for an update of exactly the documents that are tagged in the changed
  regions of code.

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

## Bondstone on bondstone

This repository documents itself with bondstone. [`.bondstone/profile.yaml`](.bondstone/profile.yaml)
uses the `adr` and `capability` packs of the example until the library package exists.

| Where | What |
| --- | --- |
| [`docs/adr`](docs/adr) | The decisions of the design (D1 to D14) and later ones, as immutable records. |
| [`docs/capabilities`](docs/capabilities) | One living spec per engine area. Every requirement is tagged in `src/bondstone` with a `bondstone: REQ-...` comment. |
| [`docs/generated`](docs/generated) | The decision log, the capability index and the requirement list, written by `bondstone gen`. |

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
