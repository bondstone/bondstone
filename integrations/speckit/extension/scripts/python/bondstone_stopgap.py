#!/usr/bin/env python3
"""Bondstone stopgap: applies the simple-app profile until the CLI takes over.

Reads the living docs in docs/, the change docs in plan/, Spec Kit's folders in
specs/, test files and the JUnit report, and computes findings, each
requirement's evidence status, the phase and the one next step. It never opens
a network connection, calls a model, runs project code or reads production
code. Standard library only.

Usage: bondstone_stopgap.py (check|status|next) [--json] [--staged] [--change DIR] [--root DIR]
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = 1
STATUSES = ("draft", "stable", "deprecated")
DELTA_KINDS = ("ADDED", "MODIFIED", "REMOVED", "DEFERRED", "DROPPED")
SEP = " · "

# Living docs: path -> (type, id). Capabilities and decisions are globbed.
LIVING = {
    "docs/brief.md": ("brief", "BRIEF"),
    "docs/roadmap.md": ("roadmap", "ROADMAP"),
    "docs/ideas.md": ("ideas", "IDEAS"),
    "docs/glossary.md": ("glossary", "GLOSSARY"),
    "docs/architecture/overview.md": ("architecture", "ARCH"),
    "docs/ux/screens.md": ("screens", "SCREENS"),
    "docs/runbook.md": ("runbook", "RUNBOOK"),
}
CONSTITUTION = ".specify/memory/constitution.md"
CHANGELOG = "CHANGELOG.md"
DEFAULT_CONFIG = {
    "junit": ["build/test-results/*.xml"],
    "tests": ["tests/**/*.py", "tests/**/*.ts", "tests/**/*.js", "tests/**/*.kt",
              "tests/**/*.swift", "tests/**/*.java", "tests/**/*.go", "tests/**/*.rb",
              "**/*_test.go", "**/*.test.ts", "**/*.test.js", "**/*Test.kt", "**/*Tests.swift"],
}
CONFIG_PATH = ".specify/extensions/bondstone/bondstone-config.yml"

ID_RE = r"[A-Z][A-Z0-9]*-\d+(?:\.\d+)?"
HEADING_RE = re.compile(r"^(#{2,4})\s+(\S+)\s*(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
DELTA_RE = re.compile(r"^\s*[-*]?\s*(ADDED|MODIFIED|REMOVED|DEFERRED|DROPPED):\s*(.*)$")
EXAMPLE_RE = re.compile(r"^\s*[-*]\s+(?:\*\*)?(" + ID_RE + r")(?:\*\*)?\s*[:.]?\s+(.*)$")
TASK_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s")
CHANGE_DIR_RE = re.compile(r"^(\d{3,}|\d{8}-\d{6})-")
PLACEHOLDER_RE = re.compile(r"\[[A-Z][A-Z0-9_]{2,}\]")


class UsageError(Exception):
    pass


# ---------------------------------------------------------------- data model


@dataclass
class Finding:
    file: str
    line: int
    severity: str
    rule: str
    message: str

    def key(self):
        return (self.file, self.line, self.rule, self.message)

    def text(self):
        return f"{self.file}:{self.line}: {self.severity} {self.rule}: {self.message}"


@dataclass
class Doc:
    path: str
    fm: dict
    lines: list
    fm_end: int  # index of the first body line

    @property
    def status(self):
        return self.fm.get("status")

    @property
    def approved(self):
        return self.fm.get("status") == "stable"


@dataclass
class Example:
    id: str
    req: str
    line: int
    status: str = "untested"


@dataclass
class Requirement:
    id: str
    cap: str
    title: str
    path: str
    line: int
    fields: dict
    statement: str
    examples: list = field(default_factory=list)
    status: str = "untested"

    @property
    def release(self):
        return self.fields.get("Release")

    @property
    def pending(self):
        return [p.strip() for p in self.fields.get("Pending", "").split(",") if p.strip()]

    @property
    def manual(self):
        return self.fields.get("Check", "auto") == "manual"


@dataclass
class Version:
    id: str
    title: str
    line: int
    fields: dict

    @property
    def status(self):
        return self.fields.get("Status", "planned")


@dataclass
class Delta:
    kind: str
    ids: list
    target: str | None
    line: int


@dataclass
class Story:
    id: str
    title: str
    proves: list
    removes: list
    depends: list
    table_status: str
    path: str
    line: int
    epic: str | None
    prd: "Prd"
    change: "Change | None" = None
    status: str = "planned"


@dataclass
class Prd:
    doc: Doc
    version: str
    archived: bool
    deltas: list
    stories: list


@dataclass
class Change:
    folder: str
    spec: Doc | None
    story: str | None
    proves: list
    removes: list
    track: str | None
    has_plan: bool
    plan_has_impact: bool
    tasks_total: int
    tasks_done: int
    has_tasks: bool
    living_filled: bool
    clarify_open: bool
    tasks_text: str
    spec_text: str

    @property
    def finished(self):
        return self.has_tasks and self.tasks_total > 0 and self.tasks_done == self.tasks_total


# ---------------------------------------------------------------- parsing


def parse_scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [parse_scalar(v) for v in inner.split(",")] if inner else []
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_front_matter(lines):
    """A small YAML subset: `key: value`, inline lists, and `- item` lists."""
    if not lines or lines[0].strip() != "---":
        return None, 0
    fm, key = {}, None
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            return fm, i + 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = parse_scalar(m.group(2)) if m.group(2).strip() else []
        elif key and re.match(r"^\s+-\s+", line):
            if not isinstance(fm.get(key), list):
                fm[key] = []
            fm[key].append(parse_scalar(re.sub(r"^\s+-\s+", "", line)))
    return None, 0


def as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v)]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def split_ids(text: str):
    text = re.sub(r"`", "", text or "")
    if text.strip() in ("", "-", "—", "none", "None"):
        return []
    return [t.strip() for t in re.split(r"[,\s]+", text) if t.strip() and t.strip() not in ("-", "—")]


def parse_item_lines(lines, start):
    """Item lines: the first paragraph after a heading, `Name: value` pairs joined by ` · `."""
    fields, i = {}, start
    while i < len(lines) and not lines[i].strip():
        i += 1
    first = i
    while i < len(lines) and lines[i].strip():
        parts = [p.strip() for p in lines[i].split(SEP)]
        pairs = []
        for p in parts:
            m = re.match(r"^([A-Z][A-Za-z ]*?):\s*(.*)$", p)
            if not m:
                return {}, first
            pairs.append((m.group(1), m.group(2).strip().strip("`")))
        for k, v in pairs:
            fields[k] = v
        i += 1
    return fields, (i if fields else first)


def body_lines(doc: Doc):
    """Yield (index, line, in_code) for body lines."""
    in_code = False
    for i in range(doc.fm_end, len(doc.lines)):
        line = doc.lines[i]
        if FENCE_RE.match(line):
            in_code = not in_code
            yield i, line, True
            continue
        yield i, line, in_code


def section(doc: Doc, title_re: str):
    """Lines (index, text) of the `## ` section whose title matches, stopping at the next `## `."""
    out, inside = [], False
    for i, line, in_code in body_lines(doc):
        if not in_code and re.match(r"^##\s", line):
            if inside:
                break
            inside = bool(re.match(r"^##\s+" + title_re, line, re.I))
            continue
        if inside:
            out.append((i, line))
    return out, inside or bool(out)


def parse_table(rows):
    """Parse the first Markdown table in (index, line) rows into header and dict rows."""
    table = [(i, l) for i, l in rows if l.strip().startswith("|")]
    if len(table) < 2:
        return [], []
    cells = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    header = [c.lower() for c in cells(table[0][1])]
    out = []
    for i, l in table[2:]:
        values = cells(l)
        out.append((i, {header[k]: values[k] if k < len(values) else "" for k in range(len(header))}))
    return header, out


# ---------------------------------------------------------------- project


class Project:
    def __init__(self, root: Path, evidence=True, only_change=None):
        self.root = root
        self.evidence = evidence
        self.only_change = only_change
        self.findings: list[Finding] = []
        self.docs: dict[str, Doc] = {}
        self.capabilities: dict[str, Doc] = {}
        self.requirements: dict[str, Requirement] = {}
        self.examples: dict[str, Example] = {}
        self.decisions: dict[str, Doc] = {}
        self.versions: list[Version] = []
        self.prds: list[Prd] = []
        self.epics: dict[str, Doc] = {}
        self.stories: dict[str, Story] = {}
        self.changes: list[Change] = []
        self.retired: set[str] = set()
        self.tests_seen: dict[str, list] = {}   # example id -> test names in files
        self.results: dict[str, list] = {}      # example id -> ["pass"|"fail"]
        self.passing_tests = 0
        self.config = self.load_config()

    # -- helpers
    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def add(self, file, line, severity, rule, message):
        self.findings.append(Finding(file, line, severity, rule, message))

    def exists(self, rel):
        return (self.root / rel).is_file()

    def read_lines(self, rel):
        return (self.root / rel).read_text(encoding="utf-8").splitlines()

    def load_config(self):
        cfg = {k: list(v) for k, v in DEFAULT_CONFIG.items()}
        if self.exists(CONFIG_PATH):
            fm, _ = parse_front_matter(["---"] + self.read_lines(CONFIG_PATH) + ["---"])
            for k in cfg:
                if fm and k in fm:
                    cfg[k] = as_list(fm[k])
        return cfg

    def load_doc(self, rel, expect_type=None, expect_id=None, okf=True):
        lines = self.read_lines(rel)
        fm, end = parse_front_matter(lines)
        if fm is None:
            if okf:
                self.add(rel, 1, "error", "parse-error", "missing front-matter")
            fm, end = {}, 0
        elif okf:
            for key in ("type", "id", "title", "description", "status"):
                if not fm.get(key):
                    self.add(rel, 1, "error", "parse-error", f"front-matter has no `{key}`")
            if fm.get("status") and fm.get("status") not in STATUSES:
                self.add(rel, 1, "error", "parse-error",
                         f"status `{fm.get('status')}` is not draft, stable or deprecated")
            if expect_type and fm.get("type") and fm.get("type") != expect_type:
                self.add(rel, 1, "error", "parse-error", f"type should be `{expect_type}`")
            if expect_id and fm.get("id") and fm.get("id") != expect_id:
                self.add(rel, 1, "error", "parse-error", f"id should be `{expect_id}`")
        doc = Doc(rel, fm, lines, end)
        self.docs[rel] = doc
        return doc

    def glob(self, pattern):
        return sorted(p for p in self.root.glob(pattern) if p.is_file())

    # -- load everything
    def load(self):
        for rel, (typ, did) in LIVING.items():
            if self.exists(rel):
                self.load_doc(rel, typ, did)
        for p in self.glob("docs/capabilities/*.md"):
            doc = self.load_doc(self.rel(p), "capability")
            cid = doc.fm.get("id")
            if cid:
                if cid in self.capabilities:
                    self.add(doc.path, 1, "error", "unique-ids", f"{cid} is also {self.capabilities[cid].path}")
                self.capabilities[cid] = doc
                self.retired.update(as_list(doc.fm.get("retired")))
        for p in self.glob("docs/decisions/*.md"):
            doc = self.load_doc(self.rel(p), "decision")
            did = doc.fm.get("id")
            if did:
                if did in self.decisions:
                    self.add(doc.path, 1, "error", "unique-ids", f"{did} is also {self.decisions[did].path}")
                self.decisions[did] = doc
        self.load_roadmap()
        for doc in self.capabilities.values():
            self.load_requirements(doc)
        self.load_plans()
        self.load_changes()
        if self.evidence:
            self.load_evidence()
        self.compute_evidence()
        self.link_stories()

    def load_roadmap(self):
        doc = self.docs.get("docs/roadmap.md")
        if not doc:
            return
        for i, line, in_code in body_lines(doc):
            if in_code:
                continue
            m = HEADING_RE.match(line)
            if m and re.fullmatch(r"V-\d+(\.\d+)*", m.group(2)):
                fields, _ = parse_item_lines(doc.lines, i + 1)
                if any(v.id == m.group(2) for v in self.versions):
                    self.add(doc.path, i + 1, "error", "unique-ids", f"{m.group(2)} appears twice")
                    continue
                v = Version(m.group(2), m.group(3), i + 1, fields)
                if v.status not in ("planned", "active", "shipped"):
                    self.add(doc.path, i + 1, "error", "parse-error",
                             f"{v.id} status `{v.status}` is not planned, active or shipped")
                self.versions.append(v)

    def load_requirements(self, doc: Doc):
        cap = doc.fm.get("id")
        heads = []
        for i, line, in_code in body_lines(doc):
            if in_code:
                continue
            m = HEADING_RE.match(line)
            if m:
                heads.append((i, m))
        for n, (i, m) in enumerate(heads):
            rid = m.group(2)
            if not re.fullmatch(r"[A-Z][A-Z0-9]*-\d+", rid):
                continue
            end = heads[n + 1][0] if n + 1 < len(heads) else len(doc.lines)
            if not rid.startswith(f"{cap}-"):
                self.add(doc.path, i + 1, "error", "unique-ids", f"{rid} does not carry the prefix {cap}")
            if rid in self.requirements:
                self.add(doc.path, i + 1, "error", "unique-ids", f"{rid} appears twice")
                continue
            if rid in self.retired:
                self.add(doc.path, i + 1, "error", "unique-ids", f"{rid} is retired and cannot be reused")
            fields, j = parse_item_lines(doc.lines, i + 1)
            statement, examples, in_code = [], [], False
            for k in range(j, end):
                line = doc.lines[k]
                if FENCE_RE.match(line):
                    in_code = not in_code
                    continue
                if in_code:
                    continue
                em = EXAMPLE_RE.match(line)
                if em:
                    examples.append((em.group(1), em.group(2), k + 1))
                elif line.strip() and not examples:
                    statement.append(line.strip())
            req = Requirement(rid, cap, m.group(3), doc.path, i + 1, fields, " ".join(statement))
            self.requirements[rid] = req
            self.load_examples(req, examples)

    def load_examples(self, req: Requirement, examples):
        if not examples:
            self.add(req.path, req.line, "error", "requirement-has-example",
                     f"{req.id} has no example (`- {req.id}.1: Given …, when …, then …`)")
            return
        for eid, text, line in examples:
            if eid != req.id and not re.fullmatch(re.escape(req.id) + r"\.\d+", eid):
                self.add(req.path, line, "error", "example-id-scoped",
                         f"example {eid} under {req.id} must be {req.id}.<n>")
                continue
            if eid == req.id and len(examples) > 1:
                self.add(req.path, line, "error", "example-id-scoped",
                         f"{req.id} has several examples, so each needs a scoped ID such as {req.id}.1")
                continue
            if not (re.search(r"\bwhen\b", text, re.I) and re.search(r"\bthen\b", text, re.I)):
                self.add(req.path, line, "error", "requirement-has-example",
                         f"example {eid} needs WHEN and THEN")
            if eid in self.examples or (eid in self.retired and eid != req.id):
                self.add(req.path, line, "error", "unique-ids", f"example {eid} is a duplicate or retired ID")
                continue
            ex = Example(eid, req.id, line)
            self.examples[eid] = ex
            req.examples.append(ex)

    def load_plans(self):
        prd_paths = [(p, False) for p in self.glob("plan/*/prd.md") if p.parent.name != "archive"]
        prd_paths += [(p, True) for p in self.glob("plan/archive/*/prd.md")]
        for p, archived in prd_paths:
            ver = p.parent.name
            doc = self.load_doc(self.rel(p), "prd", f"PRD-{ver}")
            version = doc.fm.get("version") or f"V-{ver}"
            prd = Prd(doc, version, archived, [], [])
            self.prds.append(prd)
            rows, _ = section(doc, r"Deltas")
            for i, line in rows:
                m = DELTA_RE.match(line)
                if not m:
                    continue
                text, target = m.group(2), None
                if m.group(1) == "DEFERRED":
                    parts = re.split(r"\s+to\s+", text)
                    text, target = parts[0], (parts[1].strip().strip("`") if len(parts) > 1 else None)
                    if not target:
                        self.add(doc.path, i + 1, "error", "parse-error",
                                 "DEFERRED needs a target: `DEFERRED: HABIT-3 to V-1.2`")
                prd.deltas.append(Delta(m.group(1), split_ids(text), target, i + 1))
            self.load_story_table(doc, prd, None)
            for e in self.glob(f"{p.parent.relative_to(self.root).as_posix()}/epics/*.md"):
                edoc = self.load_doc(self.rel(e), "epic")
                if edoc.fm.get("id"):
                    self.epics[edoc.fm["id"]] = edoc
                self.load_story_table(edoc, prd, edoc.fm.get("id"))
        for p in self.glob("plan/*/release.md"):
            self.load_doc(self.rel(p), "release")

    def load_story_table(self, doc: Doc, prd: Prd, epic):
        rows, _ = section(doc, r"Stor(y|ies)")
        header, table = parse_table(rows)
        if not table:
            return
        col = lambda *names: next((h for h in header if h in names), None)
        cid, ctitle, cproves = col("id", "story"), col("title"), col("proves")
        cremoves, cdeps, cstatus = col("removes"), col("depends on", "depends"), col("status")
        if not cid or not cproves:
            self.add(doc.path, rows[0][0] + 1 if rows else 1, "error", "parse-error",
                     "story table needs ID and Proves columns")
            return
        for i, row in table:
            sid = row.get(cid, "").strip("` ")
            if not re.fullmatch(r"ST-\d+", sid):
                self.add(doc.path, i + 1, "error", "parse-error", f"story ID `{sid}` is not ST-<n>")
                continue
            if sid in self.stories:
                self.add(doc.path, i + 1, "error", "unique-ids", f"{sid} appears twice")
                continue
            st = Story(sid, row.get(ctitle, "") if ctitle else "", split_ids(row.get(cproves, "")),
                       split_ids(row.get(cremoves, "")) if cremoves else [],
                       split_ids(row.get(cdeps, "")) if cdeps else [],
                       (row.get(cstatus, "") if cstatus else "").strip().lower(),
                       doc.path, i + 1, epic, prd)
            self.stories[sid] = st
            prd.stories.append(st)

    def load_changes(self):
        specs = self.root / "specs"
        if not specs.is_dir():
            return
        for d in sorted(p for p in specs.iterdir() if p.is_dir() and CHANGE_DIR_RE.match(p.name)):
            rel = self.rel(d)
            spec = self.load_doc(f"{rel}/spec.md", okf=False) if (d / "spec.md").is_file() else None
            fm = spec.fm if spec else {}
            plan = (d / "plan.md").read_text(encoding="utf-8") if (d / "plan.md").is_file() else None
            tasks = (d / "tasks.md").read_text(encoding="utf-8") if (d / "tasks.md").is_file() else None
            marks = [m.group(1) for m in (TASK_RE.match(l) for l in (tasks or "").splitlines()) if m]
            spec_text = "\n".join(spec.lines) if spec else ""
            living, _ = section(spec, r"Living doc changes") if spec else ([], False)
            living_text = re.sub(r"<!--.*?-->", "", "\n".join(l for _, l in living), flags=re.S)
            self.changes.append(Change(
                folder=rel, spec=spec,
                story=(str(fm.get("story")) if fm.get("story") else None),
                proves=as_list(fm.get("proves")), removes=as_list(fm.get("removes")),
                track=(str(fm.get("track")) if fm.get("track") else None),
                has_plan=plan is not None,
                plan_has_impact=bool(plan and re.search(r"^##\s+Expected living-doc impact", plan, re.M | re.I)),
                tasks_total=len(marks), tasks_done=sum(1 for m in marks if m in "xX"),
                has_tasks=tasks is not None,
                living_filled=bool(living_text.strip()),
                clarify_open="[NEEDS CLARIFICATION" in spec_text,
                tasks_text=tasks or "", spec_text=spec_text))

    # -- evidence
    def id_pattern(self):
        prefixes = sorted({r.cap for r in self.requirements.values()}, key=len, reverse=True)
        if not prefixes:
            return None
        return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, prefixes)) +
                          r")[-_](\d+)(?:[._](\d+))?(?!\d)")

    def resolve_test_ids(self, name, pattern):
        """Map a test name to the example IDs it carries."""
        out = []
        for m in pattern.finditer(name):
            prefix, n, sub = m.group(1), m.group(2), m.group(3)
            rid = f"{prefix}-{n}"
            if sub and f"{rid}.{sub}" in self.examples:
                out.append(f"{rid}.{sub}")
            elif rid in self.examples:
                out.append(rid)
            else:
                out.append("?" + (f"{rid}.{sub}" if sub else rid))
        return out

    def load_evidence(self):
        pattern = self.id_pattern()
        if not pattern:
            return
        seen_files = set()
        for g in self.config["tests"]:
            for p in self.glob(g):
                if p in seen_files or any(part in ("node_modules", ".git", "build", ".specify")
                                          for part in p.relative_to(self.root).parts):
                    continue
                seen_files.add(p)
                try:
                    text = p.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                for n, line in enumerate(text.splitlines(), 1):
                    if not re.search(r"\b(def test|class Test|fun |func Test|it\(|test\(|@Test)", line) \
                            and not re.search(r"\btest_?[A-Z]", line):
                        continue
                    for eid in self.resolve_test_ids(line, pattern):
                        if eid.startswith("?"):
                            self.add(self.rel(p), n, "warning", "test-links-unknown-id",
                                     f"test names {eid[1:]}, which is no example")
                        else:
                            self.tests_seen.setdefault(eid, []).append(f"{self.rel(p)}:{n}")
        for g in self.config["junit"]:
            for p in self.glob(g):
                try:
                    tree = ET.parse(p)
                except ET.ParseError as e:
                    self.add(self.rel(p), 1, "error", "parse-error", f"JUnit report: {e}")
                    continue
                for case in tree.iter("testcase"):
                    if case.find("skipped") is not None:
                        continue
                    failed = case.find("failure") is not None or case.find("error") is not None
                    if not failed:
                        self.passing_tests += 1
                    name = f"{case.get('classname', '')} {case.get('name', '')}"
                    for eid in self.resolve_test_ids(name, pattern):
                        if not eid.startswith("?"):
                            self.results.setdefault(eid, []).append("fail" if failed else "pass")

    def compute_evidence(self):
        for ex in self.examples.values():
            res = self.results.get(ex.id, [])
            if "fail" in res:
                ex.status = "failing"
            elif res:
                ex.status = "passing"
            elif ex.id in self.tests_seen:
                ex.status = "linked"
            else:
                ex.status = "untested"
        for req in self.requirements.values():
            states = [e.status for e in req.examples] or ["untested"]
            if "failing" in states:
                req.status = "failing"
            elif req.manual and req.fields.get("Verified"):
                req.status = "manual"
            elif all(s == "passing" for s in states):
                req.status = "passing"
            elif "untested" in states:
                req.status = "untested"
            else:
                req.status = "linked"

    def link_stories(self):
        for ch in self.changes:
            if ch.story and ch.story in self.stories:
                st = self.stories[ch.story]
                if st.change is not None:
                    self.add(f"{ch.folder}/spec.md", 1, "error", "unique-ids",
                             f"{ch.story} already has {st.change.folder}")
                else:
                    st.change = ch
        for st in self.stories.values():
            if st.change and st.change.finished:
                st.status = "done"
            elif st.change:
                st.status = "in progress"
        for st in self.stories.values():
            if st.status == "planned":
                deps_done = all(self.stories.get(d) and self.stories[d].status == "done" for d in st.depends)
                st.status = "ready" if deps_done and st.prd.doc.approved else "blocked"

    # -- scope
    def version_index(self, vid):
        for n, v in enumerate(self.versions):
            if v.id == vid:
                return n
        return None

    @property
    def current(self) -> Version | None:
        for v in self.versions:
            if v.status != "shipped":
                return v
        return self.versions[-1] if self.versions else None

    @property
    def all_shipped(self):
        return bool(self.versions) and all(v.status == "shipped" for v in self.versions)

    def in_scope(self, req: Requirement):
        cur = self.current
        idx = self.version_index(req.release) if req.release else None
        if cur is None or idx is None:
            return False
        return idx <= self.version_index(cur.id)

    def prd_for(self, vid) -> Prd | None:
        return next((p for p in self.prds if p.version == vid and not p.archived), None) or \
            next((p for p in self.prds if p.version == vid), None)

    def expand(self, ids):
        """Example IDs that a list of requirement or example IDs covers."""
        out = []
        for i in ids:
            if i in self.requirements:
                out += [e.id for e in self.requirements[i].examples]
            elif i in self.examples:
                out.append(i)
        return out

    def known(self, i):
        return i in self.requirements or i in self.examples

    # ---------------------------------------------------------------- rules

    def check(self):
        self.rule_links()
        self.rule_deltas()
        self.rule_changes()
        if self.evidence:
            self.rule_evidence()
        if self.only_change:
            keep = self.only_change.rstrip("/") + "/"
            self.findings = [f for f in self.findings if f.file.startswith(keep)]
        uniq = {f.key(): f for f in self.findings}
        self.findings = sorted(uniq.values(), key=lambda f: (f.file, f.line, f.rule, f.message))
        return self.findings

    def added_pending(self):
        """IDs that unapproved PRDs add: not yet expected to exist."""
        out = set()
        for prd in self.prds:
            if not prd.doc.approved:
                for d in prd.deltas:
                    if d.kind == "ADDED":
                        out.update(d.ids)
        return out

    def rule_links(self):
        vids = {v.id for v in self.versions}
        for req in self.requirements.values():
            if not req.release:
                self.add(req.path, req.line, "error", "requirement-has-release",
                         f"{req.id} has no `Release:` line")
            elif self.versions and req.release not in vids:
                self.add(req.path, req.line, "error", "no-dangling-links",
                         f"{req.id} release {req.release} is not in the roadmap")
            for p in req.pending:
                if not any(prd.doc.fm.get("id") == p for prd in self.prds):
                    self.add(req.path, req.line, "error", "no-dangling-links", f"{req.id} pending {p} has no PRD")
        adding = self.added_pending()
        for prd in self.prds:
            if self.versions and prd.version not in vids:
                self.add(prd.doc.path, 1, "error", "no-dangling-links",
                         f"version {prd.version} is not in the roadmap")
            if prd.archived:
                continue
            for st in prd.stories:
                for i in st.proves + st.removes:
                    if not self.known(i) and i not in adding and i not in self.retired:
                        self.add(st.path, st.line, "error", "no-dangling-links", f"{st.id} names {i}, which does not exist")
                for d in st.depends:
                    if d not in self.stories:
                        self.add(st.path, st.line, "error", "no-dangling-links", f"{st.id} depends on unknown {d}")
        for ch in self.changes:
            path = f"{ch.folder}/spec.md"
            if not ch.spec:
                continue
            for i in ch.proves:
                if not self.known(i) and not (ch.finished and i in self.retired):
                    self.add(path, 1, "error", "no-dangling-links", f"proves {i}, which does not exist")

    def rule_deltas(self):
        for prd in self.prds:
            if prd.archived or not prd.doc.approved:
                continue
            pid = prd.doc.fm.get("id")
            proving = {}
            removing = {}
            for st in prd.stories:
                for i in st.proves:
                    proving.setdefault(i, []).append(st)
                for i in st.removes:
                    removing.setdefault(i, []).append(st)
            for d in prd.deltas:
                for i in d.ids:
                    req = self.requirements.get(i)
                    where = (prd.doc.path, d.line)
                    if d.kind == "ADDED":
                        if i in self.retired:
                            continue  # added, then dropped or removed later
                        if not req:
                            self.add(*where, "error", "delta-applied",
                                     f"ADDED {i} is not in docs/capabilities/ yet; write it as planned")
                        elif req.release != prd.version and not self.deferred(i):
                            self.add(req.path, req.line, "error", "delta-applied",
                                     f"{i} was added by {pid} and needs `Release: {prd.version}`")
                    elif d.kind == "DEFERRED":
                        if req and req.release != d.target:
                            self.add(req.path, req.line, "error", "delta-applied",
                                     f"{i} is deferred to {d.target} by {pid}")
                    elif d.kind == "DROPPED":
                        if req or i not in self.retired:
                            self.add(*where, "error", "delta-applied",
                                     f"DROPPED {i} must be deleted and listed under `retired`")
                    elif d.kind in ("MODIFIED", "REMOVED"):
                        stories = (proving if d.kind == "MODIFIED" else removing).get(i, [])
                        col = "Proves" if d.kind == "MODIFIED" else "Removes"
                        if not stories:
                            self.add(*where, "error", "delta-has-story",
                                     f"{d.kind} {i} needs a story that lists it under {col}")
                            continue
                        done = any(s.status == "done" for s in stories)
                        if d.kind == "REMOVED" and done:
                            if req or i not in self.retired:
                                self.add(*where, "error", "delta-applied",
                                         f"{i} was removed by a finished story; delete it and list it under `retired`")
                        elif not done and req and pid not in req.pending:
                            self.add(req.path, req.line, "error", "delta-applied",
                                     f"{i} waits for {d.kind} in {pid}: add `Pending: {pid}`")
                        elif done and req and pid in req.pending:
                            self.add(req.path, req.line, "error", "delta-applied",
                                     f"{i} was changed by a finished story; apply the wording and clear `Pending: {pid}`")

    def deferred(self, i):
        return any(d.kind == "DEFERRED" and i in d.ids for p in self.prds for d in p.deltas)

    def rule_changes(self):
        for ch in self.changes:
            path = f"{ch.folder}/spec.md"
            if not ch.spec:
                continue
            if not ch.story and ch.track != "quick":
                self.add(path, 1, "error", "change-has-story",
                         "front-matter needs `story: ST-<n>` and `proves: [...]`, or `track: quick`")
                continue
            st = self.stories.get(ch.story) if ch.story else None
            if ch.story and not st:
                self.add(path, 1, "error", "no-dangling-links", f"story {ch.story} is in no story table")
            if st and not st.prd.doc.approved:
                self.add(path, 1, "error", "story-before-approval",
                         f"{ch.story} belongs to {st.prd.doc.fm.get('id')}, which is not approved")
            if st and set(st.proves) != set(ch.proves) and not ch.finished:
                self.add(path, 1, "warning", "change-proves-mismatch",
                         f"proves {', '.join(ch.proves) or 'nothing'}; the story row says {', '.join(st.proves) or 'nothing'}")
            if ch.finished:
                if not ch.living_filled:
                    self.add(path, 1, "error", "change-living-docs",
                             "the story is finished but `## Living doc changes` is empty")
                continue
            # Unfinished change: the stopgap checks the analyze-time rules.
            for i in ch.proves:
                req = self.requirements.get(i) or (self.requirements.get(self.examples[i].req)
                                                   if i in self.examples else None)
                if req:
                    for sentence in re.split(r"(?<=[.;])\s+", req.statement):
                        s = " ".join(sentence.split())
                        if len(s) >= 40 and s in " ".join(ch.spec_text.split()):
                            self.add(path, 1, "error", "change-restates-requirement",
                                     f"restates {req.id}; refer to it by ID instead")
                            break
            if ch.has_plan and not ch.plan_has_impact:
                self.add(f"{ch.folder}/plan.md", 1, "error", "change-plan-impact",
                         "plan.md has no `## Expected living-doc impact` section")
            if ch.has_tasks:
                missing = [e for e in self.expand(ch.proves) if not re.search(
                    r"(?<![A-Za-z0-9])" + re.escape(e).replace(r"\-", "[-_]").replace(r"\.", "[._]") + r"(?![\d.])",
                    ch.tasks_text)]
                if missing:
                    self.add(f"{ch.folder}/tasks.md", 1, "error", "change-tasks-cover-examples",
                             f"no test task names {', '.join(missing)}")
                if not re.search(r"living doc", ch.tasks_text, re.I):
                    self.add(f"{ch.folder}/tasks.md", 1, "error", "change-tasks-cover-examples",
                             "no task updates the living docs")
        for st in self.stories.values():
            if st.table_status and st.table_status in ("done", "finished") and st.status != "done":
                self.add(st.path, st.line, "warning", "story-status-stale",
                         f"{st.id} is marked done but is {st.status}")
            elif st.status == "done" and st.table_status and st.table_status not in ("done", "finished"):
                self.add(st.path, st.line, "warning", "story-status-stale", f"{st.id} is done; mark its row done")

    def rule_evidence(self):
        for req in self.requirements.values():
            if not self.in_scope(req) or req.manual:
                continue
            if req.status == "untested":
                self.add(req.path, req.line, "warning", "requirement-covered",
                         f"{req.id} has examples without tests: " +
                         ", ".join(e.id for e in req.examples if e.status == "untested"))
            elif req.status in ("failing", "linked"):
                self.add(req.path, req.line, "warning", "requirement-passing", f"{req.id} is {req.status}")

    # ---------------------------------------------------------------- phases

    def doc_ok(self, rel):
        d = self.docs.get(rel)
        if not d:
            return False, f"write {rel}"
        if any(f.file == rel and f.severity == "error" for f in self.findings):
            return False, f"fix errors in {rel}"
        if not d.approved:
            return False, f"approve {d.fm.get('id', rel)}"
        return True, None

    def phases(self):
        out = []

        def phase(pid, name, opens, state=None):
            out.append({"id": pid, "name": name,
                        "state": state or ("done" if not opens else "open"), "open": opens})

        ok, why = self.doc_ok("docs/brief.md")
        phase(0, "inception", [] if ok else [why])
        opens = []
        for rel in ("docs/roadmap.md", "docs/architecture/overview.md"):
            ok, why = self.doc_ok(rel)
            if not ok:
                opens.append(why)
        first = self.versions[0] if self.versions else None
        fprd = self.prd_for(first.id) if first else None
        if not first:
            opens.append("add the first version to docs/roadmap.md")
        elif not fprd:
            opens.append(f"write plan/{first.id[2:]}/prd.md")
        else:
            ok, why = self.doc_ok(fprd.doc.path)
            if not ok:
                opens.append(why)
        phase(1, "shape", opens)
        opens = []
        if not self.exists(CONSTITUTION):
            opens.append("write the constitution with speckit.constitution")
        elif PLACEHOLDER_RE.search("\n".join(self.read_lines(CONSTITUTION))):
            opens.append("finish the constitution: it still has template placeholders")
        if not self.exists("docs/runbook.md"):
            opens.append("write docs/runbook.md")
        if self.evidence and self.passing_tests == 0:
            opens.append("get one passing test into the JUnit report (walking skeleton)")
        phase(2, "foundation", opens)
        cur = self.current
        if cur and self.version_index(cur.id) > 0 and not self.all_shipped:
            prd = self.prd_for(cur.id)
            opens = []
            if not prd:
                opens.append(f"write plan/{cur.id[2:]}/prd.md")
            else:
                ok, why = self.doc_ok(prd.doc.path)
                if not ok:
                    opens.append(why)
            phase(6, f"next version {cur.id}", opens)
        opens = self.build_opens()
        phase(3, f"build {cur.id}" if cur else "build", opens)
        phase(4, f"release {cur.id}" if cur else "release", self.release_opens())
        shipped = [v.id for v in self.versions if v.status == "shipped"]
        phase(5, "operate", [], "running" if shipped else "not started")
        return out

    def build_opens(self):
        cur = self.current
        if not cur:
            return ["add a version to docs/roadmap.md"]
        if self.all_shipped:
            return []
        opens = []
        prd = self.prd_for(cur.id)
        for st in (prd.stories if prd else []):
            if st.status != "done":
                opens.append(f"{st.id} is {st.status}")
        for req in sorted(self.requirements.values(), key=lambda r: r.id):
            if self.in_scope(req) and req.status not in ("passing", "manual"):
                opens.append(f"{req.id} is {req.status}")
        return opens

    def release_opens(self):
        cur = self.current
        if not cur or self.all_shipped:
            return []
        opens = []
        if self.build_opens():
            opens.append("finish build")
        rel = f"plan/{cur.id[2:]}/release.md"
        ok, why = self.doc_ok(rel)
        if not ok:
            opens.append(why.replace("approve ", "sign off ") if why.startswith("approve") else why)
        if not self.changelog_has(cur.id):
            opens.append(f"add a `## [{cur.id[2:]}…]` section to {CHANGELOG}")
        opens.append(f"mark {cur.id} `Status: shipped` in the roadmap and tag the release")
        return opens

    def changelog_has(self, vid):
        if not self.exists(CHANGELOG):
            return False
        ver = re.escape(vid[2:])
        return any(re.match(r"^##\s+\[?v?" + ver + r"(?![\d])", l) for l in self.read_lines(CHANGELOG))

    # ---------------------------------------------------------------- next

    def next_action(self):
        errors = [f for f in self.findings if f.severity == "error"]
        if errors:
            f = errors[0]
            return act("fix", f"{f.file}:{f.line}: {f.rule}: {f.message}", file=f.file,
                       more=len(errors) - 1)
        for ch in self.changes:
            if ch.finished or not ch.spec:
                continue
            label = ch.story or "quick fix"
            if ch.clarify_open:
                return act("run", f"{ch.folder} ({label}) has open clarification markers",
                           command="speckit.clarify", change=ch.folder)
            if not ch.has_plan:
                return act("run", f"{ch.folder} ({label}) has no plan.md", command="speckit.plan", change=ch.folder)
            if not ch.has_tasks:
                return act("run", f"{ch.folder} ({label}) has no tasks.md", command="speckit.tasks", change=ch.folder)
            return act("run", f"{ch.folder} ({label}) has {ch.tasks_total - ch.tasks_done} open tasks; "
                              "implement test-first, then update the living docs in the same commit",
                       command="speckit.implement", change=ch.folder)
        # Inception
        if not self.exists("docs/brief.md"):
            return act("write", "the project has no brief", doc="brief", path="docs/brief.md")
        for rel, kind in (("docs/glossary.md", "glossary"), ("docs/ideas.md", "ideas")):
            if not self.exists(rel):
                return act("write", f"Inception seeds the {kind}", doc=kind, path=rel)
        if not self.docs["docs/brief.md"].approved:
            return act("approve", "Inception ends when the brief is approved", doc="BRIEF", path="docs/brief.md")
        # Shape
        if not self.exists("docs/roadmap.md"):
            return act("write", "Shape starts with the roadmap: capabilities and the MVP slice",
                       doc="roadmap", path="docs/roadmap.md")
        if not self.versions:
            return act("write", "the roadmap has no version", doc="roadmap", path="docs/roadmap.md")
        if not self.exists("docs/architecture/overview.md"):
            return act("write", "Shape needs the architecture overview, data model and first ADRs",
                       doc="architecture", path="docs/architecture/overview.md")
        if not self.exists(CONSTITUTION):
            return act("run", "Shape drafts the constitution", command="speckit.constitution")
        first = self.versions[0]
        if not self.prd_for(first.id):
            return act("write", f"Shape ends with the PRD for {first.id}", doc="prd",
                       path=f"plan/{first.id[2:]}/prd.md")
        for rel in ("docs/roadmap.md", "docs/architecture/overview.md", self.prd_for(first.id).doc.path):
            if not self.docs[rel].approved:
                return act("approve", "Shape ends when the roadmap, architecture and first PRD are approved",
                           doc=self.docs[rel].fm.get("id", rel), path=rel)
        # Foundation
        foundation = next(p for p in self.phases() if p["id"] == 2)
        if foundation["open"]:
            o = foundation["open"][0]
            if "constitution" in o:
                return act("run", o, command="speckit.constitution")
            if "runbook" in o:
                return act("write", "Foundation writes the runbook", doc="runbook", path="docs/runbook.md")
            return act("build", "Foundation: build the walking skeleton (repo, CI, JUnit report, one deployed "
                                "screen, crash reporting, agent instructions) until one test passes in the report",
                       work="foundation")
        cur = self.current
        if self.all_shipped:
            return act("done", "every roadmap version is shipped; add the next version to the roadmap "
                               "when the owner picks one from the idea inbox")
        prd = self.prd_for(cur.id)
        if not prd:
            return act("write", f"next version: write the PRD for {cur.id}", doc="prd", path=f"plan/{cur.id[2:]}/prd.md")
        if not prd.doc.approved:
            return act("approve", f"no story of {cur.id} starts before its PRD is approved",
                       doc=prd.doc.fm.get("id"), path=prd.doc.path)
        # Build
        for st in prd.stories:
            if st.status == "ready":
                ids = ", ".join(st.proves + [f"removes {r}" for r in st.removes])
                return act("run", f"{st.id} is the first ready story", command="speckit.specify",
                           story=st.id, args=f"{st.id} {st.title}. Proves: {ids}", proves=st.proves)
        open_reqs = [r for r in sorted(self.requirements.values(), key=lambda r: r.id)
                     if self.in_scope(r) and r.status not in ("passing", "manual") and not r.manual]
        covered = {i for st in prd.stories for i in st.proves}
        uncovered = [r.id for r in open_reqs if r.id not in covered and
                     not any(e.id in covered for e in r.examples)]
        if uncovered:
            return act("write", f"in-scope requirements no story proves: {', '.join(uncovered)}; "
                                "add story rows (an amendment)", doc="prd", path=prd.doc.path)
        blocked = [st.id for st in prd.stories if st.status == "blocked"]
        if blocked:
            return act("fix", f"stories {', '.join(blocked)} are blocked by dependencies", file=prd.doc.path)
        if open_reqs:
            r = open_reqs[0]
            return act("build", f"{r.id} is {r.status} although its stories are done; "
                                "make its example tests pass", requirement=r.id)
        for r in sorted(self.requirements.values(), key=lambda r: r.id):
            if self.in_scope(r) and r.manual and not r.fields.get("Verified"):
                return act("verify", f"{r.id} is checked by hand; ask the person to verify it", requirement=r.id)
        # Release
        rel = f"plan/{cur.id[2:]}/release.md"
        if not self.exists(rel):
            return act("write", f"{cur.id} is built: write the release checklist with the drift audit "
                                "and a five-minute retro", doc="release", path=rel)
        if not self.docs[rel].approved:
            return act("approve", f"the owner signs off the {cur.id} release checklist",
                       doc=self.docs[rel].fm.get("id", rel), path=rel)
        if not self.changelog_has(cur.id):
            return act("write", f"add the {cur.id} section to {CHANGELOG}", doc="changelog", path=CHANGELOG)
        return act("approve", f"ship {cur.id}: the person marks it `Status: shipped` in the roadmap, tags "
                              f"the release and archives plan/{cur.id[2:]}/", doc="ROADMAP", path="docs/roadmap.md")

    # ---------------------------------------------------------------- reports

    def summary(self):
        return {"errors": sum(f.severity == "error" for f in self.findings),
                "warnings": sum(f.severity == "warning" for f in self.findings)}

    def requirement_rows(self):
        return [{"id": r.id, "capability": r.cap, "release": r.release, "in_scope": self.in_scope(r),
                 "status": r.status, "pending": r.pending,
                 "examples": {e.id: e.status for e in r.examples}}
                for r in sorted(self.requirements.values(), key=id_key)]

    def current_phase(self, phases):
        for p in phases:
            if p["state"] == "open":
                return p["name"]
        return "operate" if self.all_shipped else "release"


def act(action, reason, **extra):
    out = {"action": action, "reason": reason}
    out.update({k: v for k, v in extra.items() if v not in (None, "", [])})
    return out


def id_key(r):
    return [int(x) if x.isdigit() else x for x in re.split(r"[-.]", r.id)]


# ---------------------------------------------------------------- commands


def staged_copy():
    """Export the git index to a temporary directory."""
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        raise UsageError("--staged needs a git repository")
    tmp = tempfile.mkdtemp(prefix="bondstone-staged-")
    subprocess.run(["git", "checkout-index", "-a", f"--prefix={tmp}/"], cwd=top.stdout.strip(), check=True)
    return Path(tmp)


def render_status(p: Project, phases):
    cur = p.current
    out = [f"version: {cur.id + ' ' + cur.title if cur else 'none'} · phase: {p.current_phase(phases)}", "phases:"]
    for ph in phases:
        detail = ph["state"] if not ph["open"] else "open: " + "; ".join(ph["open"][:4]) + \
            (f"; +{len(ph['open']) - 4} more" if len(ph["open"]) > 4 else "")
        out.append(f"  {ph['id']} {ph['name']:<20} {detail}")
    caps = {}
    for r in p.requirements.values():
        if p.in_scope(r):
            caps.setdefault(r.cap, {}).setdefault(r.status, 0)
            caps[r.cap][r.status] += 1
    if caps:
        out.append("capabilities (in scope):")
        for c in sorted(caps):
            out.append(f"  {c:<10} " + SEP.join(f"{k} {caps[c].get(k, 0)}" for k in
                                                ("passing", "failing", "linked", "untested", "manual")))
    prd = p.prd_for(cur.id) if cur else None
    if prd and prd.stories:
        out.append(f"stories ({prd.doc.fm.get('id')}):")
        for st in prd.stories:
            extra = f" ({st.change.folder}: {st.change.tasks_done}/{st.change.tasks_total} tasks)" \
                if st.change and st.status != "done" else ""
            out.append(f"  {st.id} {st.status}{extra} · {st.title}")
    quick = [c for c in p.changes if c.track == "quick" and not c.finished]
    for c in quick:
        out.append(f"  quick fix {c.folder}: {c.tasks_done}/{c.tasks_total} tasks")
    s = p.summary()
    out.append(f"errors: {s['errors']} · warnings: {s['warnings']}")
    return "\n".join(out)


def render_next(a):
    lines = [f"{a['action']}: {a['reason']}"]
    for k in ("command", "args", "doc", "path", "change", "story", "file", "requirement"):
        if k in a:
            lines.append(f"  {k}: {a[k]}")
    return "\n".join(lines)


def main(argv):
    args = list(argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if args else 2
    cmd = args.pop(0)
    if cmd not in ("check", "status", "next"):
        raise UsageError(f"unknown command `{cmd}`")
    as_json = staged = False
    only_change, root = None, Path.cwd()
    while args:
        a = args.pop(0)
        if a == "--json":
            as_json = True
        elif a == "--staged" and cmd == "check":
            staged = True
        elif a == "--change" and args:
            only_change = args.pop(0).rstrip("/")
        elif a == "--root" and args:
            root = Path(args.pop(0))
        else:
            raise UsageError(f"unknown option `{a}`")
    tmp = None
    try:
        if staged:
            tmp = staged_copy()
            root = tmp
        p = Project(root.resolve(), evidence=not staged, only_change=only_change)
        p.load()
        p.check()
        if cmd == "check":
            if as_json:
                print(json.dumps({"schema_version": SCHEMA_VERSION, "summary": p.summary(),
                                  "findings": [f.__dict__ for f in p.findings],
                                  "requirements": p.requirement_rows()}, indent=2, sort_keys=True))
            else:
                for f in p.findings:
                    print(f.text())
                s = p.summary()
                print(f"errors: {s['errors']} · warnings: {s['warnings']}")
            return 1 if p.summary()["errors"] else 0
        phases = p.phases()
        if cmd == "status":
            if as_json:
                cur = p.current
                print(json.dumps({"schema_version": SCHEMA_VERSION, "version": cur.id if cur else None,
                                  "phase": p.current_phase(phases), "phases": phases,
                                  "requirements": p.requirement_rows(),
                                  "stories": [{"id": s.id, "status": s.status, "title": s.title,
                                               "change": s.change.folder if s.change else None}
                                              for s in p.stories.values()],
                                  "summary": p.summary()}, indent=2, sort_keys=True))
            else:
                print(render_status(p, phases))
            return 0
        a = p.next_action()
        print(json.dumps(dict(a, schema_version=SCHEMA_VERSION), indent=2, sort_keys=True) if as_json
              else render_next(a))
        return 0
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except UsageError as e:
        print(f"usage error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:  # noqa: BLE001 - exit code 3 is part of the contract
        print(f"internal error: {e!r}", file=sys.stderr)
        sys.exit(3)
