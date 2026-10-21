# Bondstone

Bondstone keeps AI-built software tied to what you approved. You approve the behavior, tests prove it, and Bondstone computes the rest: which requirements are proven, what is missing, and the one next step. It is a command-line tool that reads Markdown documents, test files and test reports, with no network access and no AI, plus an extension and preset for GitHub Spec Kit.

**Status:** in design. Nothing is released yet. Release 0.0 is the Spec Kit extension and preset with a stopgap behind them, release 0.1 the checker, and release 0.2 the agent loop.

## Read more

- [Brief](docs/brief.md): the problem, goals and releases
- [Architecture](docs/architecture.md): components, flows, decisions and risks
- [Living specs](docs/spec/): what each capability does, with examples that run as tests
- [Decisions](docs/decisions/)
- [Agent guide](AGENTS.md): how agents work in this repository

Bondstone is built with Bondstone. This repository follows its own simple-app profile, described in the [PROFILE spec](docs/spec/profile.md).

## License

MIT
