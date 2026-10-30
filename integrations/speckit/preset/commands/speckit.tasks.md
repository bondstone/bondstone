## Bondstone: tests and living docs are always tasks

- Whatever the tests setting says, include tasks that write failing tests named after every example ID the spec's `proves` covers (a requirement ID covers all its examples), before the implementation tasks. Name each test with the example ID, dots and hyphens as underscores: `test_SYNC_2_1_<what>`.
- Keep the template's `Bondstone tasks` section, and put the living-doc update last.
