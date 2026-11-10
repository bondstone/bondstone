<!-- bondstone:generated view=capability/requirements; do not edit, run `bondstone gen` -->
# Requirements

| Id | Title | Parent |
|---|---|---|
| [REQ-AGT-001](../capabilities/agent-instructions.md#req-agt-001-generate-instructions) | Generate instructions | CAP-agent-instructions |
| [REQ-AGT-002](../capabilities/agent-instructions.md#req-agt-002-explain-rules) | Explain rules | CAP-agent-instructions |
| [REQ-AGT-003](../capabilities/agent-instructions.md#req-agt-003-machine-readable-results) | Machine-readable results | CAP-agent-instructions |
| [REQ-DIF-001](../capabilities/diff-checks.md#req-dif-001-enforce-status-transitions) | Enforce status transitions | CAP-diff-checks |
| [REQ-DIF-002](../capabilities/diff-checks.md#req-dif-002-protect-immutable-documents) | Protect immutable documents | CAP-diff-checks |
| [REQ-DIF-003](../capabilities/diff-checks.md#req-dif-003-start-new-documents-in-a-creation-status) | Start new documents in a creation status | CAP-diff-checks |
| [REQ-DIF-004](../capabilities/diff-checks.md#req-dif-004-follow-renames) | Follow renames | CAP-diff-checks |
| [REQ-DIF-005](../capabilities/diff-checks.md#req-dif-005-run-on-change-rules) | Run on-change rules | CAP-diff-checks |
| [REQ-DIF-006](../capabilities/diff-checks.md#req-dif-006-require-the-traced-specs-to-change) | Require the traced specs to change | CAP-diff-checks |
| [REQ-DIF-007](../capabilities/diff-checks.md#req-dif-007-compare-adopted-documents-with-the-baseline) | Compare adopted documents with the baseline | CAP-diff-checks |
| [REQ-DIF-008](../capabilities/diff-checks.md#req-dif-008-report-a-missing-baseline-commit) | Report a missing baseline commit | CAP-diff-checks |
| [REQ-DIF-009](../capabilities/diff-checks.md#req-dif-009-set-the-baseline) | Set the baseline | CAP-diff-checks |
| [REQ-GRA-001](../capabilities/graph.md#req-gra-001-determine-document-types) | Determine document types | CAP-graph |
| [REQ-GRA-002](../capabilities/graph.md#req-gra-002-reject-unknown-frontmatter-keys) | Reject unknown frontmatter keys | CAP-graph |
| [REQ-GRA-003](../capabilities/graph.md#req-gra-003-extract-embedded-items) | Extract embedded items | CAP-graph |
| [REQ-GRA-004](../capabilities/graph.md#req-gra-004-resolve-links-by-name) | Resolve links by name | CAP-graph |
| [REQ-GRA-005](../capabilities/graph.md#req-gra-005-validate-link-targets) | Validate link targets | CAP-graph |
| [REQ-GRA-006](../capabilities/graph.md#req-gra-006-enforce-unique-and-well-formed-ids) | Enforce unique and well-formed ids | CAP-graph |
| [REQ-LIB-001](../capabilities/built-in-library.md#req-lib-001-decision-records) | Decision records | CAP-built-in-library |
| [REQ-LIB-002](../capabilities/built-in-library.md#req-lib-002-product-discovery) | Product discovery | CAP-built-in-library |
| [REQ-LIB-003](../capabilities/built-in-library.md#req-lib-003-living-capability-specs) | Living capability specs | CAP-built-in-library |
| [REQ-LIB-004](../capabilities/built-in-library.md#req-lib-004-change-proposals) | Change proposals | CAP-built-in-library |
| [REQ-LIB-005](../capabilities/built-in-library.md#req-lib-005-releases-and-changelog) | Releases and changelog | CAP-built-in-library |
| [REQ-LIB-006](../capabilities/built-in-library.md#req-lib-006-bridges-between-built-in-packs) | Bridges between built-in packs | CAP-built-in-library |
| [REQ-PKT-001](../capabilities/pack-testing.md#req-pkt-001-run-fixtures) | Run fixtures | CAP-pack-testing |
| [REQ-PKT-002](../capabilities/pack-testing.md#req-pkt-002-test-the-local-version) | Test the local version | CAP-pack-testing |
| [REQ-PRF-001](../capabilities/profiles.md#req-prf-001-resolve-packs-and-bridges-by-version) | Resolve packs and bridges by version | CAP-profiles |
| [REQ-PRF-002](../capabilities/profiles.md#req-prf-002-validate-bridge-requirements) | Validate bridge requirements | CAP-profiles |
| [REQ-PRF-003](../capabilities/profiles.md#req-prf-003-override-severities-except-locked-rules) | Override severities except locked rules | CAP-profiles |
| [REQ-PRF-004](../capabilities/profiles.md#req-prf-004-waive-diagnostics-with-a-reason) | Waive diagnostics with a reason | CAP-profiles |
| [REQ-PRF-005](../capabilities/profiles.md#req-prf-005-warn-about-unbridged-packs) | Warn about unbridged packs | CAP-profiles |
| [REQ-PRF-006](../capabilities/profiles.md#req-prf-006-assign-roles-only-in-bridges-and-profiles) | Assign roles only in bridges and profiles | CAP-profiles |
| [REQ-RUL-001](../capabilities/rules.md#req-rul-001-select-nodes) | Select nodes | CAP-rules |
| [REQ-RUL-002](../capabilities/rules.md#req-rul-002-evaluate-requirement-clauses) | Evaluate requirement clauses | CAP-rules |
| [REQ-RUL-003](../capabilities/rules.md#req-rul-003-validate-frontmatter-against-the-type-schema) | Validate frontmatter against the type schema | CAP-rules |
| [REQ-RUL-004](../capabilities/rules.md#req-rul-004-check-supersession) | Check supersession | CAP-rules |
| [REQ-RUL-005](../capabilities/rules.md#req-rul-005-require-sections) | Require sections | CAP-rules |
| [REQ-RUL-006](../capabilities/rules.md#req-rul-006-flag-unfinished-placeholders) | Flag unfinished placeholders | CAP-rules |
| [REQ-RUL-007](../capabilities/rules.md#req-rul-007-select-by-code-coverage) | Select by code coverage | CAP-rules |
| [REQ-SCF-001](../capabilities/scaffolding.md#req-scf-001-assign-the-next-id) | Assign the next id | CAP-scaffolding |
| [REQ-SCF-002](../capabilities/scaffolding.md#req-scf-002-pre-fill-required-frontmatter) | Pre-fill required frontmatter | CAP-scaffolding |
| [REQ-SCF-003](../capabilities/scaffolding.md#req-scf-003-mark-unfinished-content) | Mark unfinished content | CAP-scaffolding |
| [REQ-SCF-004](../capabilities/scaffolding.md#req-scf-004-supersede-documents) | Supersede documents | CAP-scaffolding |
| [REQ-SCF-005](../capabilities/scaffolding.md#req-scf-005-initialise-a-repository) | Initialise a repository | CAP-scaffolding |
| [REQ-TRC-001](../capabilities/code-traceability.md#req-trc-001-recognise-tags) | Recognise tags | CAP-code-traceability |
| [REQ-TRC-002](../capabilities/code-traceability.md#req-trc-002-reject-wrong-references) | Reject wrong references | CAP-code-traceability |
| [REQ-TRC-003](../capabilities/code-traceability.md#req-trc-003-report-coverage) | Report coverage | CAP-code-traceability |
| [REQ-VIE-001](../capabilities/views.md#req-vie-001-render-tables) | Render tables | CAP-views |
| [REQ-VIE-002](../capabilities/views.md#req-vie-002-render-trees) | Render trees | CAP-views |
| [REQ-VIE-003](../capabilities/views.md#req-vie-003-report-stale-views) | Report stale views | CAP-views |
| [REQ-VIE-004](../capabilities/views.md#req-vie-004-write-only-changed-views) | Write only changed views | CAP-views |
