---
id: CHG-007
title: Document every built-in pack and bridge (self-hosting phase 3)
status: implemented
owner: dworek
kind: docs
---

## Why

Built-in packs and bridges are only described by their manifests. Users choosing packs need a README, and its version must not drift from the manifest.

## What changes

- Local `library` pack: a `README.md` next to every built-in `pack.yaml` / `bridge.yaml`, with purpose, contents and an example.
- Rules (using CHG-005): every manifest has a README, and the README's name and version match the manifest.

## Out of scope

A rendered catalog website.
