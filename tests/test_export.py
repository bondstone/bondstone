"""`bondstone graph`: the JSON export, its schema and the Mermaid diagram."""

import json
from pathlib import Path

import pytest
from conftest import EXAMPLE, adr, capability, standard
from jsonschema import Draft202012Validator
from test_cli import run

import bondstone
from bondstone.config import load_config
from bondstone.export import graph_json, graph_mermaid, to_json
from bondstone.graph import build_graph
from bondstone.model import Refused

SCHEMA = json.loads((Path(bondstone.__file__).parent / "schemas" / "graph.schema.json").read_text(encoding="utf-8"))


@pytest.fixture
def loaded(project):
    standard(project, code={"include": ["src/*.py"]})
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "superseded"))
    project.write("docs/adr/ADR-002-b.md", adr("ADR-002", extra="supersedes: ADR-001\ndeciders: [ann]\n"))
    project.write("docs/capabilities/a.md", capability("CAP-a", "AA", extra="constrained_by: [ADR-002, ADR-009]\n"))
    project.write("src/a.py", "# bondstone: REQ-AA-001\ndef a():\n    return 1\n")
    cfg = load_config(project.root)
    return cfg, build_graph(cfg)


def test_the_export_matches_its_schema(loaded):
    Draft202012Validator.check_schema(SCHEMA)
    for root_graph in (loaded, (load_config(EXAMPLE), build_graph(load_config(EXAMPLE)))):
        payload = json.loads(to_json(graph_json(*root_graph)))
        assert list(Draft202012Validator(SCHEMA).iter_errors(payload)) == []


def test_nodes_edges_and_code(loaded):
    payload = graph_json(*loaded)
    assert payload["version"] == 1
    assert payload["components"] == [{"kind": "pack", "id": "adr", "version": "1.0.0"},
                                     {"kind": "pack", "id": "capability", "version": "1.0.0"},
                                     {"kind": "bridge", "id": "adr-capability", "version": "1.0.0"}]
    assert payload["roles"] == {"decision": ["adr:Decision"], "living-spec": ["capability:Capability"]}
    by_id = {node["id"]: node for node in payload["nodes"]}
    assert list(by_id) == ["ADR-001", "ADR-002", "CAP-a", "REQ-AA-001"]
    assert by_id["ADR-002"] == {"id": "ADR-002", "type": "adr:Decision", "path": "docs/adr/ADR-002-b.md", "line": 1,
                                "title": "Decision ADR-002", "status": "accepted", "covered": False,
                                "fields": {"owner": "me", "date": "2026-01-01", "deciders": ["ann"]}}
    assert by_id["REQ-AA-001"] == {"id": "REQ-AA-001", "type": "capability:Requirement", "path": "docs/capabilities/a.md",
                                   "line": 16, "title": "Thing", "status": "active", "parent": "CAP-a",
                                   "covered": True, "fields": {}}
    assert payload["edges"] == [
        {"from": "ADR-002", "to": "ADR-001", "link": "adr:supersedes"},
        {"from": "CAP-a", "to": "ADR-002", "link": "adr-capability:constrained_by"},
        {"from": "CAP-a", "to": "ADR-009", "link": "adr-capability:constrained_by"},  # broken links stay visible
    ]
    assert payload["code"] == [{"id": "REQ-AA-001", "path": "src/a.py", "start": 1, "end": 3}]


def test_types_limit_the_export(loaded):
    payload = graph_json(*loaded, ["Decision"])
    assert [node["id"] for node in payload["nodes"]] == ["ADR-001", "ADR-002"]
    assert payload["edges"] == [{"from": "ADR-002", "to": "ADR-001", "link": "adr:supersedes"}]
    assert payload["code"] == []
    assert [n["id"] for n in graph_json(*loaded, ["capability:Requirement"])["nodes"]] == ["REQ-AA-001"]
    with pytest.raises(Refused, match="unknown type 'Nope'"):
        graph_json(*loaded, ["Nope"])


def test_mermaid_shows_documents_grouped_by_type(loaded):
    assert graph_mermaid(*loaded) == (
        'flowchart LR\n'
        '  subgraph adr_Decision["adr:Decision"]\n'
        '    ADR_001["ADR-001<br/>Decision ADR-001"]\n'
        '    ADR_002["ADR-002<br/>Decision ADR-002"]\n'
        '  end\n'
        '  subgraph capability_Capability["capability:Capability"]\n'
        '    CAP_a["CAP-a<br/>Capability CAP-a"]\n'
        '  end\n'
        '  ADR_002 -->|supersedes| ADR_001\n'
        '  CAP_a -->|constrained_by| ADR_002\n')


def test_mermaid_with_items_draws_them_to_their_document(loaded):
    text = graph_mermaid(*loaded, ["Capability", "Requirement"])
    assert '    REQ_AA_001["REQ-AA-001<br/>Thing"]\n' in text
    assert text.endswith("  REQ_AA_001 -.-> CAP_a\n")
    assert "ADR" not in text


def test_mermaid_escapes_quotes_and_keeps_ids_apart(project):
    standard(project)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001").replace("title: Decision ADR-001", 'title: Say "no"'))
    project.write("docs/capabilities/a.md", capability("CAP-a.b", "AA"))
    project.write("docs/capabilities/b.md", capability("CAP-a_b", "BB"))
    cfg = load_config(project.root)
    text = graph_mermaid(cfg, build_graph(cfg))
    assert 'ADR_001["ADR-001<br/>Say #quot;no#quot;"]' in text
    assert 'CAP_a_b["CAP-a.b<br/>' in text and 'CAP_a_b_["CAP-a_b<br/>' in text


def test_graph_command(loaded, project, capsys):
    code, out, err = run(capsys, "--root", project.root, "graph")
    assert (code, err) == (0, "") and json.loads(out) == json.loads(to_json(graph_json(*loaded)))
    code, out, _ = run(capsys, "--root", project.root, "graph", "--format", "mermaid", "--type", "Decision")
    assert code == 0 and out == graph_mermaid(*loaded, ["Decision"])
    code, out, err = run(capsys, "--root", project.root, "graph", "--type", "Nope")
    assert code == 1 and "unknown type 'Nope'" in err
    assert json.loads(out)["error"]["kind"] == "refused"  # the default format of `graph` is JSON
    code, out, _ = run(capsys, "--root", project.root, "graph", "--format", "mermaid", "--type", "Nope")
    assert (code, out) == (1, "")
