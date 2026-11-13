"""Every command has a reference document, and the document names what the parser accepts.

The design leaves this to a test: "every CLI subcommand has a command document" is easier to
check over the argument parser than with a documentation rule."""

import argparse

import pytest
from conftest import REPO

from bondstone.cli import build_parser
from bondstone.config import load_config
from bondstone.graph import build_graph


def subcommands(parser: argparse.ArgumentParser, prefix: tuple[str, ...] = ()):
    """(name, parser) of every command that can run; `profile check` is one command."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                if any(isinstance(a, argparse._SubParsersAction) for a in sub._actions):
                    yield from subcommands(sub, (*prefix, name))
                else:
                    yield " ".join((*prefix, name)), sub


COMMANDS = dict(subcommands(build_parser()))


@pytest.fixture(scope="module")
def documents():
    cfg = load_config(REPO)
    assert cfg.errors == []
    graph = build_graph(cfg)
    return {node.title: node for node in graph.nodes if node.type == "cli:Command"}, graph


def test_every_command_has_a_document_and_every_document_a_command(documents):
    nodes, _ = documents
    assert sorted(nodes) == sorted(COMMANDS)
    for name, node in nodes.items():
        slug = name.replace(" ", "-")
        assert (node.id, node.path) == (f"CLI-{slug}", f"docs/cli/{slug}.md")


@pytest.mark.parametrize("name", sorted(COMMANDS))
def test_the_document_names_every_option_of_the_parser(documents, name):
    node = documents[0][name]
    synopsis = node.fields["synopsis"]
    assert synopsis.startswith(f"bondstone {name}")
    options = node.body.split("## Options", 1)[1].split("\n## ", 1)[0]
    for action in COMMANDS[name]._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        shown = action.option_strings[0] if action.option_strings else (action.metavar or action.dest.upper())
        assert f"`{shown}" in options, f"{name}: {shown} is missing under Options"
        if action.dest != "root":
            assert shown in synopsis, f"{name}: {shown} is missing in the synopsis"
    takes_json = any(a.dest == "format" and "json" in (a.choices or []) for a in COMMANDS[name]._actions)
    assert node.fields.get("json_output", False) is takes_json
    assert ("JSON output" in node.heading_titles()) is takes_json


def test_every_command_is_tagged_at_its_parser_and_implements_a_capability(documents):
    nodes, graph = documents
    tagged = {tag.id for tag in graph.code_tags if tag.path == "src/bondstone/cli.py"}
    for node in nodes.values():
        assert node.covered and node.id in tagged, node.id
        assert node.links.get("cli-capability:implements"), node.id
