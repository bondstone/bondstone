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

from . import __version__, agent, context, edit, export, packs, packtest, report, waive
from .baseline import record_baseline, record_known
from .config import Config, load_config
from .format import FORMATS, JSON_VERSION, render
from .git import GitRepository
from .graph import build_graph
from .known import KNOWN_PATH
from .model import ERROR, IGNORE, PROFILE_PATH, WARN, EnvironmentProblem, Refused
from .resolve import find_root, resolve
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
    compared = _compared(repo, args.base) if repo is not None and args.format == "json" else None
    sys.stdout.write(render(args.format, diagnostics, nodes=len(graph.nodes), base=compared))
    return EXIT_VIOLATIONS if fails(diagnostics, args.fail_on) else EXIT_OK


# bondstone: REQ-CLI-006
def _compared(repo: GitRepository, ref: str) -> dict[str, Any]:
    """What `--base` compared: the ref, the merge base it stands for, and the files that differ."""
    commit = repo.merge_base(ref)
    changes = []
    for change in repo.changes(commit):
        entry = {"path": change.path, "kind": change.kind}
        if change.old_path:
            entry["old_path"] = change.old_path
        changes.append(entry)
    return {"ref": ref, "commit": commit, "changes": changes}


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
    if args.prune and not args.known:
        raise Refused("--prune only applies to `baseline --known`")
    if args.known:
        if args.ref is not None:
            raise Refused("`baseline --known` records the working tree; it takes no REF")
        return _known(cfg, args.prune)
    commit = record_baseline(cfg.root, GitRepository(cfg.root), args.ref or "HEAD")
    print(f"baseline: {commit}")
    return EXIT_OK


# bondstone: REQ-KNV-001, REQ-KNV-005
def _known(cfg: Config, prune: bool) -> int:
    result = record_known(cfg, prune)
    if prune:
        print(f"removed {result.removed} known violation(s) that no longer occur; {result.entries} remain")
    elif result.entries:
        print(f"recorded {result.entries} known violation(s) in {KNOWN_PATH} ({result.added} new)")
    else:
        print("no violations to record")
    if result.deleted:
        print(f"deleted {KNOWN_PATH}: it had no entries left")
    if result.refused and not prune:
        print(f"{result.refused} violation(s) were not recorded: their rules do not accept known violations")
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
    created = edit.new_document(cfg, build_graph(cfg), args.type, args.title, _sets(args.set),
                                dry_run=args.dry_run)
    if args.dry_run:
        if args.format == "json":
            _print_json({"version": JSON_VERSION, "id": created.id, "path": created.path, "dry_run": True})
        else:
            print(f"would create {created.path} ({created.id})")
        return EXIT_OK
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


# bondstone: REQ-AGT-005
def cmd_agent(args: argparse.Namespace) -> int:
    cfg = _config(args)
    if cfg is None:
        return EXIT_CONFIG
    if args.output == "-":
        sys.stdout.write(agent.skill(cfg) if args.format == "skill" else agent.instructions(cfg))
        return EXIT_OK
    path, changed = agent.write(cfg, args.format, args.output)
    print(f"wrote {path}" if changed else f"{path} is up to date")
    return EXIT_OK


# bondstone: REQ-AGT-007
def cmd_graph(args: argparse.Namespace) -> int:
    cfg = _config(args)
    if cfg is None:
        return EXIT_CONFIG
    graph = build_graph(cfg)
    if args.format == "mermaid":
        sys.stdout.write(export.graph_mermaid(cfg, graph, args.type))
    else:
        sys.stdout.write(export.to_json(export.graph_json(cfg, graph, args.type)))
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


# bondstone: REQ-PRF-016
def cmd_waive(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    waived = waive.add_waiver(cfg, build_graph(cfg), args.rule, args.node, args.reason, args.expires)
    if args.format == "json":
        _print_json({"version": JSON_VERSION, **waived.to_dict()})
    else:
        print(f"waived {waived.rule} for {waived.node or 'every node'} until {waived.expires} ({waived.path})")
    return EXIT_OK


# bondstone: REQ-CLI-008
def cmd_report(args: argparse.Namespace) -> int:
    cfg = _config(args, args.format)
    if cfg is None:
        return EXIT_CONFIG
    repo = GitRepository(cfg.root) if args.base else None
    found = report.build_report(cfg, build_graph(cfg), repo=repo, base=args.base)
    if args.format == "json":
        _print_json({"version": JSON_VERSION, **found.to_dict()})
    else:
        sys.stdout.write(report.to_text(found))
    return EXIT_OK


def _folder(args: argparse.Namespace) -> Path:
    """The folder a command works in when it needs no profile: `--root`, or the current folder."""
    if args.root is None:
        return Path.cwd()
    root = Path(args.root)
    if not root.is_dir():
        raise EnvironmentProblem(f"--root: '{args.root}' is not a directory")
    return root.resolve()


# bondstone: REQ-PKT-003
def cmd_packs(args: argparse.Namespace) -> int:
    """Without a profile, list what a new profile here could use."""
    try:
        root = _root(args)
    except EnvironmentProblem:
        root = _folder(args)
    profile, components = None, []
    if (root / PROFILE_PATH).is_file():
        resolution = resolve(root)
        if resolution.profile is None:
            sys.stdout.write(render(args.format, resolution.problems))
            return EXIT_CONFIG
        profile, components = resolution.profile, resolution.components
    found = packs.available(root, profile, components)
    if args.format == "json":
        _print_json({"version": JSON_VERSION, "components": [item.to_dict() for item in found]})
    else:
        sys.stdout.write(packs.to_text(found))
    return EXIT_OK


# bondstone: REQ-PKT-001
def cmd_pack_test(args: argparse.Namespace) -> int:
    results = [result for directory in args.dirs for result in packtest.run_fixtures(Path(directory))]
    if args.format == "json":
        _print_json({"version": JSON_VERSION, **packtest.to_dict(results)})
    else:
        sys.stdout.write(packtest.to_text(results))
    return EXIT_OK if all(result.passed for result in results) else EXIT_VIOLATIONS


# bondstone: REQ-PRF-012
def cmd_init(args: argparse.Namespace) -> int:
    root = _folder(args)
    path = packs.init_profile(root, args.preset)
    print(f"created {path}")
    if args.preset:
        print("next: list this repository's source files under `code.include`, then run `bondstone agent`")
    else:
        print("next: `bondstone packs` lists the packs, bridges and presets to add to it")
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

    # bondstone: CLI-check
    check = commands.add_parser("check", parents=[common, output],
                                help="validate documents, links, rules, code tags and views")
    check.add_argument("--fail-on", choices=[ERROR, WARN], default=ERROR,
                       help="lowest severity that fails the run (default: error)")
    check.add_argument("--base", metavar="REF",
                       help="also check the changes since REF: lifecycles, immutability and diff rules")
    check.add_argument("--no-exemptions", action="store_true",
                       help="with --base, ignore the commit trailers that exempt a change from a diff rule")
    check.set_defaults(func=cmd_check)

    # bondstone: CLI-gen
    gen = commands.add_parser("gen", parents=[common], help="regenerate views")
    gen.set_defaults(func=cmd_gen)

    # bondstone: CLI-baseline
    baseline = commands.add_parser(
        "baseline", parents=[common],
        help="record the commit whose documents count as already adopted, or with --known the current violations")
    baseline.add_argument("ref", nargs="?", default=None, metavar="REF", help="the commit (default: HEAD)")
    baseline.add_argument("--known", action="store_true",
                          help="record the current violations in .bondstone/known.json instead of a commit")
    baseline.add_argument("--prune", action="store_true",
                          help="with --known, only remove the entries that no longer occur")
    baseline.set_defaults(func=cmd_baseline)

    setting = argparse.ArgumentParser(add_help=False)
    setting.add_argument("--title", required=True, help="title of the new document")
    setting.add_argument("--set", action="append", metavar="KEY=VALUE",
                         help="a frontmatter field or link of the new document; may be repeated")

    # bondstone: CLI-new
    new = commands.add_parser("new", parents=[common, output, setting],
                              help="scaffold a document with the next id at its type's path")
    new.add_argument("type", metavar="TYPE", help="a document type such as adr:Decision")
    new.add_argument("--dry-run", action="store_true",
                     help="check the request and print the id and the path, without creating the document")
    new.set_defaults(func=cmd_new)

    # bondstone: CLI-status
    status = commands.add_parser("status", parents=[common, output],
                                 help="change the status of a document or an item, if its lifecycle allows it")
    status.add_argument("id", metavar="ID")
    status.add_argument("status", metavar="STATUS")
    status.set_defaults(func=cmd_status)

    # bondstone: CLI-supersede
    supersede = commands.add_parser("supersede", parents=[common, output, setting],
                                    help="replace a document: successor, `superseded` status, links moved")
    supersede.add_argument("id", metavar="ID", help="the document to replace")
    supersede.set_defaults(func=cmd_supersede)

    # bondstone: CLI-context
    ctx = commands.add_parser("context", parents=[common, output],
                              help="list what to read before editing: traced documents and the rules that will fire")
    what = ctx.add_mutually_exclusive_group(required=True)
    what.add_argument("--for", dest="paths", nargs="+", metavar="PATH", help="files or folders about to be edited")
    what.add_argument("--base", metavar="REF", help="the files changed since REF")
    ctx.set_defaults(func=cmd_context)

    # bondstone: CLI-agent
    instructions = commands.add_parser("agent", parents=[common],
                                       help="write the instructions for coding agents from the active profile")
    instructions.add_argument("--format", choices=["md", "skill"], default="md",
                              help="Markdown (default) or a Claude Code skill")
    instructions.add_argument("--output", metavar="FILE",
                              help=f"where to write (default: {agent.MARKDOWN_PATH}, or {agent.SKILL_PATH} "
                                   "for a skill); `-` prints instead")
    instructions.set_defaults(func=cmd_agent)

    # bondstone: CLI-graph
    graph = commands.add_parser("graph", parents=[common], help="export the graph of documents, links and code tags")
    graph.add_argument("--format", choices=["json", "mermaid"], default="json",
                       help="JSON (default) or a Mermaid diagram")
    graph.add_argument("--type", action="append", metavar="TYPE",
                       help="only nodes of this type; may be repeated (a diagram shows documents only by default)")
    graph.set_defaults(func=cmd_graph)

    # bondstone: CLI-rules
    rules = commands.add_parser("rules", parents=[common, output],
                                help="list the active rules with their effective severity")
    rules.set_defaults(func=cmd_rules)

    # bondstone: CLI-explain
    explain = commands.add_parser("explain", parents=[common, output],
                                  help="explain one rule: what it asks, why, and how to satisfy it")
    explain.add_argument("rule", metavar="RULE", help="a rule id such as adr/alternatives-considered")
    explain.set_defaults(func=cmd_explain)

    # bondstone: CLI-waive
    waiver = commands.add_parser("waive", parents=[common, output],
                                 help="add a waiver to the profile: one exception with a reason and an end")
    waiver.add_argument("rule", metavar="RULE", help="a rule id such as adr/alternatives-considered")
    waiver.add_argument("node", metavar="NODE", nargs="?",
                        help="the node the waiver is for (default: every node)")
    waiver.add_argument("--reason", required=True, help="why the exception is acceptable")
    waiver.add_argument("--expires", required=True, metavar="DATE", help="the last day it applies, as YYYY-MM-DD")
    waiver.set_defaults(func=cmd_waive)

    # bondstone: CLI-report
    reporting = commands.add_parser("report", parents=[common, output],
                                    help="count nodes, coverage, waivers, known violations and exemptions")
    reporting.add_argument("--base", metavar="REF", help="also count the exemptions used since REF")
    reporting.set_defaults(func=cmd_report)

    # bondstone: CLI-init
    init = commands.add_parser("init", parents=[common], help="create a profile in this folder")
    init.add_argument("--preset", metavar="NAME", help="extend this preset, such as `starter`")
    init.set_defaults(func=cmd_init)

    # bondstone: CLI-packs
    listing = commands.add_parser("packs", parents=[common, output],
                                  help="list the packs, bridges and presets available to this repository")
    listing.set_defaults(func=cmd_packs)

    pack = commands.add_parser("pack", help="pack commands")
    pack_commands = pack.add_subparsers(dest="pack_command", required=True, metavar="COMMAND")
    # bondstone: CLI-pack-test
    pack_test = pack_commands.add_parser("test", parents=[output],
                                         help="run the fixtures of packs, bridges and presets")
    pack_test.add_argument("dirs", nargs="+", metavar="DIR", help="folder of a pack, a bridge or a preset")
    pack_test.set_defaults(func=cmd_pack_test)

    profile = commands.add_parser("profile", help="profile commands")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True, metavar="COMMAND")
    # bondstone: CLI-profile-check
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
        return _stopped(args, "refused", exc, EXIT_VIOLATIONS)
    except (EnvironmentProblem, OSError) as exc:
        return _stopped(args, "environment", exc, EXIT_ENVIRONMENT)


# bondstone: REQ-CLI-009
def _stopped(args: argparse.Namespace, kind: str, exc: Exception, code: int) -> int:
    """Report why a command did nothing: on stderr, and with `--format json` as an object on stdout.

    The exit codes say whether work is wrong (1) or the checker could not run (3); the object
    lets a program tell a refused command from a check that found violations, which also exits with 1."""
    print(f"bondstone: {exc}", file=sys.stderr)
    if getattr(args, "format", None) == "json":
        _print_json({"version": JSON_VERSION, "error": {"kind": kind, "message": str(exc)}})
    return code
