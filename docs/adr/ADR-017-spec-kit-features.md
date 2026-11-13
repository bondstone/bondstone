---
id: ADR-017
type: adr:Decision
title: Read Spec Kit features through a frontmatter block and derive their status
status: proposed
owner: Adam Dworzyński
date: 2026-11-12
---

## Context

Bondstone plans its own changes with Spec Kit, and the `speckit` pack makes each feature
folder `specs/NNN-name/` a node (D13 in [the design](../design.md), ADR-013). Three things in
the design did not fit what was built since:

- The design types a feature by its path and takes its id from the folder, "so it needs no
  frontmatter". ADR-015 later made `type` mandatory in every document's frontmatter.
- Spec Kit writes no status that bondstone could read. Its templates carry a bold line
  `**Status**: Draft` that its commands never update.
- Spec Kit's templates and customisation mechanisms change between releases. The latest
  release when this was written is 1.4.0; its `spec-template` and `plan-template` have no
  frontmatter, and `tasks-template` has a frontmatter block of its own.

## Decision

1. **A feature is its `spec.md`, with a frontmatter block.** `spec.md` starts with `id`,
   `type: speckit:Feature`, `title` and the links `modifies`, `delivers` and `decided_by`.
   ADR-015 holds for features as for every other document. The id is the folder's name, and
   `bondstone/id-path` reports a feature whose id and folder differ.
2. **A Spec Kit preset adds the block.** The library ships a hand-written Spec Kit preset
   next to the `speckit` pack. It prepends the block to `spec-template` and appends a section
   to the `speckit.specify` command that tells the agent how to fill it in. It is installed
   with `specify preset add --dev`.
3. **The status is derived from files.** A new trait, `derived-status`, gives a document the
   first status whose condition holds, in the order written: for a feature `implemented` when
   every task in `tasks.md` is ticked, `planned` when `plan.md` exists, `specified` when
   `spec.md` exists. A type has `lifecycle` or `derived-status`, never both, and a `status`
   in the frontmatter of such a document is an error.
4. **`plan.md` and `tasks.md` are part of the feature, not documents.** They have no
   frontmatter and no type. A change to one of them counts as a change to the feature when a
   diff rule asks which documents changed.
5. **The adapter is pinned to Spec Kit 1.4.0.** The preset requires `>=1.4.0,<1.5`: patch
   releases are accepted, and a new minor release is tested before the bound is raised (D13).
   The pack's README names the tested release and the steps of that test, and a test in the
   library keeps the pin and the README in step.

## Alternatives considered

- **No frontmatter in `spec.md`**, as the design says. It needs an exception to ADR-015, and
  the links to capabilities, requirements and decisions would need another place to live.
- **Frontmatter in `plan.md` and `tasks.md` too.** `tasks-template` already has a
  frontmatter block; a second one would break it. The two files say nothing a feature's
  `spec.md` does not, apart from the status.
- **A `status` field that an agent keeps up to date.** Spec Kit's commands would not write
  it, so it would drift from the task list, which is where the work is tracked.
- **Generate the preset from the packs** with `bondstone adapter install speckit`. That is
  the plan for phase 6; a hand-written preset is the smaller step, and generation can replace
  it without changing what a feature looks like.

## Consequences

- An agent fills in the block. Nothing runs a script, so a block that was dropped or left
  with its placeholders shows up in `bondstone check` as `bondstone/type-missing` or
  `bondstone/id-format`.
- A feature that existed before the preset was installed needs the block added by hand.
- Lifecycle checks against a base commit do not apply to features: a derived status has no
  transitions to check.
- `specs/` stays out of the profile's `docs` globs. Inside them, `plan.md` and `tasks.md`
  would be reported as files that match no type.
- A new Spec Kit release means running the check described in the pack's README again
  before the upper bound of the pin is raised.
