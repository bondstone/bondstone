"""`bondstone new` and `bondstone init`."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .graph import Graph
from .loader import PROFILE_PATH, Config, as_list
from .model import BondstoneError
from .parser import slugify


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _git_user(root: Path) -> str:
    try:
        return subprocess.run(["git", "config", "user.name"], cwd=root, capture_output=True,
                              text=True).stdout.strip()
    except OSError:
        return ""


def next_id(tdef_qname: str, id_format: str, graph: Graph, slug: str) -> str:
    if "{slug" in id_format and "{n" not in id_format:
        return id_format.format(slug=slug.upper() if id_format.isupper() else slug)
    numbers = []
    for node in graph.nodes:
        if node.type == tdef_qname and node.id:
            m = re.search(r"(\d+)\D*$", node.id)
            if m:
                numbers.append(int(m.group(1)))
    return id_format.format(n=max(numbers, default=0) + 1, slug=slug)


def new_document(cfg: Config, graph: Graph, type_name: str, title: str,
                 sets: dict[str, Any]) -> Path:
    qname = type_name if ":" in type_name else next(
        (q for q in cfg.types if q.split(":", 1)[1] == type_name), type_name)
    tdef = cfg.types.get(qname)
    if tdef is None:
        raise BondstoneError(f"unknown type '{type_name}' (known: {', '.join(sorted(cfg.types))})")
    if tdef.spec.get("embedded"):
        raise BondstoneError(f"{qname} is an item type; add it as a heading inside its parent document")
    spec = tdef.spec
    slug = slugify(title)
    id_format = spec.get("id_format")
    if not id_format:
        raise BondstoneError(f"{qname} has no id_format; cannot scaffold")
    doc_id = str(sets.pop("id", None) or next_id(qname, id_format, graph, slug))

    fm: dict[str, Any] = {"id": doc_id, "title": title}
    lifecycle = tdef.traits.get("lifecycle")
    if lifecycle:
        fm["status"] = lifecycle.get("initial") or as_list(lifecycle.get("statuses"))[0]
    if "owned" in tdef.traits:
        fm["owner"] = (cfg.profile.get("defaults") or {}).get("owner") or _git_user(cfg.root)
    props = spec.get("fields") or {}
    for name in as_list(spec.get("required_fields")):
        if name not in fm:
            if (props.get(name) or {}).get("format") == "date":
                fm[name] = dt.date.today().isoformat()
            else:
                fm[name] = ""
    for link in cfg.links_from(qname):
        if link.min > 0:
            fm[link.name] = []
    fm.update(sets)

    body = ""
    template = spec.get("template")
    if template:
        body = (tdef.component_dir / template).read_text(encoding="utf-8")
        body = body.format_map(_SafeDict(**{k: str(v) for k, v in fm.items()}))
    else:
        body = "\n".join(f"## {s}\n\n<!-- todo: write {s.lower()} -->\n" for s in as_list(spec.get("sections")))

    directory = spec.get("dir")
    if not directory:
        first = as_list(spec.get("paths"))
        directory = str(Path(first[0]).parent) if first else "docs"
    filename = spec.get("filename", "{id}.md").format(id=doc_id, slug=slug)
    path = cfg.root / directory / filename
    if path.exists():
        raise BondstoneError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    front = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    path.write_text(f"---\n{front}---\n{body if body.startswith(chr(10)) else chr(10) + body}",
                    encoding="utf-8")
    return path


def init_profile(root: Path, packs: list[str], bridges: list[str]) -> Path:
    path = root / PROFILE_PATH
    if path.exists():
        raise BondstoneError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "bondstone": 0.1,
        "packs": packs,
        "bridges": bridges,
        "sources": [".bondstone/packs"],
        "code": {"include": [], "exclude": []},
        "overrides": {},
        "waivers": [],
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path

