---
id: CLI-graph
type: cli:Command
title: graph
status: stable
synopsis: bondstone graph [--format json|mermaid] [--type TYPE]
json_output: true
implements: [CAP-agent-guidance]
---

Exports the graph of documents, items, links and code tags, as JSON or as a Mermaid diagram.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format json|mermaid`: JSON (default) or a Mermaid diagram.
- `--type TYPE`: Only nodes of this type; may be repeated (a diagram shows documents only by default).

## Exit codes

- `0`: done
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone graph
bondstone graph --format mermaid --type adr:Decision
```

## JSON output

`version`, `components`, `roles`, `nodes` (with `id`, `type`, `path`, `line`, `title`, `status`, `parent`, `covered` and `fields`), `edges` (with `from`, `to` and `link`) and `code` (the tagged regions, with `id`, `path`, `start` and `end`). The schema ships as `schemas/graph.schema.json`.
