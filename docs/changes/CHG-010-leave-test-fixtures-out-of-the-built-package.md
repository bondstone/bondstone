---
id: CHG-010
title: Leave test fixtures out of the built package
status: accepted
owner: dworek
kind: fix
modifies:
- CAP-built-in-library
---

## Why

The wheel ships the `fixtures/` folders of every built-in pack and bridge (101 files). They are test data for `bondstone pack test` in this repository, not something users run, and they make the installed package larger and noisier.

## What changes

- The wheel excludes `src/bondstone/library/**/fixtures`; the source distribution keeps them.
- A requirement in the built-in library spec says what the package ships, tagged in `pyproject.toml` (which this repository now scans for tags).
- A test builds the wheel and checks that manifests, templates, READMEs and the engine rule catalog are included and fixtures are not.

## Out of scope

Shipping fixtures as a separate package for pack authors.
