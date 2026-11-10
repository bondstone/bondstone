# bondstone

**Living documentation, enforced.** Bondstone checks a repository's documents against rules
that live in the same repository. Coding agents run it to validate their own work; git hooks
and CI run it as a gate.

> Status: v1 under construction. The design is [docs/design.md](docs/design.md).

## Development

```bash
uv sync
uv run pytest
```

## License

MIT
