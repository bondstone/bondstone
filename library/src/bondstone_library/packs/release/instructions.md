- A version is planned in `docs/releases/v<version>.md` before it ships. Create it with
  `bondstone new release:Release --title "..." --set version=1.2.0`.
- When the version is published, add `date:` and run `bondstone status v<version> released`.
  A released document can no longer be edited.
- `CHANGELOG.md` is generated from the release documents. Never edit it.
