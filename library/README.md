# bondstone-library

Packs, bridges and presets for [bondstone](../README.md): the set bondstone documents itself with.

Installing this package makes its packs, bridges and presets available to every profile. Nothing is
loaded unless a profile names it, and a pack with the same id in one of the profile's own
`sources` folders wins over the copy here.

| Component | Kind | What it gives |
| --- | --- | --- |
| `adr` | pack | Decisions, with a lifecycle, supersession and immutability once accepted. |
| `capability` | pack | Living capability specs whose requirements are traced to code. |
| `adr-capability` | bridge | Capabilities are constrained by decisions; accepted decisions are applied. |
| `starter` | preset | The three above, and a rule that a change to tagged code updates the capability it implements (exempt with a `Spec-Impact` commit trailer). |

`bondstone packs` lists what is available in a repository, `bondstone init --preset starter`
starts a profile from the preset, and `bondstone pack test DIR...` runs a component's fixtures.

The package registers its folder under the entry point group `bondstone.sources`. Any other
package can do the same; the engine treats every registered folder like a folder in the
profile's `sources`.
