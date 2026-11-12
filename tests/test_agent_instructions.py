"""`bondstone agent`: instructions for coding agents, generated from the active profile."""

import yaml
from conftest import EXAMPLE, REPO, standard
from test_cli import run

from bondstone.agent import GENERATED_MARK, MARKDOWN_PATH, SKILL_PATH, instructions, skill
from bondstone.config import load_config

RULE = {"id": "code-updates-spec", "description": "Code changes update a living spec.",
        "on_change": {"paths": ["src/**"]}, "require": [{"changed": {"role": "living-spec"}, "traced": True}],
        "exempt": {"trailer": "Spec-Impact"}}


def text_for(project, **profile) -> str:
    standard(project, **profile)
    cfg = load_config(project.root)
    assert cfg.errors == []
    return instructions(cfg)


def test_instructions_start_with_the_generated_mark_and_the_workflow(project):
    text = text_for(project)
    assert text.startswith(GENERATED_MARK + "\n# Documentation rules (bondstone)\n")
    for command in ("bondstone context --for", "bondstone new <Type>", "bondstone status <ID> <STATUS>",
                    "bondstone supersede <ID>", "bondstone gen", "bondstone check --base", "bondstone explain <rule>"):
        assert command in text
    assert "Never weaken `.bondstone/profile.yaml` (overrides, waivers) to make a check pass. Ask the user instead." in text
    assert "Active packs and bridges: adr@1.0.0 (pack), capability@1.0.0 (pack), adr-capability@1.0.0 (bridge)\n" in text


def test_every_type_is_described_with_what_an_author_needs(project):
    text = text_for(project)
    decision = text.split("### `adr:Decision`")[1].split("###")[0]
    assert "- location: `docs/adr/{id}-{slug}.md`\n- id: `ADR-{n:03d}`\n" in decision
    assert '- create: `bondstone new adr:Decision --title "..."`\n' in decision
    assert "- fields: title (required), date (required), deciders\n" in decision
    assert "- required sections: Context, Decision, Consequences\n" in decision
    assert "- status: proposed | accepted | rejected | deprecated | superseded (new ones start as `proposed`)\n" in decision
    assert "- allowed status changes: proposed → accepted, rejected; accepted → deprecated, superseded\n" in decision
    assert "- needs an `owner`\n" in decision
    assert ("- immutable once accepted, rejected, deprecated, superseded: only status may change; "
            "supersede it instead of editing it\n") in decision
    assert "- links: `supersedes` → adr:Decision (at most 1)\n" in decision
    capability = text.split("### `capability:Capability`")[1].split("###")[0]
    assert '- create: `bondstone new capability:Capability --title "..." --set code=...`\n' in capability
    assert "`constrained_by` → adr:Decision" in capability  # a link that a bridge adds


def test_item_types_say_where_they_are_written_and_how_they_are_traced(project):
    requirement = text_for(project).split("### `capability:Requirement`")[1].split("## Roles")[0]
    assert ("- add one by hand inside a `capability:Capability` document, as a heading `### {id}: {title}` under "
            "`## Requirements`\n") in requirement
    assert ("- id: `REQ-{code}-{n:03d}` (`{code}` is that document's `code` field; "
            "`{n}` is the next free number in that document)\n") in requirement
    assert "- status: planned | active | removed (`active` without a `Status:` line under the heading)\n" in requirement
    assert ("- tag the code that implements it with a comment `bondstone: <ID>`; one without a tag in status active "
            "is reported (warn); remove the tag in status removed\n") in requirement


def test_the_workflow_covers_what_a_first_time_agent_had_to_guess(project):
    text = text_for(project)
    assert "Some types are items: headings inside a document, which you add by hand." in text
    assert "After you edit documents by hand, run `bondstone gen`." in text
    assert "It compares your working tree, committed or not, with that branch." in text
    silent = text_for(project, overrides={"bondstone/code-coverage": "ignore"})
    assert "is reported (" not in silent.split("### `capability:Requirement`")[1].split("## Roles")[0]


def test_rules_carry_the_effective_severity_and_ignored_rules_are_left_out(project):
    text = text_for(project, overrides={"adr/alternatives-considered": "error",
                                        "capability/requirement-has-scenario": "ignore"})
    assert ("- **`adr/alternatives-considered`** (error): Accepted decisions record the alternatives that were "
            'considered. _Add a "## Alternatives considered" section._\n') in text
    assert "capability/requirement-has-scenario" not in text
    assert "- **`adr-capability/accepted-decision-is-applied`** (warn): " in text
    assert "Changed in this repository: `bondstone/view-stale` is ignore." in text


def test_roles_views_and_component_guidance_are_included(project):
    project.write(".bondstone/packs/adr/instructions.md", "- Write an ADR for every structural choice.\n")
    standard(project)
    project.pack("adr", project.read(".bondstone/packs/adr/pack.yaml") + "instructions: instructions.md\n")
    text = instructions(load_config(project.root))
    assert "## Roles\n\nRules name roles so that they work across packs.\n\n- `decision`: adr:Decision\n" in text
    assert "## Generated files\n\n`bondstone gen` writes these. Do not edit them.\n\n- `docs/generated/decisions.md` (adr/decision-log)\n" in text
    assert text.endswith("## Guidance from `adr`\n\n- Write an ADR for every structural choice.\n")


def test_exemption_trailers_are_only_mentioned_when_a_rule_has_one(project):
    assert "exemption trailer" not in text_for(project)
    assert ("Do not add an exemption trailer (`Spec-Impact`) to a commit unless the user asked for one."
            in text_for(project, rules=[RULE]))
    assert "exemption trailer" not in text_for(project, rules=[RULE], overrides={"profile/code-updates-spec": "ignore"})


def test_the_skill_has_frontmatter_and_the_same_instructions(project):
    standard(project)
    cfg = load_config(project.root)
    text = skill(cfg)
    head, body = text.split("---\n", 2)[1:]
    meta = yaml.safe_load(head)
    assert meta["name"] == "bondstone"
    assert "docs/adr/, docs/capabilities/" in meta["description"] and "`bondstone:` comments" in meta["description"]
    assert body == "\n" + instructions(cfg)


def test_agent_command_writes_the_file_once(project, capsys):
    standard(project)
    assert run(capsys, "--root", project.root, "agent") == (0, f"wrote {MARKDOWN_PATH}\n", "")
    assert project.read(MARKDOWN_PATH) == instructions(load_config(project.root))
    assert run(capsys, "--root", project.root, "agent") == (0, f"{MARKDOWN_PATH} is up to date\n", "")
    assert run(capsys, "--root", project.root, "agent", "--format", "skill") == (0, f"wrote {SKILL_PATH}\n", "")
    assert project.read(SKILL_PATH).startswith("---\nname: bondstone\n")
    assert run(capsys, "--root", project.root, "agent", "--output", "docs/AGENTS.md")[1] == "wrote docs/AGENTS.md\n"
    code, out, _ = run(capsys, "--root", project.root, "agent", "--output", "-")
    assert code == 0 and out == instructions(load_config(project.root))


def test_the_instructions_of_the_example_and_of_bondstone_itself_are_up_to_date():
    for root in (EXAMPLE, REPO):
        cfg = load_config(root)
        assert (root / MARKDOWN_PATH).read_text(encoding="utf-8") == instructions(cfg), (
            f"run `bondstone --root {root} agent`")
