"""Change documents through commands: scaffold one, change a status, supersede one.

Each function refuses what `check` would report afterwards, so a command either leaves the
repository valid or changes nothing. Existing files are edited one line at a time: comments,
key order and layout of the frontmatter stay as their author wrote them."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import PLACEHOLDER, RESERVED_KEYS, Config, as_list, qualify
from .graph import Graph
from .model import PART_OF, Node, Refused, TypeDef
from .parse import STATUS_RE

SLUG_LENGTH = 60


def slugify(text: str) -> str:
    """A title as a lower-case, hyphenated file-name part."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:SLUG_LENGTH].rstrip("-") or "untitled"


# --------------------------------------------------------------------------- frontmatter edits


def _frontmatter(lines: list[str]) -> tuple[int, int]:
    """First line and end (exclusive) of the frontmatter's content."""
    if not lines or lines[0].rstrip() != "---":
        raise Refused("the document has no frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() in ("---", "...")), None)
    if end is None:
        raise Refused("the document's frontmatter is not closed")
    return 1, end


def _block_style(text: str) -> list[str]:
    """The document's lines, with a frontmatter written as `{key: value, ...}` turned into one key per line.

    Frontmatter that already has one key per line is returned as it is."""
    lines = text.split("\n")
    start, end = _frontmatter(lines)
    if not any(lines[index].lstrip().startswith("{") for index in range(start, end)):
        return lines
    data = yaml.safe_load("\n".join(lines[start:end])) or {}
    return [*lines[:start], *_dump(data), *lines[end:]]


def _dump(frontmatter: dict[str, Any]) -> list[str]:
    """Frontmatter as lines: one key per line, lists in brackets."""
    return [f"{key}: {_scalar(value)}" for key, value in frontmatter.items()]


def _key_span(lines: list[str], key: str) -> tuple[int, int] | None:
    """Lines of a top-level key and its value: (first, end exclusive)."""
    start, end = _frontmatter(lines)
    pattern = re.compile(rf"^{re.escape(key)}\s*:")
    for index in range(start, end):
        if pattern.match(lines[index]):
            last = index + 1
            while last < end and (lines[last].startswith((" ", "\t", "-")) or not lines[last].strip()):
                last += 1
            while last > index + 1 and not lines[last - 1].strip():
                last -= 1
            return index, last
    return None


def _scalar(value: Any) -> str:
    """A value as YAML on one line."""
    return yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=10_000).strip().removesuffix("\n...")


# bondstone: REQ-SCF-005
def set_field(text: str, key: str, value: Any) -> str:
    """Set one top-level frontmatter key, replacing its line or adding one at the end."""
    lines = _block_style(text)
    span = _key_span(lines, key)
    line = f"{key}: {_scalar(value)}"
    if span is None:
        _, end = _frontmatter(lines)
        lines.insert(end, line)
    else:
        lines[span[0]:span[1]] = [line]
    return "\n".join(lines)


# bondstone: REQ-SCF-005
def replace_target(text: str, key: str, old: str, new: str) -> tuple[str, bool]:
    """Replace the id `old` with `new` in the value of one frontmatter key: (text, whether it changed)."""
    lines = _block_style(text)
    span = _key_span(lines, key)
    if span is None:
        return text, False
    pattern = re.compile(rf"(?<![\w-]){re.escape(old)}(?![\w-])")
    changed = False
    for index in range(*span):
        head, value = "", lines[index]
        if index == span[0]:
            name, colon, value = lines[index].partition(":")
            head = name + colon
        replaced = pattern.sub(new, value)
        if replaced != value:
            lines[index] = head + replaced
            changed = True
    return "\n".join(lines), changed


# bondstone: REQ-SCF-005
def set_item_status(text: str, heading_line: int, status_line: int | None, status: str) -> str:
    """Write the `Status:` line under an item's heading: change the one that is there, or add one."""
    lines = text.split("\n")
    if status_line is not None:
        index = status_line - 1
        if not STATUS_RE.match(lines[index]):
            raise Refused(f"line {status_line} is not a `Status:` line; was the file changed meanwhile?")
        lines[index] = f"Status: {status}"
    else:
        lines[heading_line:heading_line] = ["", f"Status: {status}"]
        after = heading_line + 2
        if after < len(lines) and lines[after].strip():
            lines.insert(after, "")
    return "\n".join(lines)


# --------------------------------------------------------------------------- scaffolding


@dataclass
class Created:
    id: str
    path: str  # repository-relative


def _resolve_type(cfg: Config, name: str) -> TypeDef:
    if name in cfg.types:
        tdef = cfg.types[name]
    else:
        found = [t for t in cfg.types.values() if t.name == name] if ":" not in name else []
        if len(found) > 1:
            raise Refused(f"type '{name}' is ambiguous; use one of {', '.join(sorted(t.qname for t in found))}")
        if not found:
            known = ", ".join(sorted(q for q, t in cfg.types.items() if not t.embedded)) or "none"
            raise Refused(f"unknown type '{name}' (known: {known})")
        tdef = found[0]
    if tdef.embedded:
        parents = sorted(t.qname for t in cfg.types.values() if t.items and t.items.type == tdef.qname)
        raise Refused(f"{tdef.qname} is an item type; add it as a heading inside a {' or '.join(parents)} document")
    return tdef


def _fill(template: str, values: dict[str, Any], what: str) -> str:
    """A template with its placeholders filled; refuses when a value is missing."""
    missing = sorted({name for name, _ in PLACEHOLDER.findall(template) if values.get(name) in (None, "")})
    if missing:
        raise Refused(f"the {what} '{template}' needs {', '.join(missing)}; pass --set {missing[0]}=...")

    def value(match: re.Match[str]) -> str:
        name, fmt = match.groups()
        return format(values[name], fmt) if fmt and isinstance(values[name], int) else str(values[name])

    return PLACEHOLDER.sub(value, template)


def _highest(template: str, ids: list[str], values: dict[str, Any] | None = None) -> int:
    """The highest number that one of `ids` carries in the `{n}` position of a template.

    A placeholder with a value in `values` must match that value; any other matches anything."""
    pattern, position = "", 0
    for match in PLACEHOLDER.finditer(template):
        pattern += re.escape(template[position:match.start()])
        name = match.group(1)
        if name == "n":
            pattern += r"(?P<n>\d+)"
        elif values and values.get(name) not in (None, ""):
            pattern += re.escape(str(values[name]))
        else:
            pattern += r".+?"
        position = match.end()
    pattern += re.escape(template[position:])
    return max((int(found.group("n")) for node_id in ids if (found := re.fullmatch(pattern, node_id))), default=0)


def _next_number(tdef: TypeDef, graph: Graph) -> int:
    """One more than the highest number that an id of this type carries in the `{n}` position."""
    template = tdef.id_template or ""
    if "n" not in {name for name, _ in PLACEHOLDER.findall(template)}:
        return 1
    return _highest(template, [node.id for node in graph.nodes if node.type == tdef.qname and node.id]) + 1


# bondstone: REQ-AGT-003
def next_item_id(cfg: Config, graph: Graph, document: Node) -> str | None:
    """The id the next item of a document gets, or None when its type has no numbered items.

    Items are headings added by hand, so nothing else hands out their ids."""
    items = cfg.types[document.type].items
    template = items.id_template if items else None
    if not template or "n" not in {name for name, _ in PLACEHOLDER.findall(template)}:
        return None
    values = {**document.fields, "id": document.id}
    if any(values.get(name) in (None, "") for name, _ in PLACEHOLDER.findall(template) if name != "n"):
        return None
    ids = [node.id for node in graph.nodes if node.is_item and node.parent == document.id and node.id]
    return _fill(template, {**values, "n": _highest(template, ids, values) + 1}, "id template")


def _git_user(root: Path) -> str:
    try:
        result = subprocess.run(["git", "config", "user.name"], cwd=root, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


# bondstone: REQ-SCF-001, REQ-SCF-002
def new_document(cfg: Config, graph: Graph, type_name: str, title: str, sets: dict[str, Any] | None = None,
                 today: dt.date | None = None, dry_run: bool = False) -> Created:
    """Scaffold a document of a type: next id, the type's path, valid frontmatter, the template's body.

    `sets` gives frontmatter values by field or link name; `id` and `slug` may be set too.
    Refuses rather than writing a document that `check` would reject. With `dry_run` it checks
    everything and says which id and path the document would get, without writing it."""
    tdef = _resolve_type(cfg, type_name)
    sets = dict(sets or {})
    spec, traits = tdef.spec, tdef.traits
    schema = cfg.schema_for(tdef.qname)
    links = {}
    for key in list(sets):
        if key in ("id", "slug") or key in schema["properties"]:
            continue
        link, error = cfg.resolve_link_key(tdef.qname, key)
        if error:
            raise Refused(error)
        if link is None:
            known = sorted({*schema["properties"], *(l.name for l in cfg.links_from(tdef.qname))} - {"status"})
            raise Refused(f"--set {key}: {tdef.qname} has no such field or link (known: {', '.join(known)})")
        links[key] = [str(target) for target in as_list(sets.pop(key))]
    if not title.strip():
        raise Refused("--title is empty")

    fields: dict[str, Any] = {"title": title.strip()}
    lifecycle = traits.get("lifecycle")
    if lifecycle:
        fields["status"] = sets.pop("status", None) or lifecycle.get("initial") or as_list(lifecycle.get("statuses"))[0]
    if "owned" in traits:
        # the person who creates a document owns it; the profile's default covers a machine without a git user
        owner = sets.pop("owner", None) or _git_user(cfg.root) or (cfg.profile.get("defaults") or {}).get("owner")
        if not owner:
            raise Refused(f"{tdef.qname} needs an owner; pass --set owner=..., set `user.name` in git, "
                          "or set `defaults.owner` in the profile")
        fields["owner"] = owner
    slug = str(sets.pop("slug", None) or slugify(title))
    explicit_id = sets.pop("id", None)
    for name in spec.get("required") or []:
        if name in fields or name in sets:
            continue
        if (schema["properties"].get(name) or {}).get("format") == "date":
            fields[name] = today or dt.date.today()
    fields.update(sets)
    missing = [name for name in schema["required"] if fields.get(name) in (None, "")]
    if missing:
        raise Refused(f"{tdef.qname} requires {', '.join(missing)}; pass --set {missing[0]}=...")
    for link in cfg.links_from(tdef.qname):
        given = len(links.get(link.name, links.get(link.qname, [])))
        if given < link.min:
            raise Refused(f"{tdef.qname} needs at least {link.min} '{link.name}' link(s); "
                          f"pass --set {link.name}=ID")
    unknown = sorted({target for targets in links.values() for target in targets} - set(graph.by_id))
    if unknown:
        raise Refused(f"no node with id {', '.join(unknown)}")

    values = {**fields, "slug": slug, "n": _next_number(tdef, graph)}
    doc_id = str(explicit_id) if explicit_id else _fill(tdef.id_template or "", values, "id template")
    if doc_id in graph.by_id:
        raise Refused(f"id '{doc_id}' is already used by {graph.by_id[doc_id].path}")
    values["id"] = doc_id
    path = _fill(tdef.path_template or "", values, "path template")
    if (cfg.root / path).exists():
        raise Refused(f"{path} already exists")

    if dry_run:
        return Created(doc_id, path)
    frontmatter = {"id": doc_id, "type": tdef.qname, **fields, **links}
    body = _body(tdef, {key: value for key, value in values.items()})
    target = cfg.root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    head = "\n".join(_dump(frontmatter))
    target.write_text(f"---\n{head}\n---\n\n{body.strip()}\n", encoding="utf-8", newline="\n")
    return Created(doc_id, path)


def _body(tdef: TypeDef, values: dict[str, Any]) -> str:
    """The type's template with `{field}` placeholders filled, or its sections with a todo each."""
    template = tdef.spec.get("template")
    if not template:
        return "\n".join(f"## {section}\n\n<!-- todo: write this section -->\n"
                         for section in tdef.spec.get("sections") or [])
    text = (tdef.component_dir / template).read_text(encoding="utf-8")
    return re.sub(r"\{(\w+)\}", lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text)


# --------------------------------------------------------------------------- status


@dataclass
class StatusChange:
    id: str
    path: str
    old: str | None
    new: str
    changed: bool = True


def _node(graph: Graph, node_id: str) -> Node:
    node = graph.by_id.get(node_id)
    if node is None:
        raise Refused(f"no node with id '{node_id}'")
    return node


def _is_immutable(cfg: Config, node: Node, changing: str | None = None) -> bool:
    """Whether a document may not be edited in its current status (`changing`: except that key)."""
    trait = cfg.types[node.type].traits.get("immutable")
    if trait is None:
        return False
    if "when" in trait and node.status not in {str(status) for status in as_list(trait["when"])}:
        return False
    allow = {str(key) for key in as_list(trait["allow"])} if "allow" in trait else {"status"}
    return changing not in allow


# bondstone: REQ-SCF-003
def change_status(cfg: Config, graph: Graph, node_id: str, new: str) -> StatusChange:
    """Move a document or an item to another status, when its lifecycle allows the step."""
    node = _node(graph, node_id)
    lifecycle = cfg.types[node.type].traits.get("lifecycle")
    derived = cfg.types[node.type].traits.get("derived-status")
    if derived:
        files = ", ".join(dict.fromkeys(path for condition in derived.values() for path in condition.values()))
        raise Refused(f"{node_id} is a {node.type}, whose status is derived from its files ({files}); "
                      "it cannot be set")
    if lifecycle is None:
        raise Refused(f"{node_id} is a {node.type}, which has no lifecycle")
    statuses = [str(status) for status in as_list(lifecycle.get("statuses"))]
    if new not in statuses:
        raise Refused(f"'{new}' is not a status of {node.type} (statuses: {', '.join(statuses)})")
    if node.status == new:
        return StatusChange(node_id, node.path, node.status, new, changed=False)
    transitions = lifecycle.get("transitions")
    if transitions is not None and node.status is not None:
        allowed = [str(status) for status in as_list(transitions.get(node.status))]
        if new not in allowed:
            raise Refused(f"{node_id} is '{node.status}', which cannot become '{new}' "
                          f"(allowed: {', '.join(allowed) or 'none'})")
    if not node.is_item and _is_immutable(cfg, node, changing="status"):
        raise Refused(f"{node_id} is immutable in status '{node.status}', and its status may not change either")
    path = cfg.root / node.path
    text = path.read_text(encoding="utf-8")
    if node.is_item:
        # always written out, also for the lifecycle's default: the line then says what was decided
        text = set_item_status(text, node.line, node.field_lines.get("status"), new)
    else:
        text = set_field(text, "status", new)
    path.write_text(text, encoding="utf-8", newline="\n")
    return StatusChange(node_id, node.path, node.status, new)


# --------------------------------------------------------------------------- supersede


@dataclass
class Superseded:
    created: Created
    updated: list[str] = field(default_factory=list)  # one line per edited document
    skipped: list[str] = field(default_factory=list)  # links that could not be moved, with the reason


# bondstone: REQ-SCF-004
def supersede(cfg: Config, graph: Graph, old_id: str, title: str, sets: dict[str, Any] | None = None,
              today: dt.date | None = None) -> Superseded:
    """Replace a document: create its successor, mark it superseded and move the links that pointed at it.

    Links from documents that are immutable in their current status stay where they are and
    are listed as skipped."""
    old = _node(graph, old_id)
    tdef = cfg.types[old.type]
    trait = tdef.traits.get("supersedable")
    if trait is None:
        raise Refused(f"{old_id} is a {old.type}, which is not supersedable")
    link = cfg.links[qualify(trait.get("link", "supersedes"), tdef.owner)]
    lifecycle = tdef.traits.get("lifecycle")
    if old.status == "superseded" or graph.sources(old_id, {link.qname}):
        raise Refused(f"{old_id} is already superseded")
    if lifecycle:
        if "superseded" not in as_list(lifecycle.get("statuses")):
            raise Refused(f"{old.type} has no 'superseded' status")
        transitions = lifecycle.get("transitions")
        if transitions is not None and "superseded" not in as_list(transitions.get(old.status)):
            allowed = ", ".join(str(status) for status in as_list(transitions.get(old.status))) or "none"
            raise Refused(f"{old_id} is '{old.status}', which cannot become 'superseded' (allowed: {allowed})")
        if _is_immutable(cfg, old, changing="status"):
            raise Refused(f"{old_id} is immutable in status '{old.status}', and its status may not change either")

    created = new_document(cfg, graph, old.type, title, {**(sets or {}), link.name: old_id}, today)
    result = Superseded(created)
    if lifecycle:
        path = cfg.root / old.path
        path.write_text(set_field(path.read_text(encoding="utf-8"), "status", "superseded"),
                        encoding="utf-8", newline="\n")
        result.updated.append(f"{old.path} (status: {old.status} -> superseded)")

    for link_qname, source in graph.incoming.get(old_id, []):
        if link_qname in (link.qname, PART_OF) or source.is_item:
            continue
        name = cfg.links[link_qname].name
        if _is_immutable(cfg, source):
            result.skipped.append(f"{source.path} ({name}: {old_id}): {source.id} is immutable in status "
                                  f"'{source.status}'")
            continue
        path = cfg.root / source.path
        text = path.read_text(encoding="utf-8")
        moved = False
        for key in source.field_lines:
            if key in RESERVED_KEYS:
                continue
            found, _ = cfg.resolve_link_key(source.type, key)
            if found is not None and found.qname == link_qname:
                text, changed = replace_target(text, key, old_id, created.id)
                moved |= changed
        if moved:
            path.write_text(text, encoding="utf-8", newline="\n")
            result.updated.append(f"{source.path} ({name}: {old_id} -> {created.id})")
    return result
