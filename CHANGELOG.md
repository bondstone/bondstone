# Changelog

All notable changes to Bondstone are recorded here, one section per release. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Spec Kit extension `bondstone` with `status`, `next`, `write` and `check`, a template for every living and change doc, a wrapper script and a pre-commit hook.
- Spec Kit preset `bondstone`: one story per spec, expected and actual living-doc changes, example-named test tasks.
- The stopgap, which applies the simple-app workflow: living docs, version PRDs with deltas, stories, scoped example IDs, evidence from JUnit reports, seven computed phases and one next step.

### Changed

- simple-app runs as living docs and change docs linked by deltas (ADR-0008): capability specs move to `docs/capabilities/`, versions to `docs/roadmap.md`, the architecture page to `docs/architecture/overview.md`, and the terms to `docs/glossary.md`.
