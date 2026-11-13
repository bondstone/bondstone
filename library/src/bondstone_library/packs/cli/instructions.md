- Every command of the command-line tool has a document in `docs/cli/`. When you add, change
  or remove an option, update that command's document in the same change.
- Tag the code that defines or handles a command with a comment `bondstone: CLI-<name>`.
- A new command starts as `experimental`. Move it to `stable` with
  `bondstone status CLI-<name> stable` once its interface is meant to stay.
