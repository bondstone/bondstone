"""Keep a repository's living documentation true, by checking it against rules stored in it.

Exit codes: 0 no violations, 1 violations found, 2 configuration error, 3 environment error."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from . import __version__, agent, context, edit
from .baseline import record_baseline
from .config import Config, load_config
from .format import FORMATS, JSON_VERSION, render
from .git import GitRepository
from .graph import build_graph
from .model import ERROR, IGNORE, WARN, EnvironmentProblem, Refused
from .resolve import find_root
from .rules import fails, run_check
from .views import generate

EXIT_OK, EXIT_VIOLATIONS, EXIT_CONFIG, EXIT_ENVIRONMENT = 0, 1, 2, 3


# bondstone: REQ-PRF-003
def _root(args: argparse.Namespace) -> Path:
    if args.root is None:
        return find_root(Path.cwd())
    root = Path(args.root)
    if not root.is_dir():
        raise EnvironmentProblem(f"--root: '{args.root}' is not a directory")
    return root.resolve()


# bondstone: REQ-PRF-010, REQ-CLI-007
def _config(args: argparse.Namespace, fmt: str = "text") -> Config | None:
    """The configuration, or None after reporting configuration errors (exit code 2)."""
    cfg = load_config(_root(args))
    if cfg.errors:
        sys.stdout.write(render(fmt, cfg.errors))
        print("bondstone: the configuration is invalid; nothing was checked", file=sys.stderr)
        return None
    return cfg


# bondstone: REQ-CLI-001
def cmd_check(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    repo = GitRepository(cfg.root) if args.base else None
    graph = build_graph(cfg)
    diagnostics = run_check(cfg, graph, repo=repo, base=args.base, exemptions=not args.no_exemptions)
    sys.stdout.write(render(args.format, diagnostics, nodes=len(graph.nodes)))
    return EXIT_VIOLATIONS if fails(diagnostics, args.fail_on) else EXIT_OK


# bondstone: REQ-CLI-002
def cmd_gen(args: argparse.Namespace) -> int:
    cfg = _config(args)
    if cfg is None:
        return EXIT_CONFIG
    written = generate(cfg, build_graph(cfg))
    for path in written:
        print(f"wrote {path}")
    if not written:
        print("views are up to date")
    return EXIT_OK


# bondstone: REQ-CLI-004
def cmd_baseline(args: argparse.Namespace) -> int:
    cfg = _config(args)
    if cfg is None:
        return EXIT_CONFIG
    commit = record_baseline(cfg.root, GitRepository(cfg.root), args.ref)
    print(f"baseline: {commit}")
    return EXIT_OK


# bondstone: REQ-CLI-003
def cmd_profile_check(args: argparse.Namespace) -> int:
    cfg = load_config(_root(args))
    if cfg.errors:
        sys.stdout.write(render(args.format, cfg.errors))
        return EXIT_CONFIG
    warnings = [replace(d, severity=cfg.severity(d.rule, d.severity)) for d in cfg.problems]
    sys.stdout.write(render(args.format, [d for d in warnings if d.severity != IGNORE]))
    return EXIT_OK


def _sets(items: list[str] | None) -> dict[str, Any]:
    """`--set KEY=VALUE` options as a mapping; a value is read as YAML, so `a=[X, Y]` is a list."""
    sets: dict[str, Any] = {}
    for item in items or []:
        key, separator, value = item.partition("=")
        if not separator or not key.strip():
            raise Refused(f"--set expects KEY=VALUE, got '{item}'")
        try:
            sets[key.strip()] = yaml.safe_load(value) if value.strip() else ""
        except yaml.YAMLError:
            sets[key.strip()] = value  # not YAML, such as text with a colon: keep it as written
    return sets


# bondstone: REQ-SCF-006
def _after_edit(args: argparse.Namespace, lines: list[str], payload: dict[str, Any]) -> int:
    """Regenerate the views an edit made stale, then report what the command did."""
    cfg = load_config(_root(args))
    views = generate(cfg, build_graph(cfg)) if not cfg.errors else []
    if args.format == "json":
        _print_json({"version": JSON_VERSION, **payload, "views": views})
    else:
        for line in [*lines, *(f"wrote {path}" for path in views)]:
            print(line)
    return EXIT_OK


# bondstone: REQ-SCF-001
def cmd_new(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    created = edit.new_document(cfg, build_graph(cfg), args.type, args.title, _sets(args.set))
    return _after_edit(args, [f"created {created.path} ({created.id})"], {"id": created.id, "path": created.path})


# bondstone: REQ-SCF-003
def cmd_status(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    change = edit.change_status(cfg, build_graph(cfg), args.id, args.status)
    line = (f"{change.id}: {change.old} -> {change.new} ({change.path})" if change.changed
            else f"{change.id} is already {change.new}")
    return _after_edit(args, [line], {"id": change.id, "path": change.path, "old": change.old, "new": change.new,
                                      "changed": change.changed})


# bondstone: REQ-SCF-004
def cmd_supersede(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    result = edit.supersede(cfg, build_graph(cfg), args.id, args.title, _sets(args.set))
    lines = [f"created {result.created.path} ({result.created.id})",
             *(f"updated {line}" for line in result.updated), *(f"skipped {line}" for line in result.skipped)]
    return _after_edit(args, lines, {"id": result.created.id, "path": result.created.path,
                                     "updated": result.updated, "skipped": result.skipped})


# bondstone: REQ-AGT-003
def cmd_context(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    graph = build_graph(cfg)
    if args.base:
        found = context.context_since(cfg, graph, GitRepository(cfg.root), args.base)
    else:
        found = context.context_for(cfg, graph, [context.normalize(cfg, path) for path in args.paths])
    if args.format == "json":
        _print_json({"version": JSON_VERSION, **found.to_dict()})
    else:
        sys.stdout.write(context.to_text(found))
    return EXIT_OK


def _print_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


# bondstone: REQ-AGT-001
def cmd_rules(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    rules = agent.list_rules(cfg)
    if args.format == "json":
        _print_json({"version": JSON_VERSION, "rules": [rule.to_dict() for rule in rules]})
    else:
        sys.stdout.write(agent.rules_text(rules))
    return EXIT_OK


# bondstone: REQ-AGT-002
def cmd_explain(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    if args.format == "json":
        _print_json({"version": JSON_VERSION, **agent.explain(cfg, args.rule)})
    else:
        sys.stdout.write(agent.explain_text(cfg, args.rule))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS,
                        help="repository root (default: the nearest folder with .bondstone/profile.yaml)")
    output = argparse.ArgumentParser(add_help=False)
    output.add_argument("--format", choices=FORMATS, default="text", help="output format (default: text)")

    parser = argparse.ArgumentParser(prog="bondstone", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"bondstone {__version__}")
    parser.add_argument("--root", default=None,
                        help="repository root (default: the nearest folder with .bondstone/profile.yaml)")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    check = commands.add_parser("check", parents=[common, output],
                                help="validate documents, links, rules, code tags and views")
    check.add_argument("--fail-on", choices=[ERROR, WARN], default=ERROR,
                       help="lowest severity that fails the run (default: error)")
    check.add_argument("--base", metavar="REF",
                       help="also check the changes since REF: lifecycles, immutability and diff rules")
    check.add_argument("--no-exemptions", action="store_true",
                       help="with --base, ignore the commit trailers that exempt a change from a diff rule")
    check.set_defaults(func=cmd_check)

    gen = commands.add_parser("gen", parents=[common], help="regenerate views")
    gen.set_defaults(func=cmd_gen)

    baseline = commands.add_parser("baseline", parents=[common],
                                   help="record the commit whose documents count as already adopted")
    baseline.add_argument("ref", nargs="?", default="HEAD", metavar="REF", help="the commit (default: HEAD)")
    baseline.set_defaults(func=cmd_baseline)

    setting = argparse.ArgumentParser(add_help=False)
    setting.add_argument("--title", required=True, help="title of the new document")
    setting.add_argument("--set", action="append", metavar="KEY=VALUE",
                         help="a frontmatter field or link of the new document; may be repeated")

    new = commands.add_parser("new", parents=[common, output, setting],
                              help="scaffold a document with the next id at its type's path")
    new.add_argument("type", metavar="TYPE", help="a document type such as adr:Decision")
    new.set_defaults(func=cmd_new)

    status = commands.add_parser("status", parents=[common, output],
                                 help="change the status of a document or an item, if its lifecycle allows it")
    status.add_argument("id", metavar="ID")
    status.add_argument("status", metavar="STATUS")
    status.set_defaults(func=cmd_status)

    supersede = commands.add_parser("supersede", parents=[common, output, setting],
                                    help="replace a document: successor, `superseded` status, links moved")
    supersede.add_argument("id", metavar="ID", help="the document to replace")
    supersede.set_defaults(func=cmd_supersede)

    ctx = commands.add_parser("context", parents=[common, output],
                              help="list what to read before editing: traced documents and the rules that will fire")
    what = ctx.add_mutually_exclusive_group(required=True)
    what.add_argument("--for", dest="paths", nargs="+", metavar="PATH", help="files or folders about to be edited")
    what.add_argument("--base", metavar="REF", help="the files changed since REF")
    ctx.set_defaults(func=cmd_context)

    rules = commands.add_parser("rules", parents=[common, output],
                                help="list the active rules with their effective severity")
    rules.set_defaults(func=cmd_rules)

    explain = commands.add_parser("explain", parents=[common, output],
                                  help="explain one rule: what it asks, why, and how to satisfy it")
    explain.add_argument("rule", metavar="RULE", help="a rule id such as adr/alternatives-considered")
    explain.set_defaults(func=cmd_explain)

    profile = commands.add_parser("profile", help="profile commands")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True, metavar="COMMAND")
    profile_check = profile_commands.add_parser("check", parents=[common, output],
                                                help="validate the profile, packs and bridges")
    profile_check.set_defaults(func=cmd_profile_check)
    return parser


# bondstone: REQ-CLI-007
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Refused as exc:
        print(f"bondstone: {exc}", file=sys.stderr)
        return EXIT_VIOLATIONS
    except EnvironmentProblem as exc:
        print(f"bondstone: {exc}", file=sys.stderr)
        return EXIT_ENVIRONMENT
    except OSError as exc:
        print(f"bondstone: {exc}", file=sys.stderr)
        return EXIT_ENVIRONMENT
