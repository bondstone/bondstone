---
id: CLI-update
type: cli:Command
title: update
status: experimental
synopsis: bondstone update [--format text|json] [--locked] [NAME ...]
json_output: true
implements: [CAP-profiles]
---

Fetches the git sources that the profile and its presets name, and pins each one in `.bondstone/bondstone.lock`: its commit and a SHA-256 of the files of every pack, bridge and preset in it.

This is the only command that uses the network. `check` and every other command read the lock and a cache outside the repository (`$BONDSTONE_CACHE`, or `bondstone` in the user's cache folder).

Without options every ref is resolved again, so a source written with a branch moves to the branch's newest commit, and a source that nothing names any more leaves the lock. With names, only the sources that hold one of those components move. With `--locked` exactly the pinned commits are fetched and the lock is not touched: run it in CI before `check`.

Git reads `https://<host>/<org>/<repo>`. To fetch another way, such as over SSH, set git's own `url.<base>.insteadOf`.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `--locked`: Fetch exactly what the lock pins and change nothing; for CI, before check.
- `NAME`: Only move the sources that hold these packs, bridges or presets.

## Exit codes

- `0`: every source is in the cache, and without `--locked` the lock is up to date
- `1`: refused: with `--locked` the lock does not pin a source or does not match what its commit holds; a name that no pinned source holds; a source without components; a malformed lock
- `3`: no profile, `--root` is not a directory, or a source could not be fetched

## Examples

```sh
bondstone update
bondstone update architecture
bondstone update --locked
```

## JSON output

```json
{"version": 1, "lock": ".bondstone/bondstone.lock", "changed": true, "removed": [],
 "sources": [{"source": "github.com/acme/bondstone-packs//packs@v1.2.0", "commit": "4f2a9c1…", "previous": null,
              "changed": true, "components": [{"kind": "pack", "id": "architecture", "version": "1.2.0"}]}]}
```

`previous` is the commit the lock had before, `null` for a source that was not pinned. `removed` lists the sources that left the lock.
