---
type: decision
id: ADR-0008
title: Run simple-app as living docs, version PRDs and stories as Spec Kit specs
description: simple-app keeps living docs and change docs apart, links them by deltas, makes each Spec Kit spec one story, and computes seven phases from inception to later versions.
status: draft
---

# Run simple-app as living docs, version PRDs and stories as Spec Kit specs

## Context and Problem Statement

ADR-0005 and ADR-0006 gave simple-app a brief, an architecture page, one living spec per capability and a `## Spec changes` section in each Spec Kit change, with four stages (frame, shape, build, release). That covers building one release, but not how a product starts from nothing, how a version is planned and approved before work starts, how planned and shipped behavior sit together, or how behavior is changed, deferred or dropped in later versions. The Simple-App Workflow Design of 2026-10-30, reviewed with nine outside suggestions, answers those questions. How does simple-app run from inception to later versions?

## Considered Options

- Keep the four stages and `## Spec changes`, and plan versions outside Bondstone
- Two document layers linked by deltas, with stories as Spec Kit specs and computed phases

## Decision Outcome

Chosen option: "Two document layers linked by deltas, with stories as Spec Kit specs and computed phases", because it covers a product's whole life with one mechanism and keeps every step deterministic. It changes ADR-0005 and ADR-0006 as follows; those records stay as written.

- **Layers.** Living docs in `docs/` (brief, roadmap, idea inbox, glossary, architecture folder, capability specs, decisions, screens, runbook) describe the product as shipped and planned. Change docs in `plan/<version>/` (version PRD, optional epics, release checklist) and Spec Kit's `specs/` describe one piece of work and are archived or frozen.
- **Deltas.** A version PRD declares ADDED, MODIFIED, REMOVED, DEFERRED and DROPPED requirements. ADDED, DEFERRED and DROPPED land in the capability specs when the PRD is approved; MODIFIED and REMOVED land in the commit of the story that changes the code, with a `Pending: PRD-<version>` marker meanwhile. `## Spec changes` is replaced by front-matter links and `## Living doc changes`.
- **Stories.** The PRD (or an optional epic) holds a story table; each Spec Kit spec is one story, linked by `story` and `proves` in its front-matter. Spec Kit's numbering stays independent.
- **Examples.** Acceptance criteria are examples under each requirement with scoped IDs (`SYNC-2.1`) that tests carry in their names; a requirement passes when every example passes.
- **Releases.** Versions move from the brief to the roadmap (`V-0.0`); every requirement carries its release, and the first version not shipped is current.
- **Phases.** Inception, Shape and Foundation once; Build, Release and Next version per version; Operate alongside. They are computed, like the stages they replace.
- **Approval.** The owner approves intent (brief, roadmap, architecture, PRD, ADRs, release checklist) and every living-doc diff in story pull requests; tests prove behavior.

### Consequences

- Good, because planned and shipped behavior live in one place per capability, and the spec never describes behavior the code lacks.
- Good, because a project with nothing gets one computed next step from its first minute, and later versions use the same loop.
- Good, because the stopgap can check every link without an AI: delta applied, pending marker, story finished, example tested.
- Bad, because the profile has more documents and rules than ADR-0006's, and a weekend app still goes through Foundation.
- Bad, because the preset wraps Spec Kit's spec template rather than appending to it, to put the story front-matter first.
- Bad, because requirement IDs of the draft PROFILE and SPECKIT specs were renumbered for this design before any was approved.
