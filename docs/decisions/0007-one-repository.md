---
type: decision
id: ADR-0007
title: Keep the CLI and its integrations in one repository
description: The CLI and its integrations live in one repository and are released with separate tags.
status: proposed
---

# Keep the CLI and its integrations in one repository

## Context and Problem Statement

Bondstone has a CLI and integrations: the Spec Kit extension and preset, hook configuration and a CI example. The CLI must stay usable without any integration, so that other hosts such as BMAD can use it. Do they share a repository?

## Considered Options

- One repository with separate release tags
- Separate repositories for the CLI and each integration

## Decision Outcome

Chosen option: "One repository with separate release tags". `bondstone-vX.Y.Z` tags publish the CLI to PyPI, and `speckit-vX.Y.Z` tags attach the extension and preset zips to a GitHub release. Version numbers follow the release they ship in: REL-0.1 ships 0.1.x. The CLI never imports or depends on an integration.

### Consequences

- Good, because a change to the CLI's JSON contract and the extension that reads it lands in one pull request.
- Bad, because the release workflow builds two kinds of artifact, and each integration declares the minimum CLI version it needs (SPECKIT-10).
