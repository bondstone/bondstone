---
type: decision
id: ADR-0003
title: Make Spec Kit the first host
description: Bondstone integrates with GitHub Spec Kit first, and keeps everything Spec Kit-specific out of the core.
status: draft
---

# Make Spec Kit the first host

## Context and Problem Statement

Bondstone needs one spec-driven tool to integrate with first. The candidates were compared in October 2026 on stable IDs, extension points and lifecycle hooks. BMAD and OpenSpec should follow later without command changes, and `next` must know which change is in progress without Bondstone storing a session focus. Which host comes first, and how is it plugged in?

## Considered Options

- GitHub Spec Kit
- OpenSpec
- No host: plain Markdown only

## Decision Outcome

Chosen option: "GitHub Spec Kit", because its feature folders give stable IDs, and it has extensions, presets and lifecycle hooks. In that comparison, OpenSpec lost front-matter on archive and had no lifecycle hooks.

- Everything Spec Kit-specific lives in the Spec Kit extension and preset and, from 0.1, in a `speckit` host pack that is data, not code. It covers the change folders (`specs/NNN-slug/` or `specs/YYYYMMDD-HHMMSS-slug/`), the `## Spec changes` section, each change's steps, and when a change is finished. Spec Kit's own `FR-` and `SC-` IDs stay plain text.
- A Spec Kit change is finished when every task in its `tasks.md` is checked. The core offers a small set of finish conditions that host packs choose from: every checkbox in a declared file is checked, a declared field has a given value, or the change folder has moved under a declared path. `next` starts from the first unfinished change in ID order. Bondstone never runs a host's own tools to ask.

### Consequences

- Good, because Spec Kit has a large user base and a community catalog to be listed in.
- Good, because the change in progress comes from tracked files, so every clone and every session agrees on it.
- Bad, because Spec Kit's feature specs describe one change, not the system, so Bondstone provides the living spec itself (ADR-0005).
- Bad, because Spec Kit releases often: 0.10 removed the `--ai` flag of `specify init`, and Claude Code now installs commands as skills. The extension pins `>=1.2.0,<2.0.0`, and CI tests the install against new versions.
- Bad, because a host whose changes finish in another way needs a new finish condition in the core and a new pack schema version, though no new command.
