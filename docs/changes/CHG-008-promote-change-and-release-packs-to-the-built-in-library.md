---
id: CHG-008
title: Promote change and release packs to the built-in library
status: accepted
owner: dworek
kind: feature
modifies:
- CAP-built-in-library
---

## Why

`change` and `release` and their bridges proved themselves on bondstone itself and are not bondstone-specific. Other repositories should be able to use them without copying files.

## What changes

- Move `change`, `release`, `change-capability`, `change-adr` and `release-change` (with fixtures) from `.bondstone/packs` into the built-in library, keeping their versions.
- A `library` capability spec describing what the built-in library offers, tagged in the manifests.

## Out of scope

Promoting `cli`, `library` and `engine`, which stay specific to this repository.
