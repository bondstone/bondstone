---
type: spec
id: EVIDENCE
title: Test evidence
description: How Bondstone links tests to requirements and decides which requirements are proven.
status: draft
components: [COMP-EVIDENCE]
fixture: simple-app
---

# Test evidence

A requirement is proven by tests whose names carry its ID. Bondstone reads the JUnit XML reports that test runners write, and searches the lines of test files that declare tests for IDs, as plain text. It never parses code and never reads the content of production source files.

## Requirements

### EVIDENCE-1 Configuration

Bondstone shall read its evidence settings from `rules.yml`: `reports` (globs of JUnit XML files), `tests` (globs of test files to search), `style` (how tests are declared and named, such as `pytest`, `jest`, `go` or `generic`) and `case_insensitive` (false by default).

- WHEN `rules.yml` sets `evidence: {reports: [build/test-results/*.xml], tests: [tests/**/*.py], style: pytest}` and CHECK-3 is untested THEN the `fix:` hint of its `requirement-covered` warning says to add a test named `test_CHECK_3_<behavior>`.

### EVIDENCE-2 ID tokens

Bondstone shall recognise a requirement ID in a reported test case or on a test-declaration line as an existing capability prefix, then `-` or `_`, then the number, where the prefix is not preceded by an uppercase letter or a digit and the number is not followed by a digit. With `case_insensitive: true`, the prefix may be in any case and shall not be preceded by any letter or digit.

| Text | Finds |
| --- | --- |
| `test_SYNC_2_uploads_once` | SYNC-2 |
| `SYNC-2 uploads pending entries once` | SYNC-2 |
| `testSYNC_2_uploadsOnce` | SYNC-2 |
| `TestSYNC_2_Uploads/offline` | SYNC-2 |
| `test_ASYNC_2_retry` | nothing |
| `test_SYNC_20_backfill` | SYNC-20 |

- WHEN a test is named `test_ASYNC_2_retry` and capability SYNC exists THEN no test is linked to SYNC-2.
- WHEN `case_insensitive` is true and a test is named `test_async_2_retry` THEN no test is linked to SYNC-2.

### EVIDENCE-3 Test reports

For each `<testcase>` in the configured reports, read in sorted path order whether a report's root is `<testsuites>` or `<testsuite>`, Bondstone shall look for IDs in its `classname` and `name` attributes and record its result as passed, failed (a `failure` or `error` child) or skipped.

- WHEN `build/test-results/junit.xml` has a test case named `test_SYNC_2_uploads_once` with a `failure` child THEN SYNC-2 is `failing`.

### EVIDENCE-4 Test files

Bondstone shall search the configured test files as plain text, without parsing the language, for ID tokens on the lines that declare tests in the configured `style` (for `pytest`, lines with `def test` or `class Test`; for `generic`, every line), and record each match with its file and line.

- WHEN line 14 of `tests/test_sync.py` reads `def test_SYNC_2_uploads_once():` and no report exists THEN SYNC-2 is `linked` to `tests/test_sync.py:14`.
- WHEN capability USER exists, the style is `pytest`, and a test body contains `USER_3 = make_user()` THEN no test is linked to USER-3.

### EVIDENCE-5 Requirement status

A requirement's tests are the test-file lines and reported test cases that name it. Each requirement shall have exactly one evidence status:

- `untested`: it has no tests;
- `linked`: it has tests, but none of its reported test cases passed or failed;
- `passing`: at least one of its reported test cases passed and none failed;
- `failing`: at least one of its reported test cases failed.

Skipped test cases count as no result. `bondstone check --json` shall list every requirement with its file, line, status and linked tests.

- WHEN `test_SYNC_2_uploads_once` passed in the report and no other test references SYNC-2 THEN `bondstone check --json` lists SYNC-2 as `passing` with that test.

### EVIDENCE-6 Coverage rules

`requirement-covered` shall warn for each in-scope requirement that is `untested`, and `requirement-passing` for each in-scope requirement that is `linked` or `failing`.

```console fixture=evidence-gaps
$ bondstone check
...
[..]: warning requirement-covered: [..]
...
```

### EVIDENCE-7 Dangling test references

An ID with an existing capability prefix but no such requirement, found in a reported test case or on a test-declaration line, shall raise a `no-dangling-links` error. With `--staged`, only staged test files shall be searched.

```console fixture=violations
$ bondstone check
? 1
...
tests/[..]: error no-dangling-links: [..]
...
```

### EVIDENCE-8 Linked but not reported

When reports exist and a requirement is linked in test files but named by no reported test case, Bondstone shall report a `not-reported` review signal naming the test file, since either the test didn't run or the reporter dropped the ID from its name.

- WHEN `tests/test_sync.py` references SYNC-3 but no test case in `build/test-results/junit.xml` names it THEN `bondstone check` prints `review not-reported` for SYNC-3.

### EVIDENCE-9 Manual requirements
Release: REL-0.2

A requirement marked `Check: manual` shall have the status `manual` while its `Verified:` line is current (APPROVE-5) and none of its tests failed; otherwise its status follows EVIDENCE-5. Tests that reference it shall still be linked and reported.

- WHEN SYNC-7 is marked `Check: manual` and has a current `Verified:` line THEN its status is `manual` and `requirement-covered` does not warn for it.
- WHEN SYNC-7 also has a failing test THEN its status is `failing`.

### EVIDENCE-10 Production code is not read

Bondstone shall not read the content of any file outside the configured document paths, host change folders, test files and reports. For other files it shall use the path only.

- WHEN `src/sync.py` contains the text `SYNC-99` THEN no `no-dangling-links` error is reported.
