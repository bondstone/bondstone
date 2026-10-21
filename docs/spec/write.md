---
type: spec
id: WRITE
title: Writing documents and links
description: How Bondstone creates documents, finds IDs and adds links so nobody types an ID or a link format by hand.
status: draft
components: [COMP-WRITE]
fixture: simple-app
---

# Writing documents and links

People and agents write the prose. Bondstone writes the structure: new documents from templates, the next free ID, and links in the place each relation is declared.

## Requirements

### WRITE-1 New documents

`bondstone new <type>` shall create a document from the type's template at its configured path, with front-matter `type`, `id`, `title`, `description` and the type's initial `status` (`proposed` for decisions, `draft` for the others), and print the path. With `--json`, it shall also print the path of the type's guidance file.

```console
$ bondstone new spec --id EXPORT --title "Data export"
docs/spec/export.md
```

### WRITE-2 Next free ID

`bondstone id next <type or capability>` shall print the next free ID without creating anything. For a capability, that is its prefix and one more than the highest number among its requirements, its retired IDs and the `Adds:` lines of unfinished changes; for decisions, the next four-digit number.

```console
$ bondstone id next SYNC
SYNC-[..]
```

- WHEN SYNC-11 is the highest requirement and SYNC-12 is listed under `retired` THEN `bondstone id next SYNC` prints `SYNC-13`.
- WHEN SYNC-11 is the highest requirement and an unfinished change says `Adds: SYNC-12` THEN `bondstone id next SYNC` prints `SYNC-13`.

### WRITE-3 Links

`bondstone link <from> <to>` shall add the link where the relation between those two types is declared (item line, link section or front-matter field), using the Markdown-link form in item lines and sections, and leave every other byte of the file unchanged.

- WHEN `bondstone link SYNC COMP-STORE` runs THEN COMP-STORE is added to the `components` list in the front-matter of `docs/spec/sync.md`, and the rest of the file is byte-identical.

### WRITE-4 Front-matter round trips

When Bondstone edits front-matter, it shall preserve unknown keys, comments and key order.

- WHEN `bondstone approve SYNC` edits a spec whose front-matter has a comment and an `owner:` key THEN both are unchanged afterwards.

### WRITE-5 Templates and guidance

The simple-app pack shall ship a template and an agent guidance file for the brief, the architecture page, capability specs and decisions. Templates shall contain no IDs except placeholders that `new` fills.

- WHEN `bondstone new decision --title "Use SQLite for the queue"` runs and ADR-0003 is the highest decision THEN `docs/decisions/0004-use-sqlite-for-the-queue.md` is created with `id: ADR-0004` and MADR's minimal sections.
