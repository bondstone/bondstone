---
type: release
id: RELEASE-[version]
title: "Release V-[version]"
description: "Release checklist for V-[version]"
status: draft
---

# Release V-[version]

<!-- Change doc at plan/<version>/release.md. The owner signs it off by setting status: stable. -->

## Release check

<!-- Every requirement planned for this version is proven, deferred or dropped (run bondstone status). -->

## Drift audit

<!-- Compare architecture overview, data model, screen map and glossary with the code. Each
     finding becomes a quick-fix doc change or a note here. Advice, not a gate. -->

## Store and deploy

- [ ] Version bumped
- [ ] Migration and rollback checked
- [ ] Store assets or deploy notes ready

## Retro (five minutes)

<!-- What to keep, what to change. May amend the constitution in the release PR and prunes
     docs/ideas.md. Template or preset improvements go to the idea inbox for Bondstone itself. -->

## After sign-off

- Add the changelog section, mark the version shipped in the roadmap, tag the release, and move
  plan/<version>/ to plan/archive/<version>/.
