---
type: decision
id: ADR-0005
title: Make Spec Kit the first host, plugged in through a host pack and a bundle
description: Spec Kit is the first host; everything Bondstone knows about it lives in a host pack and a Spec Kit bundle, and the active change is found with a fixed set of locators.
status: proposed
---

# Make Spec Kit the first host, plugged in through a host pack and a bundle

## Context and Problem Statement

Bondstone needs a spec workflow to plug into first, without tying the core to it; BMAD and OpenSpec should follow without command changes. `next` and `context` also need to know which change is in progress, without Bondstone storing a session focus. Which host comes first, and how is it plugged in?

## Considered Options

- Spec Kit first, through a YAML host pack and a Spec Kit bundle
- Spec Kit first, through a Python adapter module in the core
- OpenSpec or BMAD first
- For the active change: a stored session focus
- For the active change: a fixed set of locators that host packs choose from

## Decision Outcome

Chosen option: "Spec Kit first, through a YAML host pack and a Spec Kit bundle", with "a fixed set of locators", because Spec Kit has stable feature folders, extensions, presets and hooks, and user zero already uses it.

- The host pack declares the change folders (`specs/NNN-slug/` or `specs/YYYYMMDD-HHMMSS-slug/`), the change ID taken from the folder name, the `## Spec changes` section, the IDs to ignore (`FR-`, `SC-`), and what makes a change finished.
- The bundle (extension and preset) adds the four commands, the `## Spec changes` section in the spec template and the test-naming step in the tasks command. It pins Spec Kit `>=1.2.0,<2.0.0`.
- Locators: a field in a JSON or YAML file, the current git branch matched against change IDs, or the item whose status field has a given value. Spec Kit uses the file field `feature_directory` in `.specify/feature.json`. If no change, or more than one, is found, there is no active change.
- Bondstone never runs a host's own tools to ask.

### Consequences

- Good, because a second host needs a host pack and its own bundle, not a command change.
- Good, because the active change follows what the host already records, so there is no focus to store or merge.
- Bad, because Spec Kit changes fast (0.10 removed the `--ai` flag; Claude now installs commands as skills, typed as `/speckit-bondstone-next`), so CI runs an install smoke test.
- Bad, because a host whose active work fits none of the locators needs a new locator in the core and a new pack schema version.
