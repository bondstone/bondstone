## Bondstone frontmatter

The specification starts with a YAML frontmatter block that `bondstone` reads. When you write
the specification:

1. Keep the block as the first lines of `spec.md`. Do not move it below the title.
2. Set `id` to the name of the feature's folder, such as `003-snooze-reminders`, and `title`
   to the feature's name. Leave `type: speckit:Feature` as it is.
3. Fill the links with ids, never with paths: `modifies` lists the capabilities whose
   behaviour this feature changes, `delivers` the requirements it implements, `decided_by`
   the decisions it rests on. Run `bondstone context --for <paths>` to find them. Leave a
   list empty when nothing applies yet.
4. Do not add a `status`: bondstone derives it from `spec.md`, `plan.md` and the ticked tasks
   in `tasks.md`.
5. Before you report completion, run `bondstone check` and fix what it reports for this
   feature.
