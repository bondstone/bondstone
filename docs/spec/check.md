---
type: spec
id: CHECK
title: Rule checking
description: How bondstone check evaluates rules and reports violations to people, agents and CI.
status: draft
components: [COMP-RULES, COMP-CLI, COMP-CONFIG]
fixture: simple-app
---

# Rule checking

`bondstone check` evaluates the rules of the active packs over the graph and reports what fails. Errors fail the command. Warnings and review signals are reported but never fail it, except under `--release`.

## Requirements

### CHECK-1 Exit codes

`bondstone check` shall exit with 0 when there is no error violation, 1 when there is at least one, 2 on a configuration or usage error, and 3 on an internal error.

```console
$ bondstone check
errors: 0 · warnings: 0 · signals: 0
```

```console fixture=violations
$ bondstone check
? 1
...
errors: [..] · warnings: [..] · signals: [..]
```

### CHECK-2 Text report

For each violation, the text report shall print `<file>:<line>: <severity> <rule>: <message>` and, on the next line, an indented `fix:` hint. Review signals shall print as `<file>:<line>: review <signal>: <message>`. The last line shall be the summary of errors, warnings and signals.

```console fixture=violations
$ bondstone check
? 1
...
[..]: error no-dangling-links: [..]
  fix: [..]
...
```

### CHECK-3 JSON report

With `--json`, `bondstone check` shall print exactly one JSON object on stdout and nothing else, with the keys `schema_version`, `summary`, `violations`, `signals`, `requirements`, `skipped` and `overridden`, in that order. On exit code 2 or 3, the object shall have only `schema_version` and `error`, an object with the exit code and a message.

```console
$ bondstone check --json
{"schema_version":1,"summary":{"errors":0,"warnings":0,"signals":0,"scope":"all"},[..]}
```

### CHECK-4 Deterministic output

Two runs on unchanged files shall produce byte-identical output, with violations sorted by file, line and rule.

- WHEN `bondstone check --json` runs twice on the same commit THEN both outputs are identical.

### CHECK-5 Scopes

`--all`, the default, shall evaluate every file in the working tree under the configured paths, including files git doesn't track yet. `--staged` shall evaluate the staged files, as they are in the git index, and their direct neighbours in the graph, and shall skip `requirement-covered` and `requirement-passing`, because test reports are build output that is missing or old at commit time. Outside a git repository, `--staged` shall be a usage error.

- WHEN only `docs/spec/sync.md` is staged THEN `bondstone check --staged` reports no violation located in another capability spec.
- WHEN a broken link is staged and then fixed in the working tree without staging the fix THEN `bondstone check --staged` still reports it.
- WHEN a staged test file names an untested requirement THEN `bondstone check --staged` reports no `requirement-passing` warning for it.

### CHECK-6 Overrides

Where `overrides` in `rules.yml` change a rule's severity or set it to `disabled`, Bondstone shall apply them and list each overridden rule in the JSON `overridden` field.

- WHEN `rules.yml` sets `overrides: {code-has-owner: disabled}` THEN no `code-has-owner` warning appears and `overridden` lists `code-has-owner`.

### CHECK-7 Invalid or unsafe configuration

If `rules.yml` or a pack fails schema validation, declares a `bondstone:` version this CLI doesn't know, or contains YAML that would construct objects, Bondstone shall exit with 2, name the field and its location, and evaluate nothing.

```console fixture=broken-config
$ bondstone check
? 2
.bondstone/rules.yml:[..]
```

### CHECK-8 Skipped rules

If a rule refers to a type that no active pack declares, Bondstone shall skip the rule and list it under `skipped` instead of failing. Evidence rules shall be skipped the same way when no test report exists, and `code-has-owner` outside a git repository.

- WHEN `rules.yml` sets `host: none` THEN `change-reflected` is listed under `skipped` and isn't evaluated.

### CHECK-9 Review signals

Judgement calls shall be reported as review signals, apart from violations, and shall never change the exit code on their own. Each signal is defined by the requirement that raises it, such as `not-reported` (EVIDENCE-8) and `stale-approval` (APPROVE-4).

- WHEN a test file references a requirement that no test case in the report names THEN `bondstone check` prints a `review not-reported` line and still exits with 0.

### CHECK-10 Performance

On the generated 500-document benchmark repository, `bondstone check --staged` shall finish in under 1 second and `bondstone check --all` in under 3 seconds, start-up included.

- WHEN the benchmark test runs in CI THEN it records both durations and fails if either exceeds its budget.

### CHECK-11 Release gate
Release: REL-0.2

With `--release`, Bondstone shall report as errors: every in-scope requirement that is not `passing` or `manual`, every approval the stages need that is missing or stale, a missing changelog section for the current release, and the absence of any test report.

```console fixture=release-gaps
$ bondstone check --release
? 1
...
[..]: error requirement-passing: [..]
...
```

### CHECK-12 Zero packs
Release: REL-0.2

Every command shall run with no packs active and report an empty project instead of failing.

```console fixture=empty
$ bondstone check
errors: 0 · warnings: 0 · signals: 0
$ bondstone next
Next: done[..]
```
