---
id: CLI-graph
title: graph
status: experimental
synopsis: bondstone graph
implements:
- CAP-graph
json_output: true
---

## Options

None.

## Exit codes

- `0`: success.
- `2`: configuration or usage error.

## Examples

```sh
bondstone graph > graph.json
```

## JSON output

```json
{"components": [{"kind": "pack", "id": "adr", "version": "1.0.0"}],
 "roles": {"decision": ["adr:Decision"]},
 "nodes": [{"id": "ADR-001", "type": "adr:Decision", "path": "docs/adr/ADR-001-x.md", "line": 1,
            "status": "accepted", "title": "...", "parent": null, "links": {}}]}
```
