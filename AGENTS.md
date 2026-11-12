# Instructions for coding agents

The rules for this repository's documentation are in [AGENTS.bondstone.md](AGENTS.bondstone.md). Follow them.

Bondstone is not installed globally here: run it as `uv run bondstone ...`, and the tests as `uv run pytest`.

Changes to the source are planned as Spec Kit features under `specs/` (Spec Kit 1.4.0, set up in `.specify/` with the skills in `.claude/skills/speckit-*`). A pull request that changes `src/` or `library/src/` without a changed feature fails `bondstone check --base`.
