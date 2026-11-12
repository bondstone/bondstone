<!-- bondstone:generated view=capability/requirements; do not edit, run `bondstone gen` -->
# Requirements

| Id | Title | Parent |
|---|---|---|
| [REQ-AGT-001](../capabilities/agent-guidance.md#req-agt-001-list-the-active-rules-with-their-effective-severity) | List the active rules with their effective severity | CAP-agent-guidance |
| [REQ-AGT-002](../capabilities/agent-guidance.md#req-agt-002-explain-one-rule) | Explain one rule | CAP-agent-guidance |
| [REQ-CLI-001](../capabilities/cli.md#req-cli-001-check-a-repository) | Check a repository | CAP-cli |
| [REQ-CLI-002](../capabilities/cli.md#req-cli-002-regenerate-views) | Regenerate views | CAP-cli |
| [REQ-CLI-003](../capabilities/cli.md#req-cli-003-check-the-configuration-alone) | Check the configuration alone | CAP-cli |
| [REQ-CLI-004](../capabilities/cli.md#req-cli-004-record-the-baseline) | Record the baseline | CAP-cli |
| [REQ-CLI-005](../capabilities/cli.md#req-cli-005-print-diagnostics-as-text) | Print diagnostics as text | CAP-cli |
| [REQ-CLI-006](../capabilities/cli.md#req-cli-006-print-diagnostics-as-versioned-json) | Print diagnostics as versioned JSON | CAP-cli |
| [REQ-CLI-007](../capabilities/cli.md#req-cli-007-tell-wrong-work-from-a-checker-that-could-not-run) | Tell wrong work from a checker that could not run | CAP-cli |
| [REQ-DIF-001](../capabilities/diff-checks.md#req-dif-001-read-history-through-git-only) | Read history through git only | CAP-diff-checks |
| [REQ-DIF-002](../capabilities/diff-checks.md#req-dif-002-compare-with-the-merge-base) | Compare with the merge base | CAP-diff-checks |
| [REQ-DIF-003](../capabilities/diff-checks.md#req-dif-003-see-committed-uncommitted-and-renamed-changes) | See committed, uncommitted and renamed changes | CAP-diff-checks |
| [REQ-DIF-004](../capabilities/diff-checks.md#req-dif-004-require-new-nodes-to-start-in-the-initial-status) | Require new nodes to start in the initial status | CAP-diff-checks |
| [REQ-DIF-005](../capabilities/diff-checks.md#req-dif-005-require-status-changes-to-follow-the-lifecycle) | Require status changes to follow the lifecycle | CAP-diff-checks |
| [REQ-DIF-006](../capabilities/diff-checks.md#req-dif-006-protect-immutable-documents) | Protect immutable documents | CAP-diff-checks |
| [REQ-DIF-007](../capabilities/diff-checks.md#req-dif-007-trigger-diff-rules-on-changed-paths-and-kinds) | Trigger diff rules on changed paths and kinds | CAP-diff-checks |
| [REQ-DIF-008](../capabilities/diff-checks.md#req-dif-008-evaluate-changed-exists-and-any-clauses) | Evaluate changed, exists and any clauses | CAP-diff-checks |
| [REQ-DIF-009](../capabilities/diff-checks.md#req-dif-009-trace-changed-code-regions-to-documents) | Trace changed code regions to documents | CAP-diff-checks |
| [REQ-DIF-010](../capabilities/diff-checks.md#req-dif-010-compare-with-the-baseline-when-a-document-is-new-at-the-base) | Compare with the baseline when a document is new at the base | CAP-diff-checks |
| [REQ-DIF-011](../capabilities/diff-checks.md#req-dif-011-let-a-commit-trailer-exempt-a-change) | Let a commit trailer exempt a change | CAP-diff-checks |
| [REQ-DIF-012](../capabilities/diff-checks.md#req-dif-012-reject-malformed-exemptions-and-allow-strict-runs) | Reject malformed exemptions and allow strict runs | CAP-diff-checks |
| [REQ-GRA-001](../capabilities/graph.md#req-gra-001-read-markdown-with-yaml-frontmatter) | Read Markdown with YAML frontmatter | CAP-graph |
| [REQ-GRA-002](../capabilities/graph.md#req-gra-002-derive-the-id-pattern-and-the-path-glob-from-templates) | Derive the id pattern and the path glob from templates | CAP-graph |
| [REQ-GRA-003](../capabilities/graph.md#req-gra-003-require-every-document-to-state-its-type) | Require every document to state its type | CAP-graph |
| [REQ-GRA-004](../capabilities/graph.md#req-gra-004-treat-the-docs-globs-as-managed-folders) | Treat the docs globs as managed folders | CAP-graph |
| [REQ-GRA-005](../capabilities/graph.md#req-gra-005-turn-item-headings-into-nodes) | Turn item headings into nodes | CAP-graph |
| [REQ-GRA-006](../capabilities/graph.md#req-gra-006-read-links-from-frontmatter) | Read links from frontmatter | CAP-graph |
| [REQ-GRA-007](../capabilities/graph.md#req-gra-007-check-that-ids-are-present-well-formed-and-unique) | Check that ids are present, well formed and unique | CAP-graph |
| [REQ-GRA-008](../capabilities/graph.md#req-gra-008-check-fields-and-sections-against-the-type) | Check fields and sections against the type | CAP-graph |
| [REQ-GRA-009](../capabilities/graph.md#req-gra-009-check-links-against-their-definition) | Check links against their definition | CAP-graph |
| [REQ-PRF-001](../capabilities/profiles.md#req-prf-001-validate-manifests-against-their-schemas) | Validate manifests against their schemas | CAP-profiles |
| [REQ-PRF-002](../capabilities/profiles.md#req-prf-002-reject-a-yaml-boolean-used-as-a-severity) | Reject a YAML boolean used as a severity | CAP-profiles |
| [REQ-PRF-003](../capabilities/profiles.md#req-prf-003-find-the-repository-root) | Find the repository root | CAP-profiles |
| [REQ-PRF-004](../capabilities/profiles.md#req-prf-004-resolve-packs-and-bridges-from-local-sources) | Resolve packs and bridges from local sources | CAP-profiles |
| [REQ-PRF-005](../capabilities/profiles.md#req-prf-005-check-what-a-bridge-requires) | Check what a bridge requires | CAP-profiles |
| [REQ-PRF-006](../capabilities/profiles.md#req-prf-006-check-what-a-schema-cannot-express) | Check what a schema cannot express | CAP-profiles |
| [REQ-PRF-007](../capabilities/profiles.md#req-prf-007-apply-overrides-and-respect-locked-rules) | Apply overrides and respect locked rules | CAP-profiles |
| [REQ-PRF-008](../capabilities/profiles.md#req-prf-008-apply-waivers-that-have-a-reason-and-an-expiry-date) | Apply waivers that have a reason and an expiry date | CAP-profiles |
| [REQ-PRF-009](../capabilities/profiles.md#req-prf-009-warn-about-packs-that-no-bridge-connects) | Warn about packs that no bridge connects | CAP-profiles |
| [REQ-PRF-010](../capabilities/profiles.md#req-prf-010-stop-on-a-configuration-error) | Stop on a configuration error | CAP-profiles |
| [REQ-RUL-001](../capabilities/rules.md#req-rul-001-select-nodes-with-selectors) | Select nodes with selectors | CAP-rules |
| [REQ-RUL-002](../capabilities/rules.md#req-rul-002-evaluate-node-rules) | Evaluate node rules | CAP-rules |
| [REQ-RUL-003](../capabilities/rules.md#req-rul-003-evaluate-existence-rules) | Evaluate existence rules | CAP-rules |
| [REQ-RUL-004](../capabilities/rules.md#req-rul-004-compare-a-field-with-a-value-in-another-file) | Compare a field with a value in another file | CAP-rules |
| [REQ-RUL-005](../capabilities/rules.md#req-rul-005-keep-a-catalogue-of-engine-rules) | Keep a catalogue of engine rules | CAP-rules |
| [REQ-RUL-006](../capabilities/rules.md#req-rul-006-check-the-status-of-nodes-with-a-lifecycle) | Check the status of nodes with a lifecycle | CAP-rules |
| [REQ-RUL-007](../capabilities/rules.md#req-rul-007-keep-supersession-consistent) | Keep supersession consistent | CAP-rules |
| [REQ-RUL-008](../capabilities/rules.md#req-rul-008-report-leftover-placeholders) | Report leftover placeholders | CAP-rules |
| [REQ-RUL-009](../capabilities/rules.md#req-rul-009-make-every-diagnostic-actionable) | Make every diagnostic actionable | CAP-rules |
| [REQ-TRC-001](../capabilities/code-traceability.md#req-trc-001-find-tags-in-code) | Find tags in code | CAP-code-traceability |
| [REQ-TRC-002](../capabilities/code-traceability.md#req-trc-002-know-the-region-of-code-a-tag-annotates) | Know the region of code a tag annotates | CAP-code-traceability |
| [REQ-TRC-003](../capabilities/code-traceability.md#req-trc-003-reject-tags-that-point-nowhere) | Reject tags that point nowhere | CAP-code-traceability |
| [REQ-TRC-004](../capabilities/code-traceability.md#req-trc-004-report-uncovered-nodes-in-the-statuses-that-need-code) | Report uncovered nodes in the statuses that need code | CAP-code-traceability |
| [REQ-TRC-005](../capabilities/code-traceability.md#req-trc-005-warn-about-tags-on-retired-nodes) | Warn about tags on retired nodes | CAP-code-traceability |
| [REQ-TRC-006](../capabilities/code-traceability.md#req-trc-006-give-items-a-status-of-their-own) | Give items a status of their own | CAP-code-traceability |
| [REQ-TRC-007](../capabilities/code-traceability.md#req-trc-007-let-rules-ask-whether-a-node-is-covered) | Let rules ask whether a node is covered | CAP-code-traceability |
| [REQ-VIE-001](../capabilities/views.md#req-vie-001-render-table-views) | Render table views | CAP-views |
| [REQ-VIE-002](../capabilities/views.md#req-vie-002-render-tree-views) | Render tree views | CAP-views |
| [REQ-VIE-003](../capabilities/views.md#req-vie-003-write-only-the-views-that-changed) | Write only the views that changed | CAP-views |
| [REQ-VIE-004](../capabilities/views.md#req-vie-004-fail-the-check-on-a-stale-view) | Fail the check on a stale view | CAP-views |
| [REQ-VIE-005](../capabilities/views.md#req-vie-005-mark-generated-files) | Mark generated files | CAP-views |
