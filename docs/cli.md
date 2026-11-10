# CLI surface

One binary, `bondstone`. Every command accepts `--format text|json` and
`--config PATH` (default: `bondstone.yaml` found by walking up from the current
folder).

## Commands

### Checking

| Command | Purpose |
|---|---|
| `bondstone check [--base REF] [--only RULE...] [--profile NAME] [--fail-on error\|warn] [--format text\|json\|sarif]` | Run all rules. Without `--base`, only state rules run. With it, change rules, lifecycle transitions and freeze checks run against `REF..HEAD` plus the working tree. |
| `bondstone render [--check]` | Write generated views. `--check` writes nothing and fails if any view is stale. |
| `bondstone rules [--pack NAME]` | List active rules with their resolved severity and where it came from. |
| `bondstone explain RULE` | Show a rule's description, definition, a passing and a failing example, and the fix. |

### Authoring

These exist so that neither a person nor an agent has to invent a format.

| Command | Purpose |
|---|---|
| `bondstone new TYPE --title T [--set k=v...] [--link NAME=ID...]` | Create a document from the type's template with the next id, at the right path. |
| `bondstone move ID STATUS` | Change lifecycle status, refusing illegal transitions. |
| `bondstone supersede ID --title T` | Create the successor, link it, and move the old document to its superseded status. |
| `bondstone context (--for PATH... \| --base REF \| --id ID)` | List the documents relevant to a set of files or a change: documents anchored to those files, their linked decisions and requirements, and the change rules that will apply. |
| `bondstone graph [--format json\|mermaid\|dot] [--select ...]` | Export the document graph. |

### Project and packs

| Command | Purpose |
|---|---|
| `bondstone init [--pack SOURCE...] [--profile NAME]` | Create `bondstone.yaml`, the lockfile and empty views. |
| `bondstone pack add SOURCE` / `pack update [NAME]` | Add or update a pack and rewrite the lockfile. |
| `bondstone pack lint DIR` | Validate a pack: schema, references between types, links and rules. |
| `bondstone pack test DIR` | Run the pack against its `fixtures/` (sample repositories with expected diagnostics). |
| `bondstone pack migrate NAME` | Apply a pack's migrations after a major version bump. |
| `bondstone baseline` | Record current violations as the adoption baseline. |
| `bondstone waive RULE TARGET --reason R --expires DATE` | Add a waiver to the project file. |

### Integration

| Command | Purpose |
|---|---|
| `bondstone agent install --target claude-code\|agents-md\|speckit\|bmad` | Generate agent instructions, hooks and tool-specific templates from the active packs. See [adapters.md](adapters.md). |
| `bondstone hook pre-commit\|pre-push\|agent-stop` | Entry points for git hooks and agent stop hooks. Each runs `check` with the right base and prints agent-readable output. |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | No violations at or above `--fail-on` |
| 1 | Violations found |
| 2 | Configuration error: invalid project file, pack or lockfile |
| 3 | Environment error: `--base` ref not found, not a git repository |

Codes 2 and 3 are separate from 1 so that CI and agents can tell "the work is
wrong" from "the checker could not run".

## JSON output

`check --format json` prints one object:

```json
{
  "summary": {"errors": 2, "warnings": 0, "advisories": 1, "waived": 1, "baselined": 4},
  "diagnostics": [
    {
      "rule": "solo-app/code-change-updates-capability",
      "severity": "error",
      "kind": "change",
      "target": "CAP-reminders",
      "file": "lib/reminders/scheduler.dart",
      "line": null,
      "message": "Code anchored to CAP-reminders changed, but CAP-reminders did not.",
      "fix": {
        "hint": "Update the capability doc, or add the commit trailer 'Spec-Impact: none (<reason>)'.",
        "command": null,
        "files": ["docs/capabilities/reminders.md"]
      }
    }
  ]
}
```

Every diagnostic has a `fix`. `fix.command` is filled when a single bondstone command
resolves the violation (for example `bondstone render` or `bondstone new ...`), so
an agent can apply it without interpreting prose.

`context --format json` returns the same node shape as `graph`, limited to the
relevant documents, plus `rules`: the change rules that the current diff triggers.

## A typical agent loop

```text
bondstone context --for lib/reminders/     # what must I read, what rules apply?
... edit code and documents ...
bondstone new adr/decision --title "..."   # scaffold instead of hand-writing
bondstone render                           # regenerate views
bondstone check --base origin/main --format json
... apply fixes until exit code 0 ...
```
