# Bondstone

Bondstone keeps AI-built software tied to what you approved. You approve the behavior, tests prove it, and Bondstone computes the rest: which requirements are proven, what is missing, and the one next step. It is a command-line tool that reads Markdown documents, test files and test reports, with no network access and no AI, plus an extension and preset for GitHub Spec Kit.

**Status:** proof of concept. Version 0.0, the Spec Kit extension and preset with a stopgap behind them, runs the simple-app workflow: living docs, version PRDs with deltas, one story per Spec Kit spec, and evidence from example IDs in test names. Version 0.1 is the checker and 0.2 the agent loop. See [integrations/speckit](integrations/speckit/README.md) to try it.

## Read more

- [Brief](docs/brief.md): the problem, users and goals
- [Roadmap](docs/roadmap.md): versions 0.0 to 0.2 and later
- [Architecture](docs/architecture/overview.md): concepts, components, trust model and decisions
- [Capabilities](docs/capabilities/): what each capability does, with examples that tests carry by ID
- [Decisions](docs/decisions/)
- [Agent guide](AGENTS.md): how agents work in this repository

Bondstone is built with Bondstone: this repository follows its own simple-app workflow from version 0.0.

## License

MIT
