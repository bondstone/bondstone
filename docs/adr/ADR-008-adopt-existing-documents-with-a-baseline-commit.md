---
id: ADR-008
title: Adopt existing documents with a baseline commit
status: accepted
owner: dworek
date: '2026-11-10'
---

## Context

Diff checks compare documents with a git base. When bondstone is adopted in a repository, or a long-lived branch is merged, every existing document looks new against the target branch, so `bondstone/status-initial` fails for accepted decisions and active specs that were properly reviewed along the way.

## Decision

The profile records a `baseline` commit, set with `bondstone baseline [REF]`. A document that is missing at the base but exists at the baseline is compared with its baseline version instead of being treated as new: status transitions and immutability are checked against the baseline, and the creation status check is skipped.

## Alternatives considered

- Waivers per document: one entry per file, and they silence the checks instead of comparing.
- Skipping `--base` checks for the adoption pull request in CI: hides real problems in that pull request.
- A list of grandfathered ids: grows with the repository and duplicates git history.

## Consequences

Adoption is one command and one commit. The baseline commit must be available to git (CI checks out full history), and it has to be moved forward when a long-lived branch is merged, since documents created after the baseline still count as new.
