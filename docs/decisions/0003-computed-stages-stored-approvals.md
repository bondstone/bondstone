---
type: decision
id: ADR-0003
title: Compute stages on every run and store only approvals
description: Bondstone derives stages, progress and the next step on every run, and stores only approvals and manual verifications, on the items they approve.
status: draft
---

# Compute stages on every run and store only approvals

## Context and Problem Statement

Bondstone must tell any session, on any branch, where the project stands and what to do next. Recording progress in a versioned file creates merge conflicts between branches and drifts from the documents it describes. Some facts can't be computed, though: that a person approved a document, or checked a requirement by hand. What is stored, and where?

## Considered Options

- A versioned progress file
- Computed stages, with approvals on the approved items
- Computed stages, with approvals on the items and a focus file
- Computed stages, with approvals in a separate ledger

## Decision Outcome

Chosen option: "Computed stages, with approvals on the approved items", because nothing then needs merging, and every session computes the same answer from the same files. The only state Bondstone writes is:

- an approval in the approved document's front-matter: `status: stable` and, from 0.2, Open Knowledge Format's `verified` entry for a human reviewer, `{by, at}`, with Bondstone's hash as an extra `hash` field;
- a `Verified:` line under a requirement checked by hand, with the actor, the time and, from 0.2, a hash.

A stage names the items it needs approved, so the same mechanism covers one document or many. When approved text changes, its approval goes stale and the stage reopens. The hash covers a canonical form of the text that leaves out `status`, `verified`, `Verified:` lines, front-matter comments and key order, so approving or verifying never makes anything else stale. Until 0.2 there is no hash: `status: stable` alone counts as an approval.

The focus file, a gitignored `.bondstone/state.json` that `context` would set, was dropped on 2026-10-21: it differed between clones of the same repository. The first unfinished change gives the next step its starting point instead (ADR-0005).

### Consequences

- Good, because nothing needs merging between branches, and every session computes the same answer.
- Good, because an approval travels with the document it approves and shows in its diff.
- Bad, because editing an approved document needs a new approval, and `approve` changes the approved file, so approving makes a commit.
- Bad, because the hash detects change but is not a signature; ADR-0006 covers who may write it.
- Bad, because a new canonical form needs a new hash version, and Bondstone must keep checking the old ones.
