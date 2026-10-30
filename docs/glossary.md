---
type: glossary
id: GLOSSARY
title: Glossary
description: Bondstone's domain terms and their meaning.
status: draft
---

# Glossary

- **Requirement:** an approved behavior with a stable ID, such as `SYNC-2`, a release and at least one example.
- **Example:** an acceptance criterion under a requirement, with a scoped ID such as `SYNC-2.1` that tests carry in their names.
- **Evidence status:** untested, linked (tests exist, no result yet), passing, failing or manual.
- **Living doc:** a document that describes the product as it is and as planned, kept forever: brief, roadmap, capability specs, architecture, decisions, glossary, screens, runbook.
- **Change doc:** a document written for one piece of work and archived or frozen when it ships: version PRD, epic, Spec Kit folder, release checklist, spike note.
- **Delta:** a change to requirements that a version PRD declares: ADDED, MODIFIED, REMOVED, DEFERRED or DROPPED.
- **Story:** one row of a version PRD's story table (`ST-17`); its Spec Kit spec is the story.
- **Phase:** where the project stands (Inception, Shape, Foundation, then Build, Release and Next version per version, with Operate alongside), computed from the documents and test results.
- **Profile and pack:** a profile is the set of documents, IDs, rules and phases a project uses, made of YAML packs; simple-app is the first.
- **Host:** the spec workflow Bondstone plugs into; Spec Kit is the first.
- **Appetite:** the time a release may take; scope shrinks to fit it.
