"""`bondstone new` and `bondstone init`."""

from __future__ import annotations

import datetime as dt
import re
import string
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .graph import Graph
from .edit import replace_id, set_scalar
from .loader import PROFILE_PATH, Config, as_list, qualify
from .model import PART_OF, BondstoneError
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


# bondstone: REQ-SCF-001
def next_id(tdef_qname: str, id_format: str, graph: Graph, slug: str,
            values: dict[str, Any] | None = None) -> str:
    """Next id from `id_format`; `{n}` numbers, `{slug}` and any `--set` key fill placeholders."""
    values = {k: str(v) for k, v in (values or {}).items()}
    fields = {name for _, name, _, _ in string.Formatter().parse(id_format) if name}
    missing = sorted(fields - {"n", "slug"} - set(values))
    if missing:
        raise BondstoneError(f"id_format '{id_format}' needs {', '.join(missing)}; "
                             f"pass --set {missing[0]}=...")
    n = 1
    if "n" in fields:
        numbers = []
        for node in graph.nodes:
            if node.type == tdef_qname and node.id:
                m = re.search(r"(\d+)\D*$", node.id)
                if m:
                    numbers.append(int(m.group(1)))
        n = max(numbers, default=0) + 1
    return id_format.format(n=n, slug=slug, **{k: v for k, v in values.items() if k in fields})


# bondstone: REQ-SCF-002, REQ-SCF-003
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
    doc_id = str(sets.pop("id", None) or next_id(qname, id_format, graph, slug, sets))

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


# bondstone: REQ-SCF-005
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



@dataclass
class SupersedeResult:
    created: Path
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


# bondstone: REQ-SCF-004
def supersede(cfg: Config, graph: Graph, old_id: str, title: str, sets: dict[str, Any],
              repoint: bool = True) -> SupersedeResult:
    """Create a successor of `old_id`, mark it superseded and move incoming links to it."""
    old = graph.by_id.get(old_id)
    if old is None:
        raise BondstoneError(f"no document with id '{old_id}'")
    tdef = cfg.types[old.type]
    sup = tdef.traits.get("supersedable")
    if sup is None:
        raise BondstoneError(f"{old.type} is not supersedable")
    link_qname = qualify(sup.get("link", "supersedes"), tdef.owner)
    link = cfg.links[link_qname]
    if any(lq == link_qname for lq, _ in graph.incoming.get(old_id, [])):
        raise BondstoneError(f"{old_id} is already superseded")
    lifecycle = tdef.traits.get("lifecycle")
    if lifecycle and old.status == "superseded":
        raise BondstoneError(f"{old_id} is already superseded")
    if lifecycle:
        if "superseded" not in as_list(lifecycle.get("statuses")):
            raise BondstoneError(f"{old.type} has no 'superseded' status")
        allowed = (lifecycle.get("transitions") or {}).get(old.status, [])
        if "superseded" not in allowed:
            raise BondstoneError(
                f"{old_id} is '{old.status}', which cannot become 'superseded' "
                f"(allowed: {', '.join(allowed) or 'none'})")

    created = new_document(cfg, graph, old.type, title, {link.name: old_id, **sets})
    result = SupersedeResult(created)
    new_id = _read_id(created)

    if lifecycle:
        path = cfg.root / old.path
        path.write_text(set_scalar(path.read_text(encoding="utf-8"), "status", "superseded"),
                        encoding="utf-8")
        result.updated.append(f"{old.path} (status: superseded)")

    if not repoint:
        return result
    for lq, src in graph.incoming.get(old_id, []):
        if lq in (link_qname, PART_OF) or src.parent is not None:
            continue
        src_traits = cfg.types[src.type].traits
        immutable = src_traits.get("immutable")
        if immutable and src.status in {str(s) for s in as_list(immutable.get("when"))}:
            result.skipped.append(f"{src.id} ({src.path}) is immutable in status '{src.status}'")
            continue
        keys = [k for k in src.raw_keys
                if (found := cfg.resolve_link_key(src.type, k)[0]) and found.qname == lq]
        path = cfg.root / src.path
        text = path.read_text(encoding="utf-8")
        changed_any = False
        for key in keys:
            text, changed = replace_id(text, key, old_id, new_id)
            changed_any |= changed
        if changed_any:
            path.write_text(text, encoding="utf-8")
            result.updated.append(f"{src.path} ({cfg.links[lq].name}: {old_id} -> {new_id})")
    return result


def _read_id(path: Path) -> str:
    from .parser import parse_document

    return str(parse_document(path.read_text(encoding="utf-8")).frontmatter["id"])


# bondstone: REQ-DIF-009
def set_baseline(root: Path, ref: str = "HEAD") -> str:
    """Record the commit `ref` points to as the profile's baseline; returns the commit id."""
    result = subprocess.run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=root,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise BondstoneError(f"cannot resolve '{ref}' to a commit: {result.stderr.strip()}")
    commit = result.stdout.strip()
    path = root / PROFILE_PATH
    text = path.read_text(encoding="utf-8")
    line = f"baseline: '{commit}'"  # quoted: ids like 1e5… would parse as numbers
    if re.search(r"^baseline:.*$", text, re.M):
        text = re.sub(r"^baseline:.*$", line, text, count=1, flags=re.M)
    elif re.search(r"^bondstone:.*$", text, re.M):
        text = re.sub(r"^(bondstone:.*)$", rf"\1\n{line}", text, count=1, flags=re.M)
    else:
        text = f"{line}\n{text}"
    path.write_text(text, encoding="utf-8")
    return commit
