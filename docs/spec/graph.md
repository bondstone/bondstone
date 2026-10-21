---
type: spec
id: GRAPH
title: Document graph
description: How Bondstone finds items and links in a repository.
status: draft
components: [COMP-GRAPH, COMP-CONFIG]
fixture: simple-app
---

# Document graph

Bondstone reads Markdown documents, host change folders and the git file list, and builds one graph of items and links that every other capability uses. Only declared structure counts: an ID mentioned in prose is prose, and an example inside a code block never becomes an item.

## Requirements

### GRAPH-1 Document items

A Markdown file whose front-matter has an `id` shall become an item of the type its pack declares for that file's path.

- WHEN `docs/spec/sync.md` has front-matter `id: SYNC` THEN the graph has a spec item SYNC located in that file.

### GRAPH-2 Inline items

An ATX heading that starts with an ID of a type allowed inside its document shall become an inline item with file and line. So shall a `-`, `*` or `1.` list item (task items included), where the pack allows list items for that type; elsewhere a list item that starts with an ID is prose. The ID may be wrapped in bold, code or link text. The item's parent shall be the nearest preceding item heading of a lower level, whatever the list indentation.

- WHEN line 18 of `docs/spec/sync.md` is `### SYNC-2 Offline entries sync without loss` THEN `bondstone check --json` lists requirement SYNC-2 with that file and line 18.
- WHEN a pack allows `TASK` list items in a document and a list item reads `- [ ] **TASK-3** Write the importer` THEN TASK-3 is an item whose parent is the item heading above it.
- WHEN a list item in `docs/spec/sync.md` reads `- SYNC-3 must ship first` THEN it is prose and `unique-ids` passes.

### GRAPH-3 Misplaced items and titles

If a heading starts with an ID whose type is not allowed in that document, Bondstone shall not register it and shall report a `misplaced-item` warning. A heading that starts with the document's own ID shall be treated as its title, not as an item. A token shaped like an ID whose type no active pack declares, such as Spec Kit's `FR-001`, is plain text.

```console fixture=violations
$ bondstone check
? 1
...
[..]: warning misplaced-item: [..]
...
```

### GRAPH-4 Item lines

The first paragraph after an item heading, with blank lines in between allowed, shall be read as item lines when every one of its lines starts with a `Name:` that the item's type declares. A line may hold several pairs separated by ` · `; Bondstone shall split only where the next segment starts with a declared name. A value may be wrapped in a code span, which Bondstone reads as its text. Item lines belong to heading items only.

- WHEN `### SYNC-2 …` is followed by a blank line and `Release: REL-0.2 · Check: manual` THEN SYNC-2's release is REL-0.2 and its check is manual.
- WHEN a component heading is followed by ``Paths: `src/sync/**` · Technology: SQLite`` THEN the component owns the files matching `src/sync/**`.
- WHEN that first paragraph also contains a sentence of prose THEN none of its lines are read as item lines.

### GRAPH-5 Link values

A relation's value shall be a comma-separated list of IDs, or of Markdown links whose text is an ID. Any other token shall raise a `bad-link-value` error.

```console fixture=violations
$ bondstone check
? 1
...
[..]: error bad-link-value: [..]
...
```

### GRAPH-6 Misspelled item-line names

A line or ` · ` segment in the item-line position whose name is not declared, but is within two edits of a declared name, shall raise an `unknown-item-line` warning that suggests the declared name. Other undeclared names shall be ignored.

- WHEN a requirement heading is followed by `Relase: REL-0.2` THEN `bondstone check` warns `unknown-item-line` and suggests `Release`.
- WHEN a release heading is followed by `Capabilities: SYNC · Apetite: 2 weeks` THEN `bondstone check` warns `unknown-item-line` and suggests `Appetite`.

### GRAPH-7 Link sections

Where a pack declares a link section for a type, such as `## Spec changes` in a Spec Kit `spec.md`, declared `Name:` lines anywhere in that section, outside code blocks, shall be read as links of that item, with the same value rules as item lines.

- WHEN `specs/007-photo-upload/spec.md` ends with `## Spec changes` and the line `Adds: SYNC-9` THEN the change `007-photo-upload` links to SYNC-9.

### GRAPH-8 Front-matter relations

Front-matter fields that a type declares as relations, such as `components` on a capability spec, shall be read as links, with the same value rules as item lines.

- WHEN `docs/spec/sync.md` has `components: [COMP-SYNC]` in its front-matter and the architecture has no COMP-SYNC THEN `bondstone check` reports a `no-dangling-links` error for that field.

### GRAPH-9 Skipped regions

Bondstone shall ignore fenced code blocks, HTML comments and blockquotes when finding items and links, and shall not treat setext headings (underlined with `===` or `---`) as item headings.

- WHEN `docs/architecture.md` shows `### COMP-SYNC …` inside a fenced code block THEN there is no second COMP-SYNC item and `unique-ids` passes.

### GRAPH-10 IDs in prose

An ID anywhere other than front-matter relations, item lines, link sections and test evidence shall not be treated as a link.

- WHEN a paragraph says "see SYNC-99" and SYNC-99 does not exist THEN no `no-dangling-links` error is reported.

### GRAPH-11 Malformed front-matter

If a document's front-matter can't be parsed, Bondstone shall report a `parse-error` for that file and go on scanning the others.

```console fixture=violations
$ bondstone check
? 1
...
[..]: error parse-error: [..]
...
```

### GRAPH-12 Spec Kit changes

Where `host: speckit` is configured, each folder under `specs/` whose name starts with a number or a `YYYYMMDD-HHMMSS` timestamp, then a hyphen, shall become a change item named by the folder, holding its `spec.md`, `plan.md` and `tasks.md`. Bondstone shall read only the change's `## Spec changes` section and count the checked and unchecked tasks in `tasks.md`.

- WHEN `specs/007-photo-upload/tasks.md` has 6 checked and 5 unchecked tasks THEN the change `007-photo-upload` has 6 of 11 tasks done.
- WHEN `specs/007-photo-upload/spec.md` lists `FR-001` to `FR-012` THEN the graph has no item for any of them.

### GRAPH-13 Computed reverse links
Release: REL-0.2

Links shall be stored only in their forward direction; every reverse view shall be computed from the graph.

- WHEN `docs/spec/sync.md` names COMP-SYNC in `components` THEN `bondstone context COMP-SYNC` lists SYNC as a user of the component, although `docs/architecture.md` doesn't mention SYNC.
