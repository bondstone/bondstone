---
type: capability
id: "[CAP]"
title: "[Capability name]"
description: "[What this capability lets the user do]"
status: draft
retired: []
---

# [Capability name]

<!-- Living doc at docs/capabilities/<cap>.md: the only home of this capability's requirements.
     Other documents refer to requirements by ID and never restate them.
     - A version PRD's ADDED requirements land here as planned when the PRD is approved.
     - MODIFIED and REMOVED land in the commit of the story that changes the code; until then the
       requirement keeps its old wording and carries `Pending: PRD-<version>`.
     - IDs are never reused: removed or dropped IDs, and removed example IDs, go to `retired`.
     - Each example has a scoped ID (CAP-2.1) that tests carry in their names:
       test_CAP_2_1_what_it_checks. A requirement with one example may use its plain ID. -->

### [CAP]-1 [Requirement title]
Release: V-1.0

The app shall [one behavior, in one or two sentences].

- [CAP]-1.1: GIVEN [state] WHEN [action] THEN [outcome].
- [CAP]-1.2: GIVEN [state] WHEN [action] THEN [outcome].
