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


def test_every_engine_rule_is_in_the_catalog():
    import re

    source = "\n".join(p.read_text() for p in (REPO / "src" / "bondstone").glob("*.py"))
    emitted = set(re.findall(r'"(bondstone/[a-z]+(?:-[a-z]+)*)"', source))
    catalog = (REPO / "src" / "bondstone" / "engine_rules.md").read_text()
    documented = set(re.findall(r"^### ENG-\d{3}: (bondstone/[a-z-]+)$", catalog, re.M))
    assert emitted - documented == set(), "engine rules missing from engine_rules.md"
    assert documented - emitted == set(), "catalog entries for rules the engine never emits"


def test_explain_engine_rule(capsys):
    from bondstone.cli import main

    assert main(["--root", str(REPO), "explain", "bondstone/link-min"]) == 0
    assert "**Fix:**" in capsys.readouterr().out
