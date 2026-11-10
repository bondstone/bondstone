import json

from bondstone.format import JSON_VERSION, render, summarize, to_json, to_text
from bondstone.model import Diagnostic

DIAGNOSTICS = [
    Diagnostic("bondstone/link-broken", "error", "supersedes -> 'ADR-009': no such document",
               "docs/adr/ADR-002-b.md", 9, "ADR-002"),
    Diagnostic("adr/alternatives-considered", "warn", "Accepted decisions record alternatives.",
               "docs/adr/ADR-002-b.md", 1, "ADR-002", hint="Add a section."),
    Diagnostic("bondstone/supersede-orphan", "info", "ADR-001 is superseded but nothing supersedes it",
               "docs/adr/ADR-001-a.md", 5, "ADR-001"),
    Diagnostic("bondstone/view-stale", "error", "generated view adr/decision-log is out of date",
               "docs/generated/decisions.md", hint="Run `bondstone gen`.", fix={"command": ["bondstone", "gen"]}),
    Diagnostic("x/no-location", "warn", "somewhere"),
]


def test_summary_counts_by_severity():
    assert summarize(DIAGNOSTICS) == {"errors": 2, "warnings": 2, "info": 1}
    assert summarize(DIAGNOSTICS, nodes=7) == {"errors": 2, "warnings": 2, "info": 1, "nodes": 7}
    assert summarize([]) == {"errors": 0, "warnings": 0, "info": 0}


def test_text_is_one_line_per_diagnostic_with_an_indented_hint():
    assert to_text(DIAGNOSTICS, nodes=7) == (
        "docs/adr/ADR-002-b.md:9: error bondstone/link-broken: supersedes -> 'ADR-009': no such document\n"
        "docs/adr/ADR-002-b.md:1: warn adr/alternatives-considered: Accepted decisions record alternatives.\n"
        "    hint: Add a section.\n"
        "docs/adr/ADR-001-a.md:5: info bondstone/supersede-orphan: ADR-001 is superseded but nothing supersedes it\n"
        "docs/generated/decisions.md: error bondstone/view-stale: generated view adr/decision-log is out of date\n"
        "    hint: Run `bondstone gen`.\n"
        "<repository>: warn x/no-location: somewhere\n"
        "✗ 2 error(s), 2 warning(s), 1 info, 7 nodes\n"
    )
    assert to_text([]) == "✓ 0 error(s), 0 warning(s)\n"
    assert to_text(DIAGNOSTICS[1:2]).endswith("✓ 0 error(s), 1 warning(s)\n")


def test_json_has_the_same_fields_plus_node_and_fix():
    payload = json.loads(to_json(DIAGNOSTICS, nodes=7))
    assert list(payload) == ["version", "summary", "diagnostics"]
    assert payload["version"] == JSON_VERSION == 1
    assert payload["diagnostics"][0] == {
        "rule": "bondstone/link-broken", "severity": "error", "path": "docs/adr/ADR-002-b.md", "line": 9,
        "node": "ADR-002", "message": "supersedes -> 'ADR-009': no such document"}
    assert payload["diagnostics"][3]["fix"] == {"command": ["bondstone", "gen"]}
    assert payload["diagnostics"][4] == {"rule": "x/no-location", "severity": "warn", "message": "somewhere"}


def test_render_picks_the_format():
    assert render("json", []) == to_json([])
    assert render("text", [], nodes=3) == to_text([], nodes=3)
