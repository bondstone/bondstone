# Agent guide

- Documentation rules for this repository are generated in [AGENTS.bondstone.md](AGENTS.bondstone.md).
  Follow them for every change; refresh with `bondstone agent --output AGENTS.bondstone.md`.
- Before finishing: `pytest`, `bondstone pack test src/bondstone/library/*/* .bondstone/packs/*`,
  `bondstone gen` and `bondstone check --base origin/POC`.
