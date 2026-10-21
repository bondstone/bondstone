---
type: decision
id: ADR-0002
title: Read evidence from requirement IDs in JUnit test names
description: A requirement is proven by a passing test whose name carries its ID, read from JUnit XML reports; production code is never read.
status: proposed
---

# Read evidence from requirement IDs in JUnit test names

## Context and Problem Statement

Bondstone must say, for every requirement, whether a test proves it, in any language and without reading production code. A requirement ID that is merely mentioned in a test file says nothing about whether the test passed. Where should evidence come from?

## Considered Options

- Requirement IDs in test names, with results read from JUnit XML reports
- Requirement IDs anywhere in test files (presence only)
- Per-language markers, such as pytest marks or annotations
- Coverage data or production code

## Decision Outcome

Chosen option: "Requirement IDs in test names, with results read from JUnit XML reports", because nearly every test runner can write JUnit XML, and a result there means the test ran and passed. Presence in test files is still used, but only to mark a requirement as linked (tests exist, no result yet).

### Consequences

- Good, because it works in any language with a JUnit reporter, and needs no per-language parser.
- Good, because pass and fail come from the run, not from a mention.
- Bad, because some toolchains need a converter (Xcode with `xcbeautify`, Flutter with `tojunit`), and Gradle may report each retry as a separate test.
- Bad, because naming rules such as pep8-naming's N802 flag `test_SYNC_2_…`, so test files need a lint exception.
- Bad, because reports are build output that is missing or out of date at commit time, so evidence rules run with `--all` and in CI, not in the pre-commit hook.
- Bad, because a test name is a claim: Bondstone proves the named test passed, not that it tests the requirement.
