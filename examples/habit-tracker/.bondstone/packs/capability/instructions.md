- `docs/capabilities/` describes what the system does **today**. When a change alters
  behaviour, update the affected capability in the same change; do not leave it for later.
- Add requirements as `### REQ-<CODE>-NNN: title` under `## Requirements`, never renumber
  existing ones, and remove requirements that no longer hold.
- Mark the code that implements a requirement with a comment `bondstone: REQ-<CODE>-NNN`.
- A requirement whose code arrives in the same change is active: write no `Status:` line.
  Write `Status: planned` under the heading only when the requirement has no code yet, and
  `Status: removed` when it no longer holds but its code is still there.
