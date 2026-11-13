- Plan a change as a Spec Kit feature: `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`,
  then `/speckit.implement`. Each feature is a folder `specs/NNN-name/`. Do not create one
  with `bondstone new`; Spec Kit's commands number the folder and write the files.
- `spec.md` starts with a frontmatter block: `id` is the folder's name, `type` is
  `speckit:Feature`, `title` is the feature's name. Keep the block at the top of the file.
- A feature has no `status` field. It is `specified` when `spec.md` exists, `planned` when
  `plan.md` exists, and `implemented` when every task in `tasks.md` is ticked. Tick a task
  only when it is done: rules for implemented features apply from the last tick.
