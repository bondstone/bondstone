# Constraining Spec Kit, BMAD and coding agents

Bondstone does not replace these tools. It constrains them at two points: what they
are told to produce, and whether what they produced is accepted.

## 1. Shape the output

`bondstone agent install --target <tool>` generates tool-specific files from the
active packs, so the templates a tool uses and the rules bondstone enforces come
from one source.

| Target | What is generated |
|---|---|
| `agents-md` | A marked section in `AGENTS.md`: document types, where they live, the commands to use (`context`, `new`, `render`, `check`) and each pack's `agent.guidance`. |
| `claude-code` | The same guidance as a skill, plus a stop hook that runs `bondstone hook agent-stop` so a session cannot end while `check` fails. |
| `speckit` | Template overrides and a preset that add bondstone frontmatter and links to Spec Kit's spec, plan and task templates, plus a final task telling the agent to update the living docs and run `bondstone check`. |
| `bmad` | A custom module with the same additions for BMAD's planning and story artifacts. |

The Spec Kit and BMAD targets depend on those tools' customization mechanisms,
which change between versions. Each adapter should declare the tool versions it
was tested with and refuse to install on others.

## 2. Treat their artifacts as documents

Per-change artifacts from these tools become ordinary bondstone types in an
"intake" pack, with looser rules than living docs. A sketch for Spec Kit
(paths must be checked against the installed version):

```yaml
pack: speckit-intake
version: 0.1.0
bondstone: ">=0.1"
description: Treats Spec Kit feature specs as change records.
requires: {solo-app: "^0.1"}

types:
  feature-spec:
    description: A Spec Kit feature specification.
    path: "specs/{id}/spec.md"
    id: "{seq:3}-{slug}"
    frontmatter:
      required: [title]
      properties:
        title: {type: string}

links:
  changes:
    description: The capabilities this feature adds to or modifies.
    from: feature-spec
    to: solo-app/capability
    min: 1

rules:
  - id: feature-updates-its-capabilities
    description: When a feature's code lands, every capability it changes is updated.
    severity: error
    on_change: {paths: ["lib/**"]}
    require:
      touched: {type: solo-app/capability, anchored: true, min: 1}
    unless:
      trailer: "Spec-Impact: none"
    fix: "Update each capability listed under `changes:` in the feature spec."
```

The feature spec is the per-change record; the capability document is the living
spec. The `changes` link and the change rule are what force the first to be folded
into the second.

## 3. Gate the result

| Where | Command | Effect |
|---|---|---|
| Agent stop hook | `bondstone hook agent-stop` | The agent gets the JSON diagnostics and keeps working until they are resolved. |
| `pre-commit` | `bondstone hook pre-commit` | State rules and `render --check` on staged files. |
| `pre-push` | `bondstone hook pre-push` | Change rules against the upstream branch. |
| CI | `bondstone check --base origin/$BASE --format sarif` | The authoritative gate; SARIF shows diagnostics inline on the pull request. |

The agent hook is a convenience and the CI gate is the guarantee: an agent can skip
or misconfigure its own hook, but it cannot merge past CI.
