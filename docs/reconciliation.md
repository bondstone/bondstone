# Reconciling the design sketch with the POC

Status: done on branch `proof-of-concept` · Compared: commit `27947aa` (sketch) with branch `POC` at `ba2e808`

Two designs for bondstone existed side by side: the working implementation on `POC`, and
a paper sketch written without knowledge of it (file formats, CLI surface, example
packs, no code). This document records how they were merged into one.

## Outcome

- **The POC is the design.** It runs, is tested, and documents itself. Where the two
  disagreed on something both covered, the POC's answer is kept; the table below says why.
- **The sketch's files are removed** from this branch: its format and CLI documents, its
  JSON Schemas and its example packs described formats that no engine reads.
- **The one thing the sketch had and the POC lacked as content is ported**: a TOGAF-lite
  pack with bridges to `ost` and `adr`, now in the POC's format, with fixtures, in
  [`examples/team-product`](../examples/team-product).
- **Ideas from the sketch that the POC does not implement are listed** in
  [Candidates](#candidates-for-change-proposals). None is implemented here: in this
  repository an engine change starts with a change proposal.
- **Two defects in the POC were found** while porting. See [Defects](#defects-found).

## Where the designs differed

| Topic | Sketch | POC | Kept | Why |
|---|---|---|---|---|
| Repository config | `bondstone.yaml` in the root | `.bondstone/profile.yaml` | POC | Same content; the POC also keeps local packs under `.bondstone/`. |
| Connecting packs | A bridge is a pack with `requires`; ordinary packs may also require packs | Separate `bridge.yaml`; packs never require packs (ADR-003) | POC | The sketch's `togaf-lite` and `solo-app` packs required `adr`, so neither could be used without it. Porting moved those links into bridges and the pack became independent. |
| Generic rules | Rules always name concrete types | Traits and roles (ADR-004) | POC | A role such as `living-spec` lets one diff rule work for any pack combination. The sketch needed a copy of that rule in every pack. |
| Diff rules | Live in packs with paths such as `lib/**` built in | Live in the profile | POC | Source paths belong to the repository, not to the method. |
| Tying docs to code | Path globs in frontmatter, plus optional code tags | Code tags and the code region below each tag | POC | Tags give finer tracing than globs and need no list to maintain. |
| Links to decisions | Authored on the decision (`affects`), with an exception so frozen documents can still gain links | Authored on the document that can change (`constrained_by`) | POC | No exception to immutability is needed. |
| Lifecycle | `lifecycle` with a `frozen` list | Traits `lifecycle`, `immutable`, `supersedable` | POC | Equivalent, and supersession is checked by the engine. |
| Empty-shell detection | `min_words` per section | `bondstone/todo-left` and `contains` | POC | Catches unfilled templates without a word count that filler text can satisfy. |
| Unknown frontmatter keys | Not specified | Errors | POC | |
| Severity presets | Named profiles (`solo`, `team`) defined inside packs | Overrides in the profile | POC | The two examples show the same effect: `habit-tracker` loosens `ost/committed-solution-has-evidence`, `team-product` tightens it. |
| Adoption baseline | A file of existing violations | A baseline commit (ADR-008) | POC | They solve different problems; see candidate 7. |
| Views | `table`, `tree`, `matrix`; inverse link names | `table`, `tree` with `levels` | POC | See candidate 4. |
| Manifest validation | JSON Schema files | `bondstone profile check` | POC | `profile check` also validates references between components, which a schema cannot. |
| Command names | `render`, `pack lint`, `agent install` | `gen`, `profile check`, `agent` | POC | |

They agreed on the rest: Markdown with YAML frontmatter, a typed graph with embedded
items, rules stored in the repository, state rules and diff rules, generated views checked
for staleness, scaffolding, waivers with a reason, namespaced rule ids, fixtures for packs,
a deterministic gate, and no workflow of its own.

## What was ported

`examples/team-product` is a product team using Opportunity Solution Tree discovery,
TOGAF-lite architecture and ADRs. The `togaf-lite` pack and the `ost-togaf-lite` and
`adr-togaf-lite` bridges are custom components in the example's `.bondstone/packs`, so
the example also shows how a repository defines its own method.

Changes made while porting from the sketch's format:

| Sketch | Ported as | Reason |
|---|---|---|
| One `building-block` type with a `kind` field | `ArchitectureBlock` and `SolutionBlock` | Only solution blocks are implemented by code, and `code-traceable` is set per type. |
| `affects`: decision → building block | `constrained_by`: building block → decision | Accepted decisions are immutable. |
| `togaf-lite` requires `adr` | Bridge `adr-togaf-lite` | Packs do not know each other. |
| Rule "code change updates its building block" inside the pack | Profile rule using role `living-spec` with `traced: true` | Diff rules belong to the profile. |
| Matrix view of requirements × blocks | Tree view requirement → architecture block → solution block | No matrix renderer. |
| Link columns in table views | Dropped | Table views render fields only; see candidate 4. |
| Rule "a new building block needs a decision" | Rule "a live solution block has an accepted decision" (warn) | Diff rules cannot tell added files from modified ones; see candidate 5. |
| Commit-trailer exemption on diff rules | Dropped | Not available; see candidate 2. |
| Profiles `solo` / `team` / `organisation` | Overrides in the example profile | See the table above. |

Not ported: the sketch's `solo-app` pack. The built-in `capability` and `adr` packs with
`examples/habit-tracker` already cover that case better.

## Candidates for change proposals

Ideas from the sketch that the POC does not have, most valuable first. Each would start
as a `change:Proposal`.

1. **`bondstone context`.** Given paths or a diff, list the documents an agent should read
   before editing: the documents traced to that code, the decisions and requirements
   linked to them, and the diff rules that will fire. Today an agent learns this only
   from a failed `check`.
2. **A declared exemption for diff rules.** A refactor inside a tagged region fails
   `changed … traced: true` unless the spec is edited or the profile is weakened. A
   commit trailer such as `Spec-Impact: none (<reason>)`, opted into per rule, keeps the
   gate deterministic and leaves the exemption in history where it can be counted.
3. **Coverage that depends on status.** `code-traceable.coverage` applies to every node
   of a type. "A planned solution block needs no code yet, a live one does" cannot be
   expressed: `covered` exists as a selector but not as a requirement on the node itself.
4. **Links in views.** Table columns that name a link render empty. Showing link targets
   (and incoming links) would make catalogue views useful; a `matrix` renderer would give
   a real traceability matrix.
5. **Change kinds in `on_change`.** `change: [added]` or `[deleted]` would allow rules
   such as "a new building block comes with a decision" or "deleting a service retires
   its block".
6. **A machine-applicable fix in JSON output.** `hint` is prose. A `fix.command` field,
   filled when one bondstone command resolves the diagnostic (`bondstone gen`,
   `bondstone supersede …`), lets an agent act without interpreting text.
7. **Grandfathering existing violations.** The baseline commit handles lifecycle history
   when adopting bondstone. It does not help a repository whose existing documents break
   many rules; the choices are to fix everything first or write one waiver per document.
8. **Non-blocking review tier.** The sketch had an `advisory` severity and `exec` rules
   for LLM-judged checks. ADR-005 keeps `check` deterministic, so this would be a separate
   command, not a severity.
9. **Smaller conveniences.** SARIF output for pull-request annotations; a command to
   change status that refuses illegal transitions before the edit is made; a check for
   untyped files in document folders; generic `acyclic` links; section order.
10. **Generated templates for Spec Kit and BMAD.** The POC plans an adapter pack and Spec
    Kit hooks. The sketch adds one idea: generate the tools' template overrides from the
    active packs, so what they produce and what `check` accepts come from one source.

Already on the POC roadmap and therefore not repeated here: lock file, remote pack
sources, pack migrations, portfolio aggregation.

## Defects found

Neither is fixed on this branch.

1. **A bare `off` is rejected.** YAML reads `off` as `false`, so the override shown in
   `docs/design.md`,

   ```yaml
   overrides:
     ost/committed-solution-has-evidence: {severity: off}
   ```

   fails with `bondstone/profile: … invalid severity 'False'`. With
   `code-traceable: {coverage: off}` the coverage diagnostics are still printed, with
   severity `False`, although they do not fail the run. Quoting (`'off'`) works, and the
   fixtures do that. Either the loader should accept `false`, or
   the documentation should show the quotes.
2. **`bondstone rules` and the generated agent instructions ignore overrides.** They
   print each rule's own severity. In `examples/team-product` the profile raises
   `togaf-lite/approved-requirement-is-motivated` to `error` and `check` enforces that,
   but `bondstone rules` and `AGENTS.bondstone.md` say `warn`. `bondstone rules --format json`
   is correct.
