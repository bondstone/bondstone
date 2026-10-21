---
type: spec
id: APPROVE
title: Approvals and manual verification
description: How a person approves documents and verifies requirements that no test can check, and how Bondstone notices when those go stale.
status: draft
components: [COMP-WRITE, COMP-STAGES]
fixture: simple-app
---

# Approvals and manual verification

Approval is the human act in Bondstone: a person approves what the app should do (the brief, the architecture, capability specs and decisions) and confirms the few requirements no test can check. Both are recorded on the item, with a hash, so a later edit makes them visibly stale.

## Requirements

### APPROVE-1 Approve a document

`bondstone approve <ID>` shall set the document's `status` to its approved value (`stable` for the brief, the architecture page and capability specs, `accepted` for decisions) and write `verified` with the actor, a UTC timestamp and a hash of the approved text.

```console
$ bondstone approve SYNC --yes
Approved SYNC (docs/spec/sync.md) as human:adam
```

### APPROVE-2 No approval while rules fail

If the document or any of its items has an error violation, `bondstone approve` shall refuse, list the violations and exit with 1.

```console fixture=violations
$ bondstone approve SYNC --yes
? 1
Refused: [..]
...
```

### APPROVE-3 A person at the keyboard

If `bondstone approve` or `bondstone verify` runs without an interactive terminal and without `--yes`, it shall refuse and exit with 2. When `CLAUDE_CODE_CHILD_SESSION` is set, as Claude Code does in the shells it runs, both shall refuse and exit with 2 even with `--yes`.

```console
$ bondstone approve SYNC
? 2
[..]--yes[..]
```

- WHEN an agent's shell, where `CLAUDE_CODE_CHILD_SESSION` is set, runs `bondstone approve SYNC --yes` THEN it exits with 2 and says that approvals are for people.

### APPROVE-4 Stale approvals

An approval shall be current only while its hash matches the document's text. A stale approval, or a `status` of `stable` or `accepted` without a `verified` field, shall raise a `stale-approval` review signal. The hash shall be `sha256-v1:` followed by the SHA-256 of a canonical form: the front-matter fields except `status` and `verified`, as JSON with sorted keys, then the body as UTF-8 without a byte-order mark, with `\n` line endings, in Unicode NFC, without trailing whitespace and without `Verified:` lines. A new canonical form shall get a new version prefix, and Bondstone shall keep checking hashes written with earlier ones.

- WHEN an approved SYNC spec gains a requirement THEN `bondstone check` prints `review stale-approval` for SYNC, `bondstone status` shows its approval as stale, and `bondstone next` asks to approve SYNC again.
- WHEN a decision has `status: accepted` and no `verified` field THEN `bondstone check` prints `review stale-approval` for it.
- WHEN only comments or key order change in an approved spec's front-matter THEN its approval stays current.
- WHEN `bondstone verify SYNC-7` adds a `Verified:` line to an approved spec THEN the spec's approval stays current.

### APPROVE-5 Manual verification

`bondstone verify <ID>` shall add a `Verified:` item line after the other item lines of a requirement marked `Check: manual`, replacing any earlier one, with the actor, a UTC timestamp and the hash of the requirement's block: its lines from the heading to the next heading of the same or a higher level, without `Verified:` lines, hashed as in APPROVE-4. It shall refuse with exit code 2 for any other requirement.

- WHEN SYNC-7 is marked `Check: manual` and Adam runs `bondstone verify SYNC-7` THEN a line `Verified: human:adam <timestamp> <hash>` appears under its heading and SYNC-7 becomes `manual`.

### APPROVE-6 Actor

The actor shall be `human:` followed by the local part of git's `user.email`, unless `BONDSTONE_ACTOR` is set. Without either, `approve` and `verify` shall refuse with exit code 2.

- WHEN git's `user.email` is `adam@example.com` THEN approvals record `human:adam`.
