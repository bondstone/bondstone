import pytest

from bondstone.config import load_config
from bondstone.graph import build_graph
from bondstone.select import describe, incoming_links, items, matches, natural_key, outgoing_links, sources, targets

ADR = """
    id: adr
    version: 1.0.0
    types:
      Decision:
        id: "ADR-{n:03d}"
        path: "docs/adr/{id}-{slug}.md"
        fields: {area: {type: string}, weight: {type: integer}}
        traits:
          lifecycle: {statuses: [proposed, accepted, superseded], initial: proposed}
          owned: {}
    links:
      supersedes: {from: Decision, to: Decision}
"""
CAPABILITY = """
    id: capability
    version: 1.0.0
    types:
      Capability:
        id: "CAP-{slug}"
        path: "docs/capabilities/{slug}.md"
        items: {type: Requirement, section: Requirements}
      Requirement:
        embedded: true
        traits: {code-traceable: {}}
    links:
      depends_on: {from: Capability, to: Capability}
"""
BRIDGE = """
    id: adr-capability
    version: 1.0.0
    requires: {adr: "^1", capability: "^1"}
    links:
      constrained_by: {from: capability:Capability, to: adr:Decision}
    roles:
      decision: [adr:Decision]
      living-spec: [capability:Capability]
"""


@pytest.fixture
def world(project):
    project.pack("adr", ADR).pack("capability", CAPABILITY).bridge("adr-capability", BRIDGE)
    project.profile(packs=["adr@1", "capability@1"], bridges=["adr-capability@1"],
                    code={"include": ["src/*.py"]})
    project.write("docs/adr/ADR-001-a.md",
                  "---\nid: ADR-001\ntype: adr:Decision\ntitle: A\nstatus: superseded\nowner: me\narea: storage\nweight: 1\n---\n")
    project.write("docs/adr/ADR-002-b.md",
                  "---\nid: ADR-002\ntype: adr:Decision\ntitle: B\nstatus: accepted\nowner: me\narea: sync\n"
                  "supersedes: ADR-001\n---\n")
    project.write("docs/capabilities/a.md",
                  "---\nid: CAP-a\ntype: capability:Capability\ntitle: Cap\nconstrained_by: [ADR-002, ADR-001, ADR-404]\n---\n"
                  "## Requirements\n\n### REQ-A-001: One\n\n### REQ-A-002: Two\n")
    project.write("src/a.py", "# bondstone: REQ-A-001\n")
    cfg = load_config(project.root)
    assert cfg.errors == []
    return cfg, build_graph(cfg)


def ids(cfg, graph, selector, context=None):
    return [n.id for n in graph.nodes if matches(cfg, n, selector, context)]


def test_empty_selector_matches_everything(world):
    cfg, graph = world
    assert len(ids(cfg, graph, None)) == len(ids(cfg, graph, {})) == 5


def test_type_is_qualified_outside_its_pack(world):
    cfg, graph = world
    assert ids(cfg, graph, {"type": "adr:Decision"}) == ["ADR-001", "ADR-002"]
    assert ids(cfg, graph, {"type": "Decision"}) == []  # unqualified, no pack context
    assert ids(cfg, graph, {"type": "Decision"}, context="adr") == ["ADR-001", "ADR-002"]
    assert ids(cfg, graph, {"type": "Decision"}, context="capability") == []
    assert ids(cfg, graph, {"type": ["Capability", "adr:Decision"]}, context="capability") == [
        "ADR-001", "ADR-002", "CAP-a"]


def test_role_trait_status_and_covered(world):
    cfg, graph = world
    assert ids(cfg, graph, {"role": "decision"}) == ["ADR-001", "ADR-002"]
    assert ids(cfg, graph, {"role": ["decision", "living-spec"]}) == ["ADR-001", "ADR-002", "CAP-a"]
    assert ids(cfg, graph, {"role": "nobody"}) == []
    assert ids(cfg, graph, {"trait": "lifecycle"}) == ["ADR-001", "ADR-002"]
    assert ids(cfg, graph, {"trait": ["lifecycle", "owned"]}) == ["ADR-001", "ADR-002"]
    assert ids(cfg, graph, {"trait": ["lifecycle", "code-traceable"]}) == []
    assert ids(cfg, graph, {"status": "accepted"}) == ["ADR-002"]
    assert ids(cfg, graph, {"status": ["accepted", "superseded"]}) == ["ADR-001", "ADR-002"]
    assert ids(cfg, graph, {"trait": "code-traceable", "covered": True}) == ["REQ-A-001"]
    assert ids(cfg, graph, {"trait": "code-traceable", "covered": False}) == ["REQ-A-002"]


def test_where_and_combination_with_and(world):
    cfg, graph = world
    assert ids(cfg, graph, {"where": {"area": "storage"}}) == ["ADR-001"]
    assert ids(cfg, graph, {"where": {"area": ["storage", "sync"]}}) == ["ADR-001", "ADR-002"]
    assert ids(cfg, graph, {"where": {"weight": 1}}) == ["ADR-001"]
    assert ids(cfg, graph, {"where": {"area": "storage", "weight": 2}}) == []
    assert ids(cfg, graph, {"type": "adr:Decision", "status": "accepted", "where": {"area": "sync"}}) == ["ADR-002"]
    assert ids(cfg, graph, {"type": "adr:Decision", "status": "accepted", "where": {"area": "storage"}}) == []


def test_link_resolution(world):
    cfg, graph = world
    cap, old, new = graph.by_id["CAP-a"], graph.by_id["ADR-001"], graph.by_id["ADR-002"]
    assert [l.qname for l in outgoing_links(cfg, cap.type, "constrained_by")] == ["adr-capability:constrained_by"]
    assert outgoing_links(cfg, old.type, "constrained_by") == []
    assert [l.qname for l in incoming_links(cfg, old.type, "adr-capability:constrained_by")] == [
        "adr-capability:constrained_by"]
    assert [n.id for n in targets(cfg, graph, cap, "constrained_by")] == ["ADR-002", "ADR-001"]  # broken link skipped
    assert [n.id for n in sources(cfg, graph, old, "constrained_by")] == ["CAP-a"]
    assert [n.id for n in sources(cfg, graph, old, "supersedes")] == ["ADR-002"]
    assert sources(cfg, graph, new, "supersedes") == []
    assert [n.id for n in items(graph, cap)] == ["REQ-A-001", "REQ-A-002"]


def test_describe_and_natural_order():
    assert describe(None) == ""
    assert describe({"type": "adr:Decision", "status": ["a", "b"]}) == " to type=adr:Decision status=['a', 'b']"
    assert describe({"type": "X"}, "from") == " from type=X"
    assert sorted(["ADR-10", "ADR-2", "ADR-1", None, "CAP-a"], key=natural_key) == [None, "ADR-1", "ADR-2", "ADR-10", "CAP-a"]
    assert sorted([3, "b", 1, "a"], key=natural_key) == [1, 3, "a", "b"]
