<!-- bondstone:generated view=speckit-capability/delivery; do not edit, run `bondstone gen` -->
# Requirements and the features that deliver them

| Id | Title | Status | Parent | ← Delivers |
|---|---|---|---|---|
| [REQ-AGT-001](../capabilities/agent-guidance.md#req-agt-001-list-the-active-rules-with-their-effective-severity) | List the active rules with their effective severity | active | CAP-agent-guidance |  |
| [REQ-AGT-002](../capabilities/agent-guidance.md#req-agt-002-explain-one-rule) | Explain one rule | active | CAP-agent-guidance |  |
| [REQ-AGT-003](../capabilities/agent-guidance.md#req-agt-003-say-what-to-read-before-editing) | Say what to read before editing | active | CAP-agent-guidance |  |
| [REQ-AGT-004](../capabilities/agent-guidance.md#req-agt-004-say-which-diff-rules-will-fire) | Say which diff rules will fire | active | CAP-agent-guidance |  |
| [REQ-AGT-005](../capabilities/agent-guidance.md#req-agt-005-generate-the-instructions-for-agents) | Generate the instructions for agents | active | CAP-agent-guidance |  |
| [REQ-AGT-006](../capabilities/agent-guidance.md#req-agt-006-offer-the-instructions-as-a-skill) | Offer the instructions as a skill | active | CAP-agent-guidance |  |
| [REQ-AGT-007](../capabilities/agent-guidance.md#req-agt-007-export-the-graph) | Export the graph | active | CAP-agent-guidance |  |
| [REQ-CLI-001](../capabilities/cli.md#req-cli-001-check-a-repository) | Check a repository | active | CAP-cli |  |
| [REQ-CLI-002](../capabilities/cli.md#req-cli-002-regenerate-views) | Regenerate views | active | CAP-cli |  |
| [REQ-CLI-003](../capabilities/cli.md#req-cli-003-check-the-configuration-alone) | Check the configuration alone | active | CAP-cli |  |
| [REQ-CLI-004](../capabilities/cli.md#req-cli-004-record-the-baseline) | Record the baseline | active | CAP-cli |  |
| [REQ-CLI-005](../capabilities/cli.md#req-cli-005-print-diagnostics-as-text) | Print diagnostics as text | active | CAP-cli |  |
| [REQ-CLI-006](../capabilities/cli.md#req-cli-006-print-diagnostics-as-versioned-json) | Print diagnostics as versioned JSON | active | CAP-cli |  |
| [REQ-CLI-007](../capabilities/cli.md#req-cli-007-tell-wrong-work-from-a-checker-that-could-not-run) | Tell wrong work from a checker that could not run | active | CAP-cli |  |
| [REQ-CLI-008](../capabilities/cli.md#req-cli-008-report-where-the-documentation-stands) | Report where the documentation stands | active | CAP-cli | [004-waive-and-report](../../specs/004-waive-and-report/spec.md) |
| [REQ-CLI-009](../capabilities/cli.md#req-cli-009-say-in-json-why-a-command-stopped) | Say in JSON why a command stopped | active | CAP-cli | [004-waive-and-report](../../specs/004-waive-and-report/spec.md) |
| [REQ-DIF-001](../capabilities/diff-checks.md#req-dif-001-read-history-through-git-only) | Read history through git only | active | CAP-diff-checks |  |
| [REQ-DIF-002](../capabilities/diff-checks.md#req-dif-002-compare-with-the-merge-base) | Compare with the merge base | active | CAP-diff-checks |  |
| [REQ-DIF-003](../capabilities/diff-checks.md#req-dif-003-see-committed-uncommitted-and-renamed-changes) | See committed, uncommitted and renamed changes | active | CAP-diff-checks |  |
| [REQ-DIF-004](../capabilities/diff-checks.md#req-dif-004-require-new-nodes-to-start-in-the-initial-status) | Require new nodes to start in the initial status | active | CAP-diff-checks |  |
| [REQ-DIF-005](../capabilities/diff-checks.md#req-dif-005-require-status-changes-to-follow-the-lifecycle) | Require status changes to follow the lifecycle | active | CAP-diff-checks |  |
| [REQ-DIF-006](../capabilities/diff-checks.md#req-dif-006-protect-immutable-documents) | Protect immutable documents | active | CAP-diff-checks |  |
| [REQ-DIF-007](../capabilities/diff-checks.md#req-dif-007-trigger-diff-rules-on-changed-paths-and-kinds) | Trigger diff rules on changed paths and kinds | active | CAP-diff-checks |  |
| [REQ-DIF-008](../capabilities/diff-checks.md#req-dif-008-evaluate-changed-exists-and-any-clauses) | Evaluate changed, exists and any clauses | active | CAP-diff-checks |  |
| [REQ-DIF-009](../capabilities/diff-checks.md#req-dif-009-trace-changed-code-regions-to-documents) | Trace changed code regions to documents | active | CAP-diff-checks |  |
| [REQ-DIF-010](../capabilities/diff-checks.md#req-dif-010-compare-with-the-baseline-when-a-document-is-new-at-the-base) | Compare with the baseline when a document is new at the base | active | CAP-diff-checks |  |
| [REQ-DIF-011](../capabilities/diff-checks.md#req-dif-011-let-a-commit-trailer-exempt-a-change) | Let a commit trailer exempt a change | active | CAP-diff-checks |  |
| [REQ-DIF-012](../capabilities/diff-checks.md#req-dif-012-reject-malformed-exemptions-and-allow-strict-runs) | Reject malformed exemptions and allow strict runs | active | CAP-diff-checks |  |
| [REQ-DIF-013](../capabilities/diff-checks.md#req-dif-013-trigger-diff-rules-on-the-repositorys-code) | Trigger diff rules on the repository's code | active | CAP-diff-checks |  |
| [REQ-DIF-014](../capabilities/diff-checks.md#req-dif-014-count-a-change-to-a-companion-file-as-a-change-to-the-document) | Count a change to a companion file as a change to the document | active | CAP-diff-checks | [001-spec-kit-adapter](../../specs/001-spec-kit-adapter/spec.md) |
| [REQ-DIF-015](../capabilities/diff-checks.md#req-dif-015-ask-that-the-link-targets-of-a-changed-node-change-too) | Ask that the link targets of a changed node change too | active | CAP-diff-checks | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-GRA-001](../capabilities/graph.md#req-gra-001-read-markdown-with-yaml-frontmatter) | Read Markdown with YAML frontmatter | active | CAP-graph |  |
| [REQ-GRA-002](../capabilities/graph.md#req-gra-002-derive-the-id-pattern-and-the-path-glob-from-templates) | Derive the id pattern and the path glob from templates | active | CAP-graph |  |
| [REQ-GRA-003](../capabilities/graph.md#req-gra-003-require-every-document-to-state-its-type) | Require every document to state its type | active | CAP-graph |  |
| [REQ-GRA-004](../capabilities/graph.md#req-gra-004-treat-the-docs-globs-as-managed-folders) | Treat the docs globs as managed folders | active | CAP-graph |  |
| [REQ-GRA-005](../capabilities/graph.md#req-gra-005-turn-item-headings-into-nodes) | Turn item headings into nodes | active | CAP-graph |  |
| [REQ-GRA-006](../capabilities/graph.md#req-gra-006-read-links-from-frontmatter) | Read links from frontmatter | active | CAP-graph |  |
| [REQ-GRA-007](../capabilities/graph.md#req-gra-007-check-that-ids-are-present-well-formed-and-unique) | Check that ids are present, well formed and unique | active | CAP-graph |  |
| [REQ-GRA-008](../capabilities/graph.md#req-gra-008-check-fields-and-sections-against-the-type) | Check fields and sections against the type | active | CAP-graph |  |
| [REQ-GRA-009](../capabilities/graph.md#req-gra-009-check-links-against-their-definition) | Check links against their definition | active | CAP-graph |  |
| [REQ-GRA-010](../capabilities/graph.md#req-gra-010-require-the-path-to-carry-the-id) | Require the path to carry the id | active | CAP-graph | [001-spec-kit-adapter](../../specs/001-spec-kit-adapter/spec.md) |
| [REQ-GRA-011](../capabilities/graph.md#req-gra-011-derive-a-status-from-files) | Derive a status from files | active | CAP-graph | [001-spec-kit-adapter](../../specs/001-spec-kit-adapter/spec.md) |
| [REQ-KNV-001](../capabilities/known-violations.md#req-knv-001-record-the-current-violations) | Record the current violations | active | CAP-known-violations | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-KNV-002](../capabilities/known-violations.md#req-knv-002-identify-a-violation-without-line-numbers) | Identify a violation without line numbers | active | CAP-known-violations | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-KNV-003](../capabilities/known-violations.md#req-knv-003-report-a-known-violation-as-info) | Report a known violation as info | active | CAP-known-violations | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-KNV-004](../capabilities/known-violations.md#req-knv-004-report-entries-that-match-nothing) | Report entries that match nothing | active | CAP-known-violations | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-KNV-005](../capabilities/known-violations.md#req-knv-005-prune-without-adding) | Prune without adding | active | CAP-known-violations | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-KNV-006](../capabilities/known-violations.md#req-knv-006-catch-a-file-that-grew) | Catch a file that grew | active | CAP-known-violations | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-KNV-007](../capabilities/known-violations.md#req-knv-007-let-a-rule-refuse-known-violations) | Let a rule refuse known violations | active | CAP-known-violations | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-KNV-008](../capabilities/known-violations.md#req-knv-008-reject-a-malformed-file) | Reject a malformed file | active | CAP-known-violations | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-LIB-001](../capabilities/library.md#req-lib-001-document-commands-with-the-cli-pack) | Document commands with the cli pack | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-LIB-002](../capabilities/library.md#req-lib-002-tie-commands-to-capabilities) | Tie commands to capabilities | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-LIB-003](../capabilities/library.md#req-lib-003-record-releases-and-generate-the-changelog) | Record releases and generate the changelog | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-LIB-004](../capabilities/library.md#req-lib-004-tie-releases-to-features) | Tie releases to features | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-LIB-005](../capabilities/library.md#req-lib-005-ship-every-component-with-fixtures) | Ship every component with fixtures | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-LIB-006](../capabilities/library.md#req-lib-006-record-decisions-with-the-adr-pack) | Record decisions with the adr pack | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-LIB-007](../capabilities/library.md#req-lib-007-keep-living-capability-specs-with-the-capability-pack) | Keep living capability specs with the capability pack | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-LIB-008](../capabilities/library.md#req-lib-008-tie-capabilities-to-decisions) | Tie capabilities to decisions | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-LIB-009](../capabilities/library.md#req-lib-009-start-a-repository-with-the-starter-preset) | Start a repository with the starter preset | active | CAP-library | [002-cli-and-release-packs](../../specs/002-cli-and-release-packs/spec.md) |
| [REQ-PKT-001](../capabilities/pack-tooling.md#req-pkt-001-run-the-fixtures-of-a-pack-a-bridge-or-a-preset) | Run the fixtures of a pack, a bridge or a preset | active | CAP-pack-tooling |  |
| [REQ-PKT-002](../capabilities/pack-tooling.md#req-pkt-002-compare-a-fixture-with-what-it-expects) | Compare a fixture with what it expects | active | CAP-pack-tooling |  |
| [REQ-PKT-003](../capabilities/pack-tooling.md#req-pkt-003-list-the-packs-bridges-and-presets-that-are-available) | List the packs, bridges and presets that are available | active | CAP-pack-tooling |  |
| [REQ-PRF-001](../capabilities/profiles.md#req-prf-001-validate-manifests-against-their-schemas) | Validate manifests against their schemas | active | CAP-profiles |  |
| [REQ-PRF-002](../capabilities/profiles.md#req-prf-002-reject-a-yaml-boolean-used-as-a-severity) | Reject a YAML boolean used as a severity | active | CAP-profiles |  |
| [REQ-PRF-003](../capabilities/profiles.md#req-prf-003-find-the-repository-root) | Find the repository root | active | CAP-profiles |  |
| [REQ-PRF-004](../capabilities/profiles.md#req-prf-004-resolve-packs-and-bridges-from-local-sources) | Resolve packs and bridges from local sources | active | CAP-profiles |  |
| [REQ-PRF-005](../capabilities/profiles.md#req-prf-005-check-what-a-bridge-requires) | Check what a bridge requires | active | CAP-profiles |  |
| [REQ-PRF-006](../capabilities/profiles.md#req-prf-006-check-what-a-schema-cannot-express) | Check what a schema cannot express | active | CAP-profiles |  |
| [REQ-PRF-007](../capabilities/profiles.md#req-prf-007-apply-overrides-and-respect-locked-rules) | Apply overrides and respect locked rules | active | CAP-profiles |  |
| [REQ-PRF-008](../capabilities/profiles.md#req-prf-008-apply-waivers-that-have-a-reason-and-an-expiry-date) | Apply waivers that have a reason and an expiry date | active | CAP-profiles |  |
| [REQ-PRF-009](../capabilities/profiles.md#req-prf-009-warn-about-packs-that-no-bridge-connects) | Warn about packs that no bridge connects | active | CAP-profiles |  |
| [REQ-PRF-010](../capabilities/profiles.md#req-prf-010-stop-on-a-configuration-error) | Stop on a configuration error | active | CAP-profiles |  |
| [REQ-PRF-011](../capabilities/profiles.md#req-prf-011-resolve-packs-and-bridges-from-installed-packages) | Resolve packs and bridges from installed packages | active | CAP-profiles |  |
| [REQ-PRF-012](../capabilities/profiles.md#req-prf-012-create-a-profile) | Create a profile | active | CAP-profiles |  |
| [REQ-PRF-013](../capabilities/profiles.md#req-prf-013-extend-presets) | Extend presets | active | CAP-profiles |  |
| [REQ-PRF-014](../capabilities/profiles.md#req-prf-014-apply-severities-in-layers) | Apply severities in layers | active | CAP-profiles |  |
| [REQ-PRF-015](../capabilities/profiles.md#req-prf-015-let-a-preset-lock-rules) | Let a preset lock rules | active | CAP-profiles |  |
| [REQ-PRF-016](../capabilities/profiles.md#req-prf-016-add-a-waiver-from-the-command-line) | Add a waiver from the command line | active | CAP-profiles | [004-waive-and-report](../../specs/004-waive-and-report/spec.md) |
| [REQ-RUL-001](../capabilities/rules.md#req-rul-001-select-nodes-with-selectors) | Select nodes with selectors | active | CAP-rules |  |
| [REQ-RUL-002](../capabilities/rules.md#req-rul-002-evaluate-node-rules) | Evaluate node rules | active | CAP-rules |  |
| [REQ-RUL-003](../capabilities/rules.md#req-rul-003-evaluate-existence-rules) | Evaluate existence rules | active | CAP-rules |  |
| [REQ-RUL-004](../capabilities/rules.md#req-rul-004-compare-a-field-with-a-value-in-another-file) | Compare a field with a value in another file | active | CAP-rules |  |
| [REQ-RUL-005](../capabilities/rules.md#req-rul-005-keep-a-catalogue-of-engine-rules) | Keep a catalogue of engine rules | active | CAP-rules |  |
| [REQ-RUL-006](../capabilities/rules.md#req-rul-006-check-the-status-of-nodes-with-a-lifecycle) | Check the status of nodes with a lifecycle | active | CAP-rules |  |
| [REQ-RUL-007](../capabilities/rules.md#req-rul-007-keep-supersession-consistent) | Keep supersession consistent | active | CAP-rules |  |
| [REQ-RUL-008](../capabilities/rules.md#req-rul-008-report-leftover-placeholders) | Report leftover placeholders | active | CAP-rules |  |
| [REQ-RUL-009](../capabilities/rules.md#req-rul-009-make-every-diagnostic-actionable) | Make every diagnostic actionable | active | CAP-rules |  |
| [REQ-SCF-001](../capabilities/scaffolding.md#req-scf-001-scaffold-a-document-at-the-right-id-and-path) | Scaffold a document at the right id and path | active | CAP-scaffolding |  |
| [REQ-SCF-002](../capabilities/scaffolding.md#req-scf-002-write-a-document-that-passes-the-check) | Write a document that passes the check | active | CAP-scaffolding |  |
| [REQ-SCF-003](../capabilities/scaffolding.md#req-scf-003-change-a-status-within-the-lifecycle) | Change a status within the lifecycle | active | CAP-scaffolding |  |
| [REQ-SCF-004](../capabilities/scaffolding.md#req-scf-004-supersede-a-document) | Supersede a document | active | CAP-scaffolding |  |
| [REQ-SCF-005](../capabilities/scaffolding.md#req-scf-005-edit-only-the-lines-that-change) | Edit only the lines that change | active | CAP-scaffolding |  |
| [REQ-SCF-006](../capabilities/scaffolding.md#req-scf-006-regenerate-views-after-an-edit) | Regenerate views after an edit | active | CAP-scaffolding |  |
| [REQ-SKT-001](../capabilities/spec-kit-adapter.md#req-skt-001-read-a-spec-kit-feature-folder-as-one-node) | Read a Spec Kit feature folder as one node | active | CAP-spec-kit-adapter | [001-spec-kit-adapter](../../specs/001-spec-kit-adapter/spec.md) |
| [REQ-SKT-002](../capabilities/spec-kit-adapter.md#req-skt-002-add-the-frontmatter-through-a-spec-kit-preset) | Add the frontmatter through a Spec Kit preset | active | CAP-spec-kit-adapter | [001-spec-kit-adapter](../../specs/001-spec-kit-adapter/spec.md) |
| [REQ-SKT-003](../capabilities/spec-kit-adapter.md#req-skt-003-fold-an-implemented-feature-into-the-capabilities) | Fold an implemented feature into the capabilities | active | CAP-spec-kit-adapter | [001-spec-kit-adapter](../../specs/001-spec-kit-adapter/spec.md) |
| [REQ-SKT-004](../capabilities/spec-kit-adapter.md#req-skt-004-rest-an-implemented-feature-on-accepted-decisions) | Rest an implemented feature on accepted decisions | active | CAP-spec-kit-adapter | [001-spec-kit-adapter](../../specs/001-spec-kit-adapter/spec.md) |
| [REQ-SKT-005](../capabilities/spec-kit-adapter.md#req-skt-005-ask-for-a-feature-when-code-changes) | Ask for a feature when code changes | active | CAP-spec-kit-adapter | [001-spec-kit-adapter](../../specs/001-spec-kit-adapter/spec.md) |
| [REQ-SKT-006](../capabilities/spec-kit-adapter.md#req-skt-006-update-the-capabilities-when-an-implemented-feature-changes) | Update the capabilities when an implemented feature changes | active | CAP-spec-kit-adapter | [003-known-violations](../../specs/003-known-violations/spec.md) |
| [REQ-TRC-001](../capabilities/code-traceability.md#req-trc-001-find-tags-in-code) | Find tags in code | active | CAP-code-traceability |  |
| [REQ-TRC-002](../capabilities/code-traceability.md#req-trc-002-know-the-region-of-code-a-tag-annotates) | Know the region of code a tag annotates | active | CAP-code-traceability |  |
| [REQ-TRC-003](../capabilities/code-traceability.md#req-trc-003-reject-tags-that-point-nowhere) | Reject tags that point nowhere | active | CAP-code-traceability |  |
| [REQ-TRC-004](../capabilities/code-traceability.md#req-trc-004-report-uncovered-nodes-in-the-statuses-that-need-code) | Report uncovered nodes in the statuses that need code | active | CAP-code-traceability |  |
| [REQ-TRC-005](../capabilities/code-traceability.md#req-trc-005-warn-about-tags-on-retired-nodes) | Warn about tags on retired nodes | active | CAP-code-traceability |  |
| [REQ-TRC-006](../capabilities/code-traceability.md#req-trc-006-give-items-a-status-of-their-own) | Give items a status of their own | active | CAP-code-traceability |  |
| [REQ-TRC-007](../capabilities/code-traceability.md#req-trc-007-let-rules-ask-whether-a-node-is-covered) | Let rules ask whether a node is covered | active | CAP-code-traceability |  |
| [REQ-VIE-001](../capabilities/views.md#req-vie-001-render-table-views) | Render table views | active | CAP-views |  |
| [REQ-VIE-002](../capabilities/views.md#req-vie-002-render-tree-views) | Render tree views | active | CAP-views |  |
| [REQ-VIE-003](../capabilities/views.md#req-vie-003-write-only-the-views-that-changed) | Write only the views that changed | active | CAP-views |  |
| [REQ-VIE-004](../capabilities/views.md#req-vie-004-fail-the-check-on-a-stale-view) | Fail the check on a stale view | active | CAP-views |  |
| [REQ-VIE-005](../capabilities/views.md#req-vie-005-mark-generated-files) | Mark generated files | active | CAP-views |  |
| [REQ-VIE-006](../capabilities/views.md#req-vie-006-show-linked-nodes-in-table-columns) | Show linked nodes in table columns | active | CAP-views |  |
| [REQ-VIE-007](../capabilities/views.md#req-vie-007-render-matrix-views) | Render matrix views | active | CAP-views |  |
