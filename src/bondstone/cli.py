"""Keep a repository's living documentation true, by checking it against rules stored in it.

Exit codes: 0 no violations, 1 violations found, 2 configuration error, 3 environment error."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__, agent
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
