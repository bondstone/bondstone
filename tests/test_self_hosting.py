"""Facts about bondstone's own repository that are checked by tests rather than by rules."""

import argparse

from bondstone.cli import build_parser
from bondstone.graph import build_graph
from bondstone.loader import load_config

from .conftest import REPO


def _commands(parser: argparse.ArgumentParser, prefix: str = "") -> list[str]:
    names = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                nested = _commands(sub, f"{prefix}{name} ")
                names.extend(nested or [f"{prefix}{name}"])
    return names


def test_every_command_has_a_cli_document():
    graph = build_graph(load_config(REPO))
    documented = {n.title for n in graph.nodes if n.type == "cli:Command"}
    commands = set(_commands(build_parser()))
    assert commands - documented == set(), "commands without docs/cli/ document"
    assert documented - commands == set(), "docs/cli/ documents for commands that do not exist"
