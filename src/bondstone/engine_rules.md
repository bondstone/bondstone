---
id: ENG-CATALOG
title: Engine rule catalog
status: draft
documents: [CAP-profiles, CAP-graph, CAP-rules, CAP-diff-checks, CAP-code-traceability, CAP-views]
---

## Purpose

Every diagnostic the engine itself emits. `bondstone explain bondstone/<rule>` reads this file.

## Rules

### ENG-001: bondstone/profile

Fires when: The profile, a pack or a bridge has a problem: a pack that is not found or whose version does not match, a bridge whose required packs are missing, unknown types, links or roles referenced by rules, invalid severities, or an override that tries to loosen a locked rule.

**Why:** Checks are only meaningful when the rules themselves are consistent.

**Fix:** Read the message; `bondstone profile check` lists only these problems.

**Severity:** error. Profiles may override it.

### ENG-002: bondstone/unbridged-packs

Fires when: The profile's packs form groups that no bridge connects.

**Why:** Unconnected packs produce islands of documents that nothing links together.

**Fix:** Add a bridge that requires packs from both groups, or remove a pack you do not use.

**Severity:** warn. Profiles may override it.

### ENG-003: bondstone/parse-error

Fires when: A document's frontmatter is not closed, is not valid YAML, or is not a mapping.

**Why:** Nothing else can be checked for an unreadable document.

**Fix:** Fix the YAML between the `---` lines.

**Severity:** error. Profiles may override it.

### ENG-004: bondstone/frontmatter-missing

Fires when: A file matches a type's `paths` but has no frontmatter.

**Why:** Files in typed folders are expected to be documents.

**Fix:** Add a frontmatter block, or create the file with `bondstone new`.

**Severity:** error. Profiles may override it.

### ENG-005: bondstone/unknown-type

Fires when: A document declares a `type:` that no active pack defines.

**Why:** The type decides every other check.

**Fix:** Use a qualified type from `bondstone rules`/`bondstone agent`, or add the pack to the profile.

**Severity:** error. Profiles may override it.

### ENG-006: bondstone/type-mismatch

Fires when: A document declares a `type:` that differs from the type its path implies.

**Why:** The same file would be checked under two different sets of rules.

**Fix:** Remove `type:` or move the file.

**Severity:** error. Profiles may override it.

### ENG-007: bondstone/type-ambiguous

Fires when: A file matches the `paths` of several types and declares none.

**Why:** Bondstone cannot tell which rules apply.

**Fix:** Add `type:` to the frontmatter.

**Severity:** error. Profiles may override it.

### ENG-008: bondstone/link-ambiguous

Fires when: A frontmatter key matches link names from several packs or bridges.

**Why:** The link could point to different kinds of documents.

**Fix:** Use the qualified name, e.g. `adr-capability:constrained_by`.

**Severity:** error. Profiles may override it.

### ENG-009: bondstone/item-heading

Fires when: A heading at an item level inside the item section does not match the item pattern, e.g. a level-3 heading under `## Requirements` that is not `REQ-...: title`.

**Why:** Malformed items would silently not be checked or traced.

**Fix:** Rename the heading to match the pattern or change its level.

**Severity:** error. Profiles may override it.

### ENG-010: bondstone/id-missing

Fires when: A document has no `id`.

**Why:** Links, tags and views all refer to ids.

**Fix:** Add `id:` following the type's id format.

**Severity:** error. Profiles may override it.

### ENG-011: bondstone/id-format

Fires when: An id does not match its type's `id_pattern`.

**Why:** Consistent ids keep links and code tags readable and unambiguous.

**Fix:** Rename the id (and update links to it).

**Severity:** error. Profiles may override it.

### ENG-012: bondstone/id-duplicate

Fires when: Two documents or items use the same id.

**Why:** Links and tags would be ambiguous.

**Fix:** Give one of them a new id.

**Severity:** error. Profiles may override it.

### ENG-013: bondstone/field-missing

Fires when: A required field is missing from the frontmatter.

**Why:** Required fields are part of the type's contract.

**Fix:** Add the field; `bondstone agent` lists the required fields per type.

**Severity:** error. Profiles may override it.

### ENG-014: bondstone/field-unknown

Fires when: A frontmatter key is neither a field, a trait key nor a link of the document's type.

**Why:** Unknown keys are usually typos of links, which would otherwise be silently ignored.

**Fix:** Use one of the fields or links listed in the hint.

**Severity:** error. Profiles may override it.

### ENG-015: bondstone/field-invalid

Fires when: A field value does not match the type's schema, e.g. an unknown status or a malformed date.

**Why:** Values outside the schema break views, rules and lifecycles.

**Fix:** Use a value allowed by the schema.

**Severity:** error. Profiles may override it.

### ENG-016: bondstone/todo-left

Fires when: A document still contains a `<!-- todo: ... -->` placeholder outside code. Warning in the initial status, error afterwards.

**Why:** Scaffolded placeholders must not survive into decided or published documents.

**Fix:** Replace every placeholder with real content.

**Severity:** warn/error. Profiles may override it.

### ENG-017: bondstone/section-missing

Fires when: A document lacks a section its type requires.

**Why:** Required sections carry the information the method depends on.

**Fix:** Add the heading (any level).

**Severity:** error. Profiles may override it.

### ENG-018: bondstone/link-broken

Fires when: A link points to an id that does not exist.

**Why:** Broken links are exactly the drift bondstone exists to prevent.

**Fix:** Fix the id or create the missing document.

**Severity:** error. Profiles may override it.

### ENG-019: bondstone/link-type

Fires when: A link points to a document of a type the link does not allow.

**Why:** Typed links keep relations meaningful.

**Fix:** Point the link at a document of an allowed type.

**Severity:** error. Profiles may override it.

### ENG-020: bondstone/link-self

Fires when: A document links to itself.

**Why:** Self-links carry no information and usually indicate a copy-paste mistake.

**Fix:** Remove or correct the link.

**Severity:** error. Profiles may override it.

### ENG-021: bondstone/link-min

Fires when: A document has fewer links of a kind than the link type requires.

**Why:** Some relations are mandatory, e.g. an opportunity must serve an outcome.

**Fix:** Add the links named in the message.

**Severity:** error. Profiles may override it.

### ENG-022: bondstone/link-max

Fires when: A document has more links of a kind than the link type allows.

**Why:** Some relations are singular, e.g. a decision supersedes at most one decision.

**Fix:** Remove the extra links.

**Severity:** error. Profiles may override it.

### ENG-023: bondstone/supersede-status

Fires when: A document is superseded by another but its status is not `superseded`.

**Why:** Readers must see that a document no longer applies.

**Fix:** Set `status: superseded`, or use `bondstone supersede`.

**Severity:** error. Profiles may override it.

### ENG-024: bondstone/supersede-multiple

Fires when: A document is superseded by more than one document.

**Why:** Supersession must form a single chain.

**Fix:** Supersede the newest document instead.

**Severity:** error. Profiles may override it.

### ENG-025: bondstone/supersede-orphan

Fires when: A document has status `superseded` but nothing supersedes it.

**Why:** Readers cannot find what replaced it.

**Fix:** Add `supersedes:` to its successor, or change its status.

**Severity:** warn. Profiles may override it.

### ENG-026: bondstone/supersede-cycle

Fires when: Supersession links form a cycle.

**Why:** A cycle has no current document.

**Fix:** Break the cycle.

**Severity:** error. Profiles may override it.

### ENG-027: bondstone/code-ref-unknown

Fires when: A code tag `bondstone: ID` refers to an id that does not exist.

**Why:** Tags to removed requirements are stale traceability.

**Fix:** Fix or remove the tag.

**Severity:** error. Profiles may override it.

### ENG-028: bondstone/code-ref-not-traceable

Fires when: A code tag refers to a node whose type is not code-traceable.

**Why:** Only some types (e.g. requirements) describe behaviour that code implements.

**Fix:** Tag the requirement instead of the document.

**Severity:** error. Profiles may override it.

### ENG-029: bondstone/code-coverage

Fires when: A code-traceable node is not referenced by any code tag. Severity comes from the trait's `coverage` setting.

**Why:** Untraced requirements may be unimplemented, or their code is not findable.

**Fix:** Add a `bondstone: ID` comment above the implementing code.

**Severity:** trait setting. Profiles may override it.

### ENG-030: bondstone/view-stale

Fires when: A generated view differs from what `bondstone gen` would write.

**Why:** Committed views must match the documents (ADR-006).

**Fix:** Run `bondstone gen` and commit the result.

**Severity:** error. Profiles may override it.

### ENG-031: bondstone/git

Fires when: Git cannot compare with the `--base` ref.

**Why:** Diff checks need the base commit.

**Fix:** Check the ref name and fetch it, e.g. `git fetch origin main`.

**Severity:** error. Profiles may override it.

### ENG-032: bondstone/status-transition

Fires when: With `--base`, a document's status changed in a way its lifecycle does not allow.

**Why:** Lifecycles encode review steps that must not be skipped.

**Fix:** Move through the allowed statuses in separate changes, as listed in the message.

**Severity:** error. Profiles may override it.

### ENG-033: bondstone/status-initial

Fires when: With `--base`, a new document does not start in a creation status (default: the initial status).

**Why:** New documents are reviewed before they are decided or activated.

**Fix:** Create it in the initial status and change it later, or set the baseline when adopting (`bondstone baseline`).

**Severity:** error. Profiles may override it.

### ENG-034: bondstone/immutable

Fires when: With `--base`, a document whose previous status is immutable was edited beyond its allowed fields.

**Why:** Decided documents are history; changing them rewrites it.

**Fix:** Create a successor with `bondstone supersede`.

**Severity:** error. Profiles may override it.

### ENG-035: bondstone/baseline-missing

Fires when: The profile's baseline commit is not available in the clone.

**Why:** Adopted documents cannot be compared without it.

**Fix:** Fetch full history (`fetch-depth: 0` in CI) or the commit itself.

**Severity:** error. Profiles may override it.

### ENG-036: bondstone/waiver-invalid

Fires when: A waiver has no `rule` or no `reason`.

**Why:** Every exception must be explained.

**Fix:** Add the missing key.

**Severity:** error. Profiles may override it.

### ENG-037: bondstone/waiver-expired

Fires when: A waiver's `expires` date has passed.

**Why:** Exceptions are temporary by design.

**Fix:** Fix the waived problem and remove the waiver, or renew it with a reason.

**Severity:** error. Profiles may override it.

### ENG-038: bondstone/waiver-unused

Fires when: A waiver matches no diagnostic.

**Why:** Unused waivers hide future problems.

**Fix:** Remove the waiver.

**Severity:** warn. Profiles may override it.
