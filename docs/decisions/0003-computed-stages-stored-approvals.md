---
type: decision
id: ADR-0003
title: Compute stages on every run and store only approvals
description: The stage, statuses and next step are computed from the files on every run; only approvals and manual checks are stored, in the documents, with a versioned hash.
status: proposed
---

# Compute stages on every run and store only approvals

## Context and Problem Statement

Every session, on every branch, must get the same stage and next step from the same files. Some facts cannot be computed, though: that a person approved a document, or checked a requirement by hand. What is stored, and where?

## Considered Options

- Compute everything on every run; store only approvals and manual checks, in the documents themselves
- Keep project state (stage, focus, progress) in a state file that commands update
- Compute stages, but keep approvals in a separate ledger file

## Decision Outcome

Chosen option: "Compute everything on every run; store only approvals and manual checks, in the documents themselves", because a state file must be merged between branches and drifts from the documents it describes.

- An approval is the document's `status` plus a `verified` record (actor, time, hash) in its front-matter.
- A manual check is a `Verified:` line under a `Check: manual` requirement.
- The hash covers the whole document after normalization (UTF-8 without a BOM, LF endings, Unicode NFC, no trailing whitespace, one final newline, front-matter without `status` and `verified`). It is stored with a version prefix, such as `sha256-n1:`.
- An approval is current while its hash matches and stale after any edit.
- There is no session focus; the active change comes from the host (ADR-0005).

### Consequences

- Good, because nothing needs merging between branches, and any session computes the same answer.
- Good, because an approval travels with the document it approves and shows in its diff.
- Bad, because `approve` changes the approved file, so approving makes a commit.
- Bad, because the hash detects change but is not a signature; ADR-0006 covers who may write it.
- Bad, because changing the normalization needs a new hash version, or every approval goes stale at once.
