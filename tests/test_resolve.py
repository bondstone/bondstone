import pytest

from bondstone import __version__
from bondstone.model import EnvironmentProblem
from bondstone import resolve as resolver
from bondstone.resolve import (find_root, find_sources, installed_sources, parse_ref, parse_version, range_is_valid,
                               resolve, shown_path, version_matches)

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
        "pack 'nope' not found in the profile's sources or in an installed package",
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
    assert messages(project) == ["pack 'a' not found in the profile's sources or in an installed package"]  # no folder: no error about it
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


def test_duplicates_and_engine_range(project):
    project.pack("a", "id: a\nversion: 1.0.0\nbondstone: '>=2.0'\n")
    project.pack("b", "id: b\nversion: 1.0.0\nbondstone: 'soon'\n")
    project.profile(packs=["a@1", "a", "b"])
    assert messages(project) == [
        "packs: pack 'a' is listed more than once",
        f"pack 'a' needs bondstone >=2.0; this is bondstone {__version__}",
        "bondstone: invalid version range 'soon'",
    ]


# ----------------------------------------------------------------------- installed packages


class FakeEntry:
    """Stands in for an entry point of an installed package."""

    def __init__(self, name, target, package="acme-packs"):
        self.name, self._target = name, target
        self.dist = type("Dist", (), {"name": package})() if package else None

    def load(self):
        if isinstance(self._target, Exception):
            raise self._target
        return self._target


@pytest.fixture
def installed(monkeypatch):
    """Replace the installed packages that register pack sources."""
    def install(*entries):
        monkeypatch.setattr(resolver, "entry_points", lambda group: list(entries) if group == "bondstone.sources" else [])
    return install


def test_the_library_registers_its_folder():
    from conftest import LIBRARY_PACKS
    sources, errors = installed_sources()
    assert errors == []
    assert [(s.label, s.dir, s.installed) for s in sources] == [("bondstone-library", LIBRARY_PACKS, True)]


def test_packs_of_installed_packages_resolve_after_the_profiles_sources(project, tmp_path_factory, installed):
    site = tmp_path_factory.mktemp("site-packages") / "acme"
    Project = type(project)
    Project(site).pack("a", PACK.format(id="a", version="1.5.0"), folder=".").pack(
        "b", PACK.format(id="b", version="1.0.0"), folder=".")
    installed(FakeEntry("acme", lambda: site))
    project.pack("a", PACK.format(id="a", version="1.2.0"))
    project.profile(packs=["a@1", "b@1"])
    result = resolve(project.root)
    assert result.problems == []
    assert [(c.id, c.version, c.manifest) for c in result.components] == [
        ("a", "1.2.0", ".bondstone/packs/a/pack.yaml"),  # the local copy wins
        ("b", "1.0.0", (site / "b" / "pack.yaml").as_posix()),  # outside the repository: the full path
    ]

    project.profile(packs=["a@1.5"])  # the local copy is too old, the installed one fits
    assert [c.version for c in resolve(project.root).components] == ["1.5.0"]


def test_an_installed_source_may_be_a_path_and_sources_are_ordered_by_name(project, tmp_path, installed):
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir(), second.mkdir()
    installed(FakeEntry("zeta", lambda: second, package="zeta-packs"), FakeEntry("alpha", first, package=None))
    project.profile()
    sources, errors = find_sources(project.root, {}, extra_sources=[tmp_path / "extra"])
    assert errors == []
    assert [(s.label, s.installed) for s in sources] == [
        ("extra", False), (".bondstone/packs", False), ("alpha", True), ("zeta-packs", True)]


def test_a_broken_installed_source_is_a_configuration_error(project, tmp_path, installed):
    installed(FakeEntry("broken", ImportError("no module named acme")),
              FakeEntry("gone", lambda: tmp_path / "missing", package="gone-packs"))
    project.profile()
    assert messages(project) == [
        "installed package 'acme-packs': its pack source 'broken' could not be loaded "
        "(ImportError: no module named acme)",
        f"installed package 'gone-packs': its pack source '{tmp_path / 'missing'}' is not a folder",
    ]


def test_shown_path_is_relative_inside_the_repository_only(tmp_path):
    root = tmp_path / "repo"
    assert shown_path(root, root / "docs" / "a.md") == "docs/a.md"
    assert shown_path(root, tmp_path / "elsewhere" / "pack.yaml") == (tmp_path / "elsewhere" / "pack.yaml").as_posix()
