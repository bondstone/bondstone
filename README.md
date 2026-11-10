# bondstone

A CLI that keeps a repository's living documentation true to a set of rules stored in
the repository itself. Coding agents run it to check their own work; git hooks and CI
run it as a gate.

> **Status: design sketch.** This branch contains the proposed file formats, the CLI
> surface and worked examples. There is no implementation here yet.

## The problem

Spec-driven tools (Spec Kit, BMAD, OpenSpec, ...) produce good per-change artifacts, but:

- nothing forces the **living docs** (decision log, capability specs, architecture) to
  be updated when a change lands, and
- the **format of documents and the links between them** are conventions nobody checks.

## The idea

| Concept | What it is |
|---|---|
| **Pack** | A versioned set of rules for one method: document types, links, lifecycles, rules, generated views, templates and agent guidance. |
| **Bridge** | A pack that defines no document types of its own and only connects the types of other packs. |
| **Project file** | `bondstone.yaml`: which packs a repository uses, the severity profile, overrides and waivers. |
| **Graph** | Every document and embedded item is a node with a stable id; links are typed edges. All rules run on the graph. |
| **State rule** | Checked against the repository as it is now. |
| **Change rule** | Checked against a diff (`--base`): "this kind of change must come with that kind of doc update". |
| **View** | A generated document (index, tree, matrix). Never written by hand or by an agent. |

Bondstone does not run a workflow. Spec Kit, BMAD or a human decide *how* work is
done; bondstone decides whether the result is acceptable.

## Contents

| Path | What |
|---|---|
| [docs/rule-pack-format.md](docs/rule-pack-format.md) | The pack and project file formats |
| [docs/cli.md](docs/cli.md) | Commands, output formats, exit codes |
| [docs/adapters.md](docs/adapters.md) | Constraining Spec Kit and BMAD, agent hooks |
| [schema/](schema/) | JSON Schemas for `pack.yaml` and `bondstone.yaml` |
| [examples/packs/](examples/packs/) | `adr`, `solo-app`, `ost`, `togaf-lite`, `ost-togaf` (a bridge) |
| [examples/projects/](examples/projects/) | A solo mobile app, and a team using OST discovery with TOGAF-lite architecture |

## What a run looks like

```text
$ bondstone check --base origin/main
docs/adr/ADR-0003-use-sqlite.md:4  error  core/frozen-edited
    ADR-0003 is 'accepted'; only its status may change.
    fix: bondstone new adr/decision --link supersedes=ADR-0003
lib/reminders/scheduler.dart      error  solo-app/code-change-updates-capability
    Code anchored to CAP-reminders changed, but CAP-reminders did not.
    fix: update docs/capabilities/reminders.md, or add the commit trailer
         "Spec-Impact: none (<reason>)"
docs/adr/README.md                error  core/view-stale
    fix: bondstone render
3 errors, 0 warnings
```

## License

MIT
