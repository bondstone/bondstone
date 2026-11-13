# speckit

Makes [Spec Kit](https://github.com/github/spec-kit) features part of the graph: each folder
`specs/NNN-name/` is a `speckit:Feature` whose status comes from its files.

| Status | When |
| --- | --- |
| `specified` | `spec.md` exists |
| `planned` | `plan.md` exists |
| `implemented` | every task in `tasks.md` is ticked |

Tested with **Spec Kit 1.4.0** (bondstone ADR-017); the preset accepts `>=1.4.0,<1.5`. Spec
Kit changes its templates and its customisation mechanisms between releases, so a new minor
release is tested before the bound is raised: install the preset in a fresh project with
`specify init`, check `specify preset resolve spec-template`, create a feature with
`.specify/scripts/bash/create-new-feature.sh` and run `bondstone check` on it.

## Frontmatter

Bondstone needs `id` and `type` in the frontmatter of every document, and Spec Kit's
`spec-template` has none. The folder `spec-kit/` here is a Spec Kit preset that adds the
block. Install it once in a repository that was set up with `specify init`:

```bash
specify preset add --dev "$(python -c 'import bondstone_library; print(bondstone_library.speckit_preset())')"
specify preset resolve spec-template    # shows the frontmatter layer on top of the core template
```

From then on `/speckit.specify` writes `spec.md` with the block, and the command tells the
agent to fill it in. A feature that exists already needs the block by hand:

```yaml
---
id: 003-snooze-reminders        # the name of the folder
type: speckit:Feature
title: Snooze reminders
modifies: [CAP-reminders]       # with the bridge speckit-capability
delivers: [REQ-REM-003]         # with the bridge speckit-capability
decided_by: [ADR-004]           # with the bridge speckit-adr
---
```

Only `spec.md` is a document. `plan.md` and `tasks.md` decide the status and count as part of
the feature when bondstone asks what a change touched. Keep `specs/` out of the profile's
`docs` globs, or bondstone reports `plan.md` and `tasks.md` as files that match no type.
