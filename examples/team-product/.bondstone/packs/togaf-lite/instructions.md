- Architecture is described in two layers: an `ArchitectureBlock` says what is needed, a
  `SolutionBlock` says what is built. Every solution block `realizes` at least one
  architecture block.
- Tag the code of a solution block with `bondstone: SBB-<name>` at the top of its entry
  module. When that code changes, update the solution block document in the same change.
- A requirement becomes `satisfied` only after an approved architecture block lists it
  under `satisfies`. Do not mark it satisfied because the code exists.
- Create documents as `draft` / `planned` and move them on in a later change.
