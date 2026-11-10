import pytest

from bondstone import __version__
from bondstone.model import EnvironmentProblem
from bondstone.resolve import find_root, parse_ref, parse_version, range_is_valid, resolve, version_matches

PACK = """
    id: {id}
    version: {version}
"""
BRIDGE = """
    id: a-b
    version: 1.0.0
    requires: {{a: "{a}", b: "^1"}}
"""


@pytest.mark.parametrize("version,spec,ok", [
    ("1.2.0", "1", True), ("2.0.0", "1", False), ("1.2.0", "^1.3", False), ("1.4.1", "1.3", True),
    ("1.4.1", "^1", True), ("0.3.0", "0.1", True), ("1.0.0", "0.1", False),
    ("1.0.0", ">=1,<2", True), ("2.0.0", ">=1,<2", False), ("1.0.0", ">=1.0", True),
    ("0.9.0", ">=1.0", False), ("1.2.3", "==1.2.3", True), ("1.2.3", "=1.2.4", False),
    ("1.0.0", ">= 1.0, < 2", True),
    ("1.0.0a1", ">=1.0", True),  # pre-release suffixes are ignored
    ("1.0.0", None, True), ("1.0.0", "", True), ("1.0.0", "latest", False), ("x", "1", False),
])
def test_version_matches(version, spec, ok):
    assert version_matches(version, spec) is ok


def test_version_helpers():
    assert parse_version("1.2") == (1, 2, 0)
    assert parse_version("1.0.0-rc.1") == (1, 0, 0)
    assert parse_version("v1") is None
    assert range_is_valid("^1") and range_is_valid(">=1,<2") and not range_is_valid("~1") and not range_is_valid("")
    assert parse_ref("adr@1") == ("adr", "1")
    assert parse_ref("adr") == ("adr", None)
    assert version_matches(__version__, ">=1.0")


def test_find_root_walks_up_and_fails_as_an_environment_problem(project, tmp_path):
    project.profile()
    nested = tmp_path / "docs" / "adr"
    nested.mkdir(parents=True)
    assert find_root(nested) == tmp_path.resolve()
    with pytest.raises(EnvironmentProblem, match="no .bondstone/profile.yaml found"):
        find_root(tmp_path.parent)


def test_missing_profile_is_an_environment_problem(tmp_path):
    with pytest.raises(EnvironmentProblem):
        resolve(tmp_path)


def test_resolves_local_packs_and_bridges(project):
    project.pack("a", PACK.format(id="a", version="1.2.0"))
    project.pack("b", PACK.format(id="b", version="1.0.0"))
    project.bridge("a-b", BRIDGE.format(a="^1"))
    project.profile(packs=["a@1", "b"], bridges=["a-b@1"])
    result = resolve(project.root)
    assert result.problems == []
    assert [(c.kind, c.id, c.version, c.manifest) for c in result.components] == [
        ("pack", "a", "1.2.0", ".bondstone/packs/a/pack.yaml"),
        ("pack", "b", "1.0.0", ".bondstone/packs/b/pack.yaml"),
        ("bridge", "a-b", "1.0.0", ".bondstone/packs/a-b/bridge.yaml"),
    ]


def messages(project, **kwargs):
    return [d.message for d in resolve(project.root, **kwargs).problems]


def test_not_found_version_mismatch_and_wrong_list(project):
    project.pack("a", PACK.format(id="a", version="1.2.0"))
    project.pack("b", PACK.format(id="b", version="1.0.0"))
    project.bridge("a-b", BRIDGE.format(a="^1"))
    project.profile(packs=["a@2", "nope@1", "a-b", "b@one"], bridges=[])
    assert messages(project) == [
        "pack 'a': no version matches '2' (available: 1.2.0)",
        "pack 'nope' not found in the profile's sources",
        "pack 'a-b' not found: 'a-b' is a bridge; list it under `bridges`",
        "pack 'b': invalid version range 'one'",
    ]


def test_bridge_requirements(project):
    project.pack("a", PACK.format(id="a", version="1.2.0"))
    project.pack("b", PACK.format(id="b", version="1.0.0"))
    project.bridge("a-b", BRIDGE.format(a="^1.3"))
    project.profile(packs=["a@1"], bridges=["a-b@1"])
    assert messages(project) == [
        "bridge 'a-b' requires a ^1.3; the profile has 1.2.0",
        "bridge 'a-b' requires pack 'b', which is not in the profile",
    ]


def test_first_source_wins_and_listed_sources_must_exist(project):
    project.pack("a", PACK.format(id="a", version="1.0.0"), folder="first")
    project.pack("a", PACK.format(id="a", version="1.5.0"), folder="second")
    project.profile(packs=["a@1"], sources=["first", "second"])
    assert [c.manifest for c in resolve(project.root).components] == ["first/a/pack.yaml"]

    project.profile(packs=["a@1.2"], sources=["first", "second", "third"])
    result = resolve(project.root)
    assert [c.manifest for c in result.components] == ["second/a/pack.yaml"]
    assert [d.message for d in result.problems] == ["sources: folder 'third' does not exist"]


def test_default_source_and_extra_sources(project, tmp_path):
    project.profile(packs=["a@1"])
    assert messages(project) == ["pack 'a' not found in the profile's sources"]  # no folder: no error about it
    project.pack("a", PACK.format(id="a", version="1.0.0"), folder="elsewhere")
    result = resolve(project.root, extra_sources=[tmp_path / "elsewhere"])
    assert [c.id for c in result.components] == ["a"] and result.problems == []


def test_invalid_manifests_are_reported_at_their_own_path(project):
    project.pack("a", "id: a\nversion: 1.0.0\ntypes: {note: {}}\n")
    project.pack("b", "id: [b\n")
    project.pack("unused", "id: [broken\n")  # not named by the profile: not reported
    project.profile(packs=["a@1", "b"])
    problems = resolve(project.root).problems
    assert [(d.path, d.rule, d.severity) for d in problems] == [
        (".bondstone/packs/a/pack.yaml", "bondstone/profile", "error"),
        (".bondstone/packs/b/pack.yaml", "bondstone/profile", "error"),
    ]
    assert problems[1].message.startswith("invalid YAML:")


def test_invalid_profile_stops_resolution(project):
    project.write(".bondstone/profile.yaml", "bondstone: 0.1\npacks: [a@1]\n")
    result = resolve(project.root)
    assert result.profile is None and result.components == []
    assert [d.message for d in result.problems] == ["bondstone: expected the format version 1, got 0.1"]


def test_presets_duplicates_and_engine_range(project):
    project.pack("a", "id: a\nversion: 1.0.0\nbondstone: '>=2.0'\n")
    project.pack("b", "id: b\nversion: 1.0.0\nbondstone: 'soon'\n")
    project.profile(extends=["starter@1"], packs=["a@1", "a", "b"])
    assert messages(project) == [
        "extends: presets are not supported yet; list the packs and bridges in the profile",
        f"pack 'a' needs bondstone >=2.0; this is bondstone {__version__}",
        "packs: pack 'a' is listed more than once",
        "bondstone: invalid version range 'soon'",
    ]
