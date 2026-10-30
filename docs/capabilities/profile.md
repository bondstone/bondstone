---
type: capability
id: PROFILE
title: simple-app profile
description: The living docs, change docs, IDs, deltas, stories, evidence and phases of the simple-app workflow, and the rules that check them.
status: draft
retired: []
---

# simple-app profile

simple-app is Bondstone's first profile, for small apps and tools such as Bondstone itself. It keeps two layers of documents: **living docs** in `docs/` describe the product as it is and as planned and are kept forever; **change docs** in `plan/` and Spec Kit's `specs/` describe one piece of work and are archived or frozen when it ships. The layers meet through deltas: a version PRD's added requirements land in the capability specs when it is approved, and its modified and removed ones land in the commit of the story that changes the code. ADR-0008 records the design; in release 0.0 the Spec Kit extension's stopgap applies it.

| Rule | Checks | Severity |
| --- | --- | --- |
| `parse-error` | Front-matter, version status, delta and story-table syntax | error |
| `unique-ids` | No ID appears twice; no retired ID returns | error |
| `no-dangling-links` | Releases, pending markers, PRD versions, story proves and dependencies, spec proves point at existing items | error |
| `requirement-has-example` | Every requirement has an example with WHEN and THEN | error |
| `example-id-scoped` | Example IDs carry their requirement's ID | error |
| `requirement-has-release` | Every requirement has a `Release:` line | error |
| `delta-applied` | An approved PRD's deltas are reflected in the capability specs | error |
| `delta-has-story` | Every MODIFIED or REMOVED delta has a story | error |
| `story-status-stale` | A story table's status column matches the computed status | warning |
| `test-links-unknown-id` | A test name carries an ID that is no example | warning |
| `requirement-covered` | Every in-scope requirement's examples have tests | warning |
| `requirement-passing` | Every in-scope requirement's tests pass | warning |

The SPECKIT capability adds the rules for Spec Kit folders.

## Requirements

### PROFILE-1 Documents
Release: V-0.0

The profile shall read these documents. Each living doc and each change doc except Spec Kit's is Markdown whose front-matter follows Open Knowledge Format 0.2 with `type`, `id`, `title`, `description` and `status`, where `status` is `draft`, `stable` (approved) or `deprecated`. A missing key or another status is a `parse-error`; keys the profile doesn't use are ignored.

| Layer | Type | ID | Path |
| --- | --- | --- | --- |
| living | `brief` | `BRIEF` | `docs/brief.md` |
| living | `roadmap` | `ROADMAP` | `docs/roadmap.md` |
| living | `ideas` | `IDEAS` | `docs/ideas.md` |
| living | `glossary` | `GLOSSARY` | `docs/glossary.md` |
| living | `architecture` | `ARCH` | `docs/architecture/overview.md` |
| living | `capability` | its prefix, such as `SYNC` | `docs/capabilities/*.md` |
| living | `decision` | `ADR-` and four digits | `docs/decisions/*.md` |
| living | `screens` | `SCREENS` | `docs/ux/screens.md` |
| living | `runbook` | `RUNBOOK` | `docs/runbook.md` |
| change | `prd` | `PRD-<version>` | `plan/<version>/prd.md`, archived in `plan/archive/<version>/` |
| change | `epic` | `EP-<n>` | `plan/<version>/epics/*.md` |
| change | `release` | `RELEASE-<version>` | `plan/<version>/release.md` |

- PROFILE-1.1: WHEN a decision has `status: proposed` THEN a `parse-error` is reported for it.
- PROFILE-1.2: WHEN a decision has an extra `owner:` key THEN nothing is reported about it.

### PROFILE-2 Roadmap and versions
Release: V-0.0

Each `### V-<semver>` heading in the roadmap shall be a version, in the roadmap's order, with a `Status:` item line of `planned`, `active` or `shipped`. The current version shall be the first one not shipped, or the last one when all are shipped. The roadmap is extended in place; shipped versions stay.

- PROFILE-2.1: WHEN V-1.0 is shipped and V-1.1 is planned THEN the current version is V-1.1.
- PROFILE-2.2: WHEN a version has `Status: beta` THEN a `parse-error` is reported.

### PROFILE-3 Requirements and examples
Release: V-0.0

A heading in a capability spec that starts with the spec's prefix, a hyphen and a number shall be a requirement. The first paragraph after it holds item lines when every line is `Name: value` pairs joined by ` · `: `Release:`, `Check:` (`auto` or `manual`), `Pending:` and `Verified:`. A requirement shall have a statement and at least one example: a list item that starts with the example's ID and contains WHEN and THEN. Example IDs shall be the requirement ID, a dot and a number; a requirement with a single example may use its plain ID. Removed requirement and example IDs go to the spec's `retired` list and never return.

- PROFILE-3.1: WHEN a requirement has no example THEN `requirement-has-example` is reported.
- PROFILE-3.2: WHEN SYNC-1 has an example `SYNC-3.2` THEN `example-id-scoped` is reported.
- PROFILE-3.3: WHEN SYNC-1 has two examples and one uses the plain ID THEN `example-id-scoped` is reported.
- PROFILE-3.4: WHEN SYNC-2 is listed under `retired` and still written THEN `unique-ids` is reported.
- PROFILE-3.5: WHEN `### SYNC-2 …` is followed by `Release: V-1.1 · Check: manual` THEN SYNC-2's release is V-1.1 and its check is manual.

### PROFILE-4 Scope
Release: V-0.0

Every requirement shall carry its release, a version in the roadmap. A requirement shall be in scope when its release is the current version or comes before it, so the capability spec shows shipped and planned behavior together.

- PROFILE-4.1: WHEN V-1.0 is current THEN a requirement of V-1.0 is in scope and one of V-1.1 is not.
- PROFILE-4.2: WHEN a requirement has no `Release:` line THEN `requirement-has-release` is reported.
- PROFILE-4.3: WHEN a requirement's release is not in the roadmap THEN `no-dangling-links` is reported.

### PROFILE-5 Evidence
Release: V-0.0

The stopgap shall read JUnit XML reports, by default `build/test-results/*.xml`, and test files, and never production code. A test carries an example when its name has a capability prefix with no letter or digit before it, `-` or `_`, the requirement number, and optionally `.` or `_` and the example number, with no digit after it. A name that carries `SYNC_2_1` proves SYNC-2.1 when that example exists, and otherwise SYNC-2's single plain example. Each example shall be `untested`, `linked` (tests in files, no result), `passing` or `failing`; a requirement is `passing` when every example passes, `failing` when any fails, and `manual` when marked `Check: manual` with a `Verified:` line and no failure.

- PROFILE-5.1: WHEN `test_SYNC_1_1_kept` passed in the report THEN SYNC-1.1 is passing.
- PROFILE-5.2: WHEN a test is named `test_ASYNC_2_retry` THEN no test is linked to SYNC-2.
- PROFILE-5.3: WHEN SYNC-2 has one plain example and `test_SYNC_2_1_notice` passed THEN SYNC-2 is passing.
- PROFILE-5.4: WHEN SYNC-1.1 passes and SYNC-1.2 has no test THEN SYNC-1 is not passing.
- PROFILE-5.5: WHEN one test of SYNC-1.1 passes and another fails THEN SYNC-1 is failing.
- PROFILE-5.6: WHEN a test file names SYNC-2 and no report exists THEN SYNC-2 is linked.
- PROFILE-5.7: WHEN a test name carries SYNC-7.1 and no such example exists THEN `test-links-unknown-id` is reported.

### PROFILE-6 Version PRD: added, deferred and dropped
Release: V-0.0

A version PRD shall list its deltas in `## Deltas` as `ADDED:`, `MODIFIED:`, `REMOVED:`, `DEFERRED: <IDs> to V-<x>` and `DROPPED:` lines. Once the PRD is approved, each ADDED requirement shall be in a capability spec with the PRD's version as its release, each DEFERRED one shall carry the target release, and each DROPPED one shall be deleted and retired. Before approval, a PRD's ADDED IDs may be named by its stories without existing yet.

- PROFILE-6.1: WHEN an approved PRD adds SYNC-3 and no capability spec has it THEN `delta-applied` is reported.
- PROFILE-6.2: WHEN a draft PRD adds SYNC-3 and a story proves it THEN nothing is reported.
- PROFILE-6.3: WHEN an approved PRD defers SYNC-2 to V-1.1 THEN `delta-applied` is reported until SYNC-2 says `Release: V-1.1`.
- PROFILE-6.4: WHEN an approved PRD drops SYNC-2 THEN `delta-applied` is reported until SYNC-2 is deleted and retired.

### PROFILE-7 Modified and removed land with the story
Release: V-0.0

Each MODIFIED or REMOVED delta of an approved PRD shall have a story that lists the ID under `Proves` or `Removes`. Until that story is finished, the requirement keeps its old wording and carries `Pending: PRD-<version>`, so the capability spec never describes behavior the code lacks. When it is finished, a modified requirement has its new wording and no pending marker, and a removed one is deleted and retired.

- PROFILE-7.1: WHEN an approved PRD modifies SYNC-1 and its story is unfinished THEN `delta-applied` is reported until SYNC-1 carries `Pending: PRD-1.1`.
- PROFILE-7.2: WHEN the story that modifies SYNC-1 is finished and the marker remains THEN `delta-applied` is reported.
- PROFILE-7.3: WHEN the story that removes SYNC-2 is finished and SYNC-2 is not retired THEN `delta-applied` is reported.
- PROFILE-7.4: WHEN an approved PRD modifies SYNC-1 and no story proves it THEN `delta-has-story` is reported.

### PROFILE-8 Stories
Release: V-0.0

A `## Stories` table in a version PRD, or in an optional epic, shall list stories with `ID` (`ST-<n>`, numbered across versions), `Title`, `Proves`, and optionally `Removes`, `Depends on` and `Status` columns. A story's status shall be computed: `done` when its Spec Kit folder is finished, `in progress` when it has one, `ready` when its PRD is approved and the stories it depends on are done, otherwise `blocked`.

- PROFILE-8.1: WHEN ST-2 depends on ST-1 and neither has a folder THEN ST-1 is ready and ST-2 is blocked.
- PROFILE-8.2: WHEN ST-1's row says done and ST-1 is not finished THEN `story-status-stale` is reported.
- PROFILE-8.3: WHEN two rows use ST-1 THEN `unique-ids` is reported.
- PROFILE-8.4: WHEN an epic EP-1 has a story table THEN its stories belong to EP-1 and its PRD.

### PROFILE-9 Phases
Release: V-0.0

The profile shall compute these phases on every run; none is stored. Phases 0 to 2 happen once; 6, 3 and 4 repeat for every version after the first; 5 runs alongside from the first release.

| Phase | Done when |
| --- | --- |
| 0 Inception | The brief is approved and has no errors |
| 1 Shape | The roadmap, the architecture overview and the first version's PRD are approved |
| 2 Foundation | The constitution has no template placeholders, the runbook exists, and a test passes in the JUnit report |
| 6 Next version | The current version's PRD is approved |
| 3 Build | Every story of the current PRD is done and every in-scope requirement is passing or manual |
| 4 Release | The release checklist is signed off, the changelog has the version's section, and the roadmap marks it shipped |
| 5 Operate | Running once any version is shipped |

- PROFILE-9.1: WHEN the brief is approved THEN Inception is done, and WHEN it is a draft THEN Inception is open on approving it.
- PROFILE-9.2: WHEN the first PRD is a draft THEN Shape is open on approving it.
- PROFILE-9.3: WHEN no test passes in the report THEN Foundation is open.
- PROFILE-9.4: WHEN every story is done and every in-scope requirement passes THEN Build is done and Release is open on the release checklist.
- PROFILE-9.5: WHEN V-1.0 is shipped and V-1.1 has no PRD THEN Next version is open on writing it.
