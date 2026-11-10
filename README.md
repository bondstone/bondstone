# bondstone

**Living documentation, enforced.** Bondstone checks a repository's documents against rules
that live in the same repository. Coding agents run it to validate their own work; git hooks
and CI run it as a gate.

> Status: v1 under construction. The design is [docs/design.md](docs/design.md). Phase 1,
> the core check, is in place: `check`, `gen` and `profile check`.

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
| `bondstone gen` | Regenerate views. |
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
| 3 | Environment error: no profile found, or the root is not a directory |

JSON output has a `version`, a `summary` and one entry per diagnostic with `rule`, `severity`,
`path`, `line`, `node`, `message`, `hint` and, when one command resolves it, `fix.command`.

## Development

```bash
uv sync
uv run pytest
uv run bondstone --root examples/habit-tracker check
```

Golden files for CLI output are in `tests/golden`; `BONDSTONE_UPDATE_GOLDEN=1 uv run pytest`
rewrites them.

## License

MIT
