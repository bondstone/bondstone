---
id: CAP-built-in-library
title: Built-in library
status: active
owner: dworek
code: LIB
constrained_by:
- ADR-002
- ADR-003
---

## Purpose

The packs and bridges that ship with bondstone, so that repositories can use common methods without writing packs.

## Requirements

### REQ-LIB-001: Decision records

The built-in library SHALL include the `adr` pack: decisions with a lifecycle, supersession, immutability once decided, and a decision log.

#### Scenario: Using ADRs

- Given a profile with `adr@1`
- When check runs
- Then documents in `docs/adr/` are validated as decisions

### REQ-LIB-002: Product discovery

The built-in library SHALL include the `ost` pack: outcomes, opportunities, solutions and experiments with an opportunity solution tree view.

#### Scenario: Using OST

- Given a profile with `ost@1`
- When `bondstone gen` runs
- Then the opportunity solution tree is generated

### REQ-LIB-003: Living capability specs

The built-in library SHALL include the `capability` pack: capability specs with requirement items that have scenarios and normative wording and are code-traceable.

#### Scenario: Using capabilities

- Given a profile with `capability@1`
- When a requirement has no scenario
- Then check reports it

### REQ-LIB-004: Change proposals

The built-in library SHALL include the `change` pack: proposals with a lifecycle from draft to implemented and open/implemented views.

#### Scenario: Using proposals

- Given a profile with `change@0.1`
- When a proposal is created
- Then it starts as draft

### REQ-LIB-005: Releases and changelog

The built-in library SHALL include the `release` pack: releases with a generated `CHANGELOG.md`.

#### Scenario: Using releases

- Given a profile with `release@0.1`
- When `bondstone gen` runs
- Then `CHANGELOG.md` lists releases

### REQ-LIB-006: Bridges between built-in packs

The built-in library SHALL include the bridges `ost-capability`, `adr-capability`, `change-capability`, `change-adr` and `release-change`.

#### Scenario: Connecting proposals and specs

- Given a profile with `change@0.1`, `capability@1` and `change-capability@0.2`
- When an implemented proposal delivers a requirement
- Then the requirement must exist and be tagged in code
