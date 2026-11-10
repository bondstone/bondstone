import re
import textwrap

import pytest

from bondstone.model import Heading
from bondstone.parse import find_headings, find_items, mask_code, parse_document

ITEM = re.compile(r"^(?P<id>[^\s:]+):\s*(?P<title>.+?)$")


def doc(text: str):
    return parse_document(textwrap.dedent(text).lstrip("\n"))


# --------------------------------------------------------------------------- frontmatter


def test_frontmatter_fields_lines_and_body():
    parsed = doc("""
        ---
        id: ADR-002
        title: Store habits locally
        date: 2026-10-12
        deciders: [dawid]
        supersedes: ADR-001
        ---
        ## Context

        Text.
    """)
    assert parsed.error is None
    assert parsed.frontmatter == {"id": "ADR-002", "title": "Store habits locally", "date": "2026-10-12",
                                  "deciders": ["dawid"], "supersedes": "ADR-001"}
    assert parsed.field_lines == {"id": 2, "title": 3, "date": 4, "deciders": 5, "supersedes": 6}
    assert parsed.body_line == 8
    assert parsed.body == "## Context\n\nText."
    assert parsed.headings == [Heading(2, "Context", 8)]


def test_field_lines_skip_nested_keys_list_items_and_comments():
    parsed = doc("""
        ---
        # a comment: with a colon
        id: X-1
        tags:
          - a: b
        nested:
          inner: value
        "quoted key": 1
        url: http://example.com
        ---
    """)
    assert parsed.field_lines == {"id": 3, "tags": 4, "nested": 6, "quoted key": 8, "url": 9}
    assert parsed.frontmatter["url"] == "http://example.com"
    assert parsed.body == "" and parsed.headings == []


def test_values_are_normalized():
    parsed = doc("""
        ---
        date: 2026-01-02
        at: 2026-01-02 10:00:00
        1: one
        ---
    """)
    assert parsed.frontmatter == {"date": "2026-01-02", "at": "2026-01-02T10:00:00", "1": "one"}


def test_no_frontmatter():
    parsed = doc("""
        # Title

        Text with --- in it.
    """)
    assert parsed.frontmatter is None and parsed.error is None
    assert parsed.body_line == 1 and parsed.headings == [Heading(1, "Title", 1)]
    assert parse_document("").frontmatter is None
    assert parse_document("\n---\nid: X\n---\n").frontmatter is None  # must start on the first line


def test_empty_frontmatter_and_alternative_end_marker():
    assert parse_document("---\n---\nbody\n").frontmatter == {}
    parsed = parse_document("---\nid: X\n...\nbody\n")
    assert parsed.frontmatter == {"id": "X"} and parsed.body == "body"


def test_bom_and_crlf():
    parsed = parse_document("﻿---\r\nid: X\r\n---\r\n## A\r\n")
    assert parsed.frontmatter == {"id": "X"}
    assert parsed.headings == [Heading(2, "A", 4)]


@pytest.mark.parametrize("text,error,line", [
    ("---\nid: X\n", "frontmatter is not closed with '---'", 1),
    ("---\nid: [X\n---\n", "invalid frontmatter YAML:", 2),
    ("---\nid: X\n  bad: indent\n---\n", "invalid frontmatter YAML:", 3),
    ("---\n- a\n- b\n---\n", "frontmatter must be a mapping of keys to values", 2),
    ("---\njust text\n---\n", "frontmatter must be a mapping of keys to values", 2),
])
def test_frontmatter_errors(text, error, line):
    parsed = parse_document(text)
    assert parsed.frontmatter is None
    assert parsed.error.startswith(error)
    assert parsed.error_line == line


# --------------------------------------------------------------------------- headings


def test_headings_levels_and_closing_hashes():
    lines = ["# One", "## Two ##", "###Not a heading", "   ### Indented three", "    #### Code, not a heading",
             "####### Seven", "## ", "#", "Setext", "======", "## Trailing #hash", "## C# and F#"]
    assert find_headings(lines, 10) == [
        Heading(1, "One", 10), Heading(2, "Two", 11), Heading(3, "Indented three", 13),
        Heading(2, "Trailing #hash", 20), Heading(2, "C# and F#", 21)]


def test_headings_inside_fenced_code_are_ignored():
    text = textwrap.dedent("""
        ## Real

        ```md
        ## In backticks
        ~~~
        ## Still in backticks
        ```

        ~~~~
        ## In tildes
        ~~~
        ## Still in tildes: the fence is shorter
        ~~~~

        ## Real again

        ```python
        # a comment, not a heading
    """).strip("\n")
    assert [(h.title, h.line) for h in find_headings(text.split("\n"), 1)] == [("Real", 1), ("Real again", 15)]


def test_inline_backticks_do_not_open_a_fence():
    lines = ["``` not a fence ``` inline", "## Heading"]
    assert [h.title for h in find_headings(lines, 1)] == ["Heading"]


def test_mask_code_keeps_offsets():
    text = "a `<!-- todo: x -->` b\n```\n<!-- todo: y -->\n```\n<!-- todo: z -->\n``double `tick` span``\n"
    masked = mask_code(text)
    assert len(masked) == len(text)
    assert masked.count("\n") == text.count("\n")
    assert masked.count("todo") == 1 and masked.index("todo") == text.index("todo: z")
    assert "tick" not in masked


# --------------------------------------------------------------------------- items

CAPABILITY = """
    ---
    id: CAP-reminders
    code: REM
    ---
    ## Purpose

    ### REQ-REM-900: Outside the section

    ## Requirements

    ### REQ-REM-001: Remind at the usual time

    The app SHALL remind.

    #### Scenario: Usual time

    - Then a reminder

    ### REQ-REM-002: Snooze a reminder

    Status: planned

    The app SHALL snooze.

    ### Not a requirement heading

    text

    #### REQ-REM-003: Wrong level

    ## Notes

    ### REQ-REM-004: After the section
"""


def test_items_are_read_only_under_their_section():
    parsed = doc(CAPABILITY)
    scan = find_items(parsed, 3, ITEM, "Requirements")
    assert [(i.id, i.title, i.line, i.end_line) for i in scan.items] == [
        ("REQ-REM-001", "Remind at the usual time", 11, 18),
        ("REQ-REM-002", "Snooze a reminder", 19, 24),
    ]
    assert scan.malformed == [Heading(3, "Not a requirement heading", 25)]


def test_item_body_headings_and_status():
    first, second = find_items(doc(CAPABILITY), 3, ITEM, "Requirements").items
    assert first.body.strip().startswith("The app SHALL remind.")
    assert "REQ-REM-002" not in first.body
    assert first.headings == [Heading(4, "Scenario: Usual time", 15)]
    assert (first.status, first.status_line) == (None, None)
    assert first.body_line == 12
    assert (second.status, second.status_line) == ("planned", 21)
    assert second.headings == []


def test_items_without_a_section_are_read_everywhere():
    scan = find_items(doc(CAPABILITY), 3, ITEM, None)
    assert [i.id for i in scan.items] == ["REQ-REM-900", "REQ-REM-001", "REQ-REM-002", "REQ-REM-004"]
    assert [h.title for h in scan.malformed] == ["Not a requirement heading"]


def test_status_line_must_be_the_first_text_of_the_item():
    parsed = doc("""
        ## Requirements

        ### R-1: First
        Status: removed
        ### R-2: Second

        Some text first.

        Status: planned
        ### R-3: Third

        Status:
        ### R-4: Fourth

        status: lower case is not a status line
    """)
    items = find_items(parsed, 3, ITEM, "Requirements").items
    assert [(i.id, i.status, i.status_line) for i in items] == [
        ("R-1", "removed", 4), ("R-2", None, None), ("R-3", "", 12), ("R-4", None, None)]


def test_last_item_runs_to_the_end_and_nested_levels_end_items():
    parsed = doc("""
        # Doc

        ## Requirements

        ### R-1: First

        text

        ## Other

        ## Requirements

        ### R-2: Second

        last line
    """)
    items = find_items(parsed, 3, ITEM, "Requirements").items
    assert [(i.id, i.line, i.end_line) for i in items] == [("R-1", 5, 8), ("R-2", 13, 15)]
    assert items[1].body == "\nlast line"


def test_items_in_a_document_without_body_or_headings():
    assert find_items(parse_document("---\nid: X\n---\n"), 3, ITEM, None).items == []
    assert find_items(parse_document("no headings\n"), 3, ITEM, "Requirements").items == []
