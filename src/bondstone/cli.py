"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .agent import agent_instructions, describe_rule, explain_rule
from .checks import has_errors, profile_problems, run_check
from .graph import build_graph
from .loader import LIBRARY, Config, find_root, index_components, load_config
from .model import ERROR, WARN, BondstoneError, Diagnostic
from .packtest import run_fixtures
from .scaffold import init_profile, new_document, supersede
from .views import generate


def _config(args: argparse.Namespace) -> Config:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    return load_config(root)


# bondstone: REQ-AGT-003
def _emit(diags: list[Diagnostic], fmt: str, extra: dict[str, Any] | None = None) -> None:
    errors = sum(d.severity == ERROR for d in diags)
    warnings = sum(d.severity == WARN for d in diags)
    if fmt == "json":
        payload = {"diagnostics": [d.to_dict() for d in diags],
                   "summary": {"errors": errors, "warnings": warnings, **(extra or {})}}
        print(json.dumps(payload, indent=2))
        return
    for d in diags:
        print(d.format())
    summary = f"{errors} error(s), {warnings} warning(s)"
    if extra:
        summary += "".join(f", {v} {k}" for k, v in extra.items())
    print(("✗ " if errors else "✓ ") + summary)


# bondstone: REQ-AGT-003
def cmd_check(args: argparse.Namespace) -> int:
    cfg = _config(args)
    graph = build_graph(cfg)
    diags = run_check(cfg, base=args.base, graph=graph)
    _emit(diags, args.format, {"nodes": len(graph.nodes)})
    return 1 if has_errors(diags, args.fail_on) else 0


def cmd_gen(args: argparse.Namespace) -> int:
    cfg = _config(args)
    written = generate(cfg, build_graph(cfg))
    for path in written:
        print(f"wrote {path}")
    if not written:
        print("views are up to date")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    cfg = _config(args)
    sets: dict[str, Any] = {}
    for item in args.set or []:
        key, _, value = item.partition("=")
        sets[key] = yaml.safe_load(value) if value else ""
    path = new_document(cfg, build_graph(cfg), args.type, args.title, sets)
    print(path.relative_to(cfg.root).as_posix())
    return 0


def _sets(items: list[str] | None) -> dict[str, Any]:
    sets: dict[str, Any] = {}
    for item in items or []:
        key, _, value = item.partition("=")
        sets[key] = yaml.safe_load(value) if value else ""
    return sets


def cmd_supersede(args: argparse.Namespace) -> int:
    cfg = _config(args)
    result = supersede(cfg, build_graph(cfg), args.id, args.title, _sets(args.set),
                       repoint=not args.no_repoint)
    print(f"created {result.created.relative_to(cfg.root).as_posix()}")
    for line in result.updated:
        print(f"updated {line}")
    for line in result.skipped:
        print(f"skipped {line}")
    written = generate(cfg, build_graph(load_config(cfg.root)))
    for path in written:
        print(f"wrote {path}")
    return 0


# bondstone: REQ-SCF-005
def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root or ".").resolve()
    packs = [p for p in (args.packs or "").split(",") if p]
    bridges = [b for b in (args.bridges or "").split(",") if b]
    path = init_profile(root, packs, bridges)
    print(f"created {path.relative_to(root).as_posix()}")
    cfg = load_config(root)
    for written in generate(cfg, build_graph(cfg)):
        print(f"wrote {written}")
    problems = profile_problems(cfg)
    for d in problems:
        print(d.format())
    return 1 if has_errors(problems) else 0


def cmd_profile_check(args: argparse.Namespace) -> int:
    cfg = _config(args)
    diags = profile_problems(cfg)
    _emit(diags, args.format)
    return 1 if has_errors(diags) else 0


def cmd_rules(args: argparse.Namespace) -> int:
    cfg = _config(args)
    if args.format == "json":
        print(json.dumps([{"id": r.qid, "owner": r.owner, "severity": cfg.overrides.get(r.qid, r.severity),
                           "locked": r.locked, "description": r.description, "spec": r.spec}
                          for r in cfg.rules], indent=2, default=str))
        return 0
    for rule in cfg.rules:
        print("- " + describe_rule(rule).replace("**", "").replace("`", ""))
    return 0


# bondstone: REQ-AGT-002
def cmd_explain(args: argparse.Namespace) -> int:
    cfg = _config(args)
    text = explain_rule(cfg, args.rule)
    if text is None:
        print(f"unknown rule '{args.rule}'", file=sys.stderr)
        return 2
    print(text)
    return 0


def cmd_agent(args: argparse.Namespace) -> int:
    cfg = _config(args)
    text = agent_instructions(cfg)
    if args.output:
        (cfg.root / args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text, end="")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    cfg = _config(args)
    graph = build_graph(cfg)
    payload = {
        "components": [{"kind": c.kind, "id": c.id, "version": c.version} for c in cfg.components],
        "roles": cfg.roles,
        "nodes": [{"id": n.id, "type": n.type, "path": n.path, "line": n.line, "status": n.status,
                   "title": n.title, "parent": n.parent,
                   "links": {lq: [r.target for r in refs] for lq, refs in n.links.items()}}
                  for n in graph.nodes],
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


def cmd_packs(args: argparse.Namespace) -> int:
    index = index_components([LIBRARY / "packs", LIBRARY / "bridges"])
    for (kind, cid), comps in sorted(index.items()):
        c = comps[0]
        print(f"{kind:6} {cid}@{c.version}  {c.data.get('description', '')}")
    return 0


# bondstone: REQ-PKT-001
def cmd_pack_test(args: argparse.Namespace) -> int:
    failed = 0
    for directory in args.dirs:
        results = run_fixtures(Path(directory).resolve())
        for r in results:
            print(f"{'PASS' if r.passed else 'FAIL'} {Path(directory).name}/{r.name}")
            if not r.passed:
                failed += 1
                print("   " + r.detail)
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bondstone", description=__doc__)
    parser.add_argument("--version", action="version", version=f"bondstone {__version__}")
    parser.add_argument("--root", help="repository root (default: nearest .bondstone/profile.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="validate documents, links, rules, code tags and views")
    p.add_argument("--base", help="git ref to diff against (enables lifecycle, immutability and diff rules)")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--fail-on", choices=[ERROR, WARN], default=ERROR)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("gen", help="regenerate views")
    p.set_defaults(func=cmd_gen)

    p = sub.add_parser("new", help="scaffold a new document")
    p.add_argument("type", help="document type, e.g. adr:Decision or Decision")
    p.add_argument("--title", required=True)
    p.add_argument("--set", action="append", metavar="KEY=VALUE", help="set a frontmatter key (YAML value)")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("supersede", help="replace a document with a new one and move links to it")
    p.add_argument("id", help="id of the document to supersede, e.g. ADR-001")
    p.add_argument("--title", required=True)
    p.add_argument("--set", action="append", metavar="KEY=VALUE")
    p.add_argument("--no-repoint", action="store_true", help="keep incoming links on the old document")
    p.set_defaults(func=cmd_supersede)

    p = sub.add_parser("init", help="create .bondstone/profile.yaml")
    p.add_argument("--packs", default="", help="comma-separated, e.g. adr@1,ost@1")
    p.add_argument("--bridges", default="")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("profile", help="profile commands")
    psub = p.add_subparsers(dest="profile_command", required=True)
    pc = psub.add_parser("check", help="validate the profile, packs and bridges")
    pc.add_argument("--format", choices=["text", "json"], default="text")
    pc.set_defaults(func=cmd_profile_check)

    p = sub.add_parser("rules", help="list active rules")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.set_defaults(func=cmd_rules)

    p = sub.add_parser("explain", help="explain a rule")
    p.add_argument("rule")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("agent", help="generate agent instructions")
    p.add_argument("--output", help="write to this file (relative to root)")
    p.set_defaults(func=cmd_agent)

    p = sub.add_parser("graph", help="export the document graph as JSON")
    p.set_defaults(func=cmd_graph)

    p = sub.add_parser("packs", help="list built-in packs and bridges")
    p.set_defaults(func=cmd_packs)

    p = sub.add_parser("pack", help="pack author commands")
    psub = p.add_subparsers(dest="pack_command", required=True)
    pt = psub.add_parser("test", help="run fixtures of packs/bridges")
    pt.add_argument("dirs", nargs="+")
    pt.set_defaults(func=cmd_pack_test)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BondstoneError as exc:
        print(f"bondstone: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
