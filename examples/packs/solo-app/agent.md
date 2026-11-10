## Capabilities and architecture

- Before changing code, run `bondstone context --for <paths>` and read the
  capability docs it lists. They describe what the app does today.
- When behaviour changes, update the capability doc in the same change: edit the
  affected requirement, or add one with the next `REQ-<KEY>-NNN` id.
- Mark the code that implements a requirement with a `@spec REQ-...` comment.
- If a code change has no effect on any spec (a refactor, a typo), say so with the
  commit trailer `Spec-Impact: none (<reason>)`.
- `docs/architecture.md` describes the system as it is, not as it was planned.
  Update it when a component, data store or external service is added or removed.
