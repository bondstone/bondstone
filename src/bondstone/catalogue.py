"""The catalogue of engine rules: every `bondstone/...` diagnostic the engine can emit.

Engine checks are rules like any other. Each has a default severity that a profile may
override, down to `ignore`. The one exception is `bondstone/profile`: the checker cannot run
on an invalid configuration, so it always stops the run with exit code 2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import ERROR, INFO, WARN, Diagnostic


@dataclass(frozen=True)
class EngineRule:
    id: str
    severity: str  # default severity
    fires: str  # when the rule reports
    why: str
    fix: str
    overridable: bool = True
    note: str = ""  # how the severity varies, when it does
    known: bool = True  # whether `.bondstone/known.json` may record its violations


def _rule(name: str, severity: str, fires: str, why: str, fix: str, **extra) -> EngineRule:
    return EngineRule(f"bondstone/{name}", severity, fires, why, fix, **extra)


# bondstone: REQ-RUL-005
ENGINE_RULES: tuple[EngineRule, ...] = (
    _rule("profile", ERROR,
          "The profile, a pack or a bridge is invalid: a manifest that breaks its schema, a pack "
          "that is not found or whose version does not match, a bridge whose required packs are "
          "missing, unknown types, links, roles or rule ids, or an override that loosens a locked rule.",
          "Checks are only meaningful when the rules themselves are consistent.",
          "Read the message; `bondstone profile check` lists only these problems.",
          overridable=False, note="Stops the run with exit code 2 and cannot be overridden or waived.", known=False),
    _rule("unbridged-packs", WARN,
          "The profile's packs form groups that no bridge connects.",
          "Unconnected packs produce islands of documents that nothing links together.",
          "Add a bridge that requires packs from both groups, or remove a pack you do not use."),
    _rule("parse-error", ERROR,
          "A document cannot be read: it is not UTF-8, or its frontmatter is not closed, is not "
          "valid YAML or is not a mapping.",
          "Nothing else can be checked for an unreadable document.",
          "Fix the YAML between the `---` lines."),
    _rule("frontmatter-missing", ERROR,
          "A file at a type's path has no frontmatter.",
          "Files in typed folders are expected to be documents.",
          "Add a frontmatter block with `id` and `type`."),
    _rule("untyped-document", ERROR,
          "A file under the profile's `docs` globs is at no type's path.",
          "Managed folders hold only documents that bondstone can check.",
          "Move the file to a type's path, or narrow `docs` in the profile."),
    _rule("type-missing", ERROR,
          "A document's frontmatter has no `type`.",
          "Every document states its type, so a reader and a tool can tell what it is without "
          "knowing the folder layout.",
          "Add `type: <pack>:<Type>` to the frontmatter; the hint names the type its path implies."),
    _rule("unknown-type", ERROR,
          "A document declares a `type` that no active pack defines.",
          "The type decides every other check.",
          "Use a qualified type of an active pack, such as `adr:Decision`, or add the pack to the profile."),
    _rule("type-mismatch", ERROR,
          "A document declares a `type` whose path it does not live at.",
          "A type's documents are found by their path; elsewhere they are easy to miss.",
          "Move the file to the type's path, or correct `type`."),
    _rule("type-ambiguous", ERROR,
          "A file is at the path of several types and declares none of them.",
          "Bondstone cannot tell which rules apply.",
          "Add `type` to the frontmatter."),
    _rule("link-ambiguous", ERROR,
          "A frontmatter key matches link names from several packs or bridges.",
          "The link could point to different kinds of documents.",
          "Use the qualified name, such as `adr-capability:constrained_by`."),
    _rule("item-heading", ERROR,
          "A heading at the item level inside the item section does not look like an item, such "
          "as a level-3 heading under `## Requirements` that is not `REQ-...: title`.",
          "Malformed items would silently not be checked or traced.",
          "Rename the heading to match the item heading, or change its level."),
    _rule("id-missing", ERROR,
          "A document has no `id`.",
          "Links, tags and views all refer to ids.",
          "Add `id` following the type's id template."),
    _rule("id-format", ERROR,
          "An id does not match its type's id template.",
          "Consistent ids keep links and code tags readable and unambiguous.",
          "Rename the id and update the links to it."),
    _rule("id-path", ERROR,
          "A document's id is not the one its path carries: the type's path template has `{id}`, "
          "and the file is somewhere else.",
          "When the path names the id, a reader finds a document from a link without searching.",
          "Rename the file or folder to the id, or correct the id."),
    _rule("id-duplicate", ERROR,
          "Two documents or items use the same id.",
          "Links and tags would be ambiguous.",
          "Give one of them a new id."),
    _rule("field-missing", ERROR,
          "A required field is missing from the frontmatter.",
          "Required fields are part of the type's contract.",
          "Add the field."),
    _rule("field-unknown", ERROR,
          "A frontmatter key is neither a field nor a link of the document's type.",
          "Unknown keys are usually typos of links, which would otherwise be silently ignored.",
          "Use one of the fields or links listed in the hint."),
    _rule("field-invalid", ERROR,
          "A field value does not match the type's schema, such as an unknown status or a malformed date.",
          "Values outside the schema break views, rules and lifecycles.",
          "Use a value the schema allows."),
    _rule("todo-left", ERROR,
          "A document still contains a `<!-- todo: ... -->` placeholder outside code.",
          "Scaffolded placeholders must not survive into decided or published documents.",
          "Replace every placeholder with real content.",
          note="A warning while the document is in its lifecycle's initial status, an error afterwards."),
    _rule("section-missing", ERROR,
          "A document lacks a section its type requires.",
          "Required sections carry the information the method depends on.",
          "Add the heading (any level)."),
    _rule("link-broken", ERROR,
          "A link points to an id that does not exist.",
          "Broken links are exactly the drift bondstone exists to prevent.",
          "Fix the id or create the missing document."),
    _rule("link-type", ERROR,
          "A link points to a node of a type the link does not allow.",
          "Typed links keep relations meaningful.",
          "Point the link at a node of an allowed type."),
    _rule("link-self", ERROR,
          "A document links to itself.",
          "Self-links carry no information and usually come from a copy-paste mistake.",
          "Remove or correct the link."),
    _rule("link-min", ERROR,
          "A document has fewer links of a kind than the link requires.",
          "Some relations are mandatory, such as an opportunity serving an outcome.",
          "Add the links named in the message."),
    _rule("link-max", ERROR,
          "A document has more links of a kind than the link allows.",
          "Some relations are singular, such as a decision superseding at most one decision.",
          "Remove the extra links."),
    _rule("supersede-status", ERROR,
          "A document is superseded by another but its status is not `superseded`.",
          "Readers must see that a document no longer applies.",
          "Set `status: superseded`."),
    _rule("supersede-multiple", ERROR,
          "A document is superseded by more than one document.",
          "Supersession must form a single chain.",
          "Supersede the newest document instead."),
    _rule("supersede-orphan", WARN,
          "A document has the status `superseded` but nothing supersedes it.",
          "Readers cannot find what replaced it.",
          "Add the supersede link to its successor, or change its status."),
    _rule("supersede-cycle", ERROR,
          "Supersede links form a cycle.",
          "A cycle has no current document.",
          "Break the cycle."),
    _rule("code-ref-unknown", ERROR,
          "A code tag `bondstone: <id>` refers to an id that does not exist.",
          "A tag for something the documentation does not contain is stale traceability.",
          "Fix or remove the tag."),
    _rule("code-ref-not-traceable", ERROR,
          "A code tag refers to a node whose type is not code-traceable.",
          "Only some types, such as requirements, describe behaviour that code implements.",
          "Tag a code-traceable node instead, such as the requirement rather than its document."),
    _rule("code-coverage", WARN,
          "A code-traceable node is not tagged anywhere in code. With `when`, only nodes in the "
          "listed statuses are checked.",
          "An untagged requirement may be unimplemented, or its code cannot be found.",
          "Add a `bondstone: <id>` comment above the implementing code.",
          note="The severity comes from the trait's `coverage` setting."),
    _rule("tag-retired", WARN,
          "A code tag refers to a node whose status is listed in its type's `code-traceable.retired`.",
          "The code claims to implement something the documentation no longer contains.",
          "Remove the tag, or the code if it is no longer needed."),
    _rule("view-stale", ERROR,
          "A generated view is missing or differs from what `bondstone gen` would write.",
          "Committed views must match the documents they are generated from.",
          "Run `bondstone gen` and commit the result.", known=False),
    _rule("status-initial", ERROR,
          "With `--base`, a new document or item starts in a status other than its lifecycle's `initial`.",
          "Skipping the first status skips the review that status stands for.",
          "Create it in the initial status and change the status in a later change. For documents "
          "that existed before bondstone, record them with `bondstone baseline`.",
          note="Only checked for lifecycles that declare `initial`.", known=False),
    _rule("status-transition", ERROR,
          "With `--base`, a document's or an item's status changed in a way its lifecycle's "
          "`transitions` do not allow.",
          "A lifecycle is only worth something when its steps cannot be skipped or undone.",
          "Use one of the allowed statuses named in the message.",
          note="Only checked for lifecycles that declare `transitions`.", known=False),
    _rule("immutable", ERROR,
          "With `--base`, a document that was in an immutable status was edited beyond the fields "
          "its type allows.",
          "A decided document is a record: readers must be able to trust it says what was decided.",
          "Undo the edit and create a new document that supersedes it.", known=False),
    _rule("baseline-missing", ERROR,
          "With `--base`, the profile's `baseline` commit is not available in the clone.",
          "Without it, documents adopted at the baseline look new and lifecycle checks misfire.",
          "Fetch the full history (`git fetch --unshallow`), or record a new commit with `bondstone baseline`.", known=False),
    _rule("exemption-used", INFO,
          "A commit trailer exempted a diff-rule violation; the message names the commit, the rule "
          "and the reason.",
          "An exemption is allowed, but it is never silent.",
          "Nothing to fix. `check --no-exemptions` ignores trailers when a run must be strict.", known=False),
    _rule("exemption-invalid", ERROR,
          "A commit in the checked range carries an exemption trailer whose value is not "
          "`none (<reason>)` or `none [ID, ...] (<reason>)`.",
          "A typo must neither exempt a change silently nor fail to exempt it silently.",
          "Amend the commit message, or add a commit with a valid trailer.", known=False),
    _rule("waiver-invalid", ERROR,
          "A waiver has no `rule`, `reason` or `expires`, names a rule that does not exist, or "
          "names a locked rule.",
          "Every exception is explained and temporary, and locked rules allow none.",
          "Complete or remove the waiver.", known=False),
    _rule("waiver-expired", ERROR,
          "A waiver's `expires` date has passed.",
          "Exceptions are temporary by design.",
          "Fix the waived problem and remove the waiver, or renew it with a reason.", known=False),
    _rule("waiver-unused", WARN,
          "A waiver matches no diagnostic.",
          "Unused waivers hide future problems.",
          "Remove the waiver.", known=False),
    _rule("known-stale", WARN,
          "An entry of `.bondstone/known.json` matches no violation: the problem was fixed, the node "
          "or the rule is gone, or the rule does not accept known violations.",
          "The file records what is still to fix, so it must not keep what is done.",
          "Run `bondstone baseline --known --prune`, which removes such entries and never adds any.",
          known=False),
    _rule("known-grew", ERROR,
          "With `--base`, `.bondstone/known.json` has entries that it did not have at the base commit.",
          "Known violations may only shrink; recording a new violation would hide it from the gate.",
          "Fix the new violations and take their entries out again. A deliberate reset overrides "
          "this rule in the profile in the same change, where a reviewer sees it.",
          note="Not reported for the change that adds the profile itself.", known=False),
)

BY_ID: dict[str, EngineRule] = {rule.id: rule for rule in ENGINE_RULES}


def engine_rule(rule_id: str) -> EngineRule | None:
    return BY_ID.get(rule_id)


def default_severity(rule_id: str) -> str:
    return BY_ID[rule_id].severity


# bondstone: REQ-RUL-005
def diagnostic(rule_id: str, message: str, path: str | None = None, line: int | None = None,
               node: str | None = None, hint: str | None = None, severity: str | None = None,
               fix: dict[str, Any] | None = None, key: str | None = None) -> Diagnostic:
    """A diagnostic of an engine rule, at the rule's default severity unless one is given.

    `key` names the specific problem, such as the missing section, when a node can break the
    rule in more than one way."""
    return Diagnostic(rule_id, severity or BY_ID[rule_id].severity, message, path, line, node, hint, fix, key=key)
