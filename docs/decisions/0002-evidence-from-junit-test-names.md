---
type: decision
id: ADR-0002
title: Read evidence from requirement IDs in JUnit test names
description: A requirement is proven by reported test results whose names carry its ID; production code is never tagged or read.
status: draft
---

# Read evidence from requirement IDs in JUnit test names

## Context and Problem Statement

Bondstone must decide, for every requirement and in any language, whether it is proven, without parsing each language. Where does the evidence come from?

## Considered Options

- Tags in production code that point at requirements, as in OpenFastTrace
- Requirement IDs anywhere in test files, counted by presence, as in DocGuard and spec-kit-trace
- Requirement IDs in test names, read from JUnit XML reports

## Decision Outcome

Chosen option: "Requirement IDs in test names, read from JUnit XML reports", because nearly every test runner can write JUnit XML and a test's name reaches the report, so Bondstone gets pass or fail per requirement without knowing the language. A plain-text search of the lines that declare tests is an early signal: a test found only there makes a requirement `linked`, not `passing`. Production code is read by path only, for component ownership.

### Consequences

- Good, because evidence means a test passed, not that an ID was mentioned.
- Good, because there are no tags in production code to keep current.
- Bad, because each stack needs a naming convention, some reporters drop display names, and some toolchains need a converter to write JUnit XML, such as xcbeautify for Xcode or tojunit for Flutter. The conventions are documented per stack, and a review signal can flag test files whose IDs never reach a report.
- Bad, because naming rules such as pep8-naming's N802 flag `test_SYNC_2_…`, so test files need a lint exception.
- Bad, because a local report can be old or missing, so the pre-commit check skips the evidence rules, and the release gate runs in CI right after the tests.
- Bad, because a test name is a claim: Bondstone proves that the named test ran and passed, not that it tests the requirement.
