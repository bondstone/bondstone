## Decisions (ADR)

- Record a decision when you choose between real alternatives: a dependency, a
  storage format, a protocol, a structural pattern. Do not record routine edits.
- Create decisions with `bondstone new adr/decision --title "..."`. Never write the
  file by hand and never pick the number yourself.
- An accepted decision is frozen. To change it, run
  `bondstone supersede ADR-NNNN --title "..."` and write the new decision.
- Never edit `docs/adr/README.md`; run `bondstone render`.
