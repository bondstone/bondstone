"""Git sources, the lock file and `bondstone update`.

The remote is a git repository in a temporary folder: git itself is told to read
`https://git.test/...` from there, so nothing here touches the network."""

import json
import shutil

import pytest
import yaml
from conftest import ADR_PACK, CAPABILITY_PACK, Project, adr, capability, check

from bondstone import resolve as resolver
from bondstone.cli import main
from bondstone.config import load_config
from bondstone.model import EnvironmentProblem
from bondstone.sources import LOCK_PATH, cache_dir, hash_folder, parse_git_source, read_lock

PACKS = "git.test/acme/packs//packs@v1"
QUIET = {"bondstone/view-stale": "ignore", "bondstone/unbridged-packs": "ignore"}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """No installed packages, a cache of its own, and `https://git.test/` served from a folder."""
    monkeypatch.setattr(resolver, "entry_points", lambda group: [])
    monkeypatch.setenv("BONDSTONE_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", f"url.file://{tmp_path.as_posix()}/remotes/.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://git.test/")


@pytest.fixture
def remote(tmp_path) -> Project:
    """The repository `git.test/acme/packs`, with the adr pack under `packs/`, tagged v1."""
    repo = Project(tmp_path / "remotes" / "acme" / "packs").init()
    repo.pack("adr", ADR_PACK, folder="packs")
    repo.write("README.md", "# Shared packs\n")
    repo.commit("the adr pack")
    repo.git("tag", "v1")
    return repo


@pytest.fixture
def user(tmp_path, remote) -> Project:
    """A repository whose profile takes the adr pack from the remote."""
    project = Project(tmp_path / "user")
    project.profile(packs=["adr@1"], sources=[PACKS], docs=["docs/**/*.md"], overrides=QUIET)
    project.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    return project


def run(capsys, project: Project, *argv: str) -> tuple[int, str, str]:
    code = main(["--root", str(project.root), *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def lock(project: Project) -> dict:
    return yaml.safe_load(project.read(LOCK_PATH))


# --------------------------------------------------------------------------- syntax


@pytest.mark.parametrize("text, expected", [
    ("github.com/acme/bondstone-packs//packs/architecture@v0.3.0",
     ("github.com/acme/bondstone-packs", "packs/architecture", "v0.3.0")),
    ("github.com/acme/packs@main", ("github.com/acme/packs", "", "main")),
    ("git.example.org/team/sub/repo//p@4f2a9c1", ("git.example.org/team/sub/repo", "p", "4f2a9c1")),
    ("github.com/acme/packs//@release/1.x", ("github.com/acme/packs", "", "release/1.x")),
])
def test_a_git_source_names_a_repository_a_folder_and_a_ref(text, expected):
    source = parse_git_source(text)
    assert (source.repo, source.path, source.ref) == expected
    assert source.url == f"https://{expected[0]}" and source.spec == text


@pytest.mark.parametrize("text", [".bondstone/packs", "vendor/packs", "vendor/packs@1", "github.com/acme/packs",
                                  "github.com/acme/packs//../x@v1", "github.com/acme/packs//a b@v1", "github.com@v1",
                                  "github.com/acme/packs@--upload-pack", "github.com/acme/packs@-x"])
def test_anything_else_is_not_a_git_source(text):
    assert parse_git_source(text) is None


def test_an_entry_that_is_neither_a_folder_nor_a_git_source(user):
    user.profile(packs=[], sources=["github.com/acme/packs//x"])
    assert [d.message for d in load_config(user.root).errors] == [
        "sources: 'github.com/acme/packs//x' is neither a folder nor a git source such as "
        "github.com/acme/bondstone-packs//packs@v1.2.0"]


# --------------------------------------------------------------------------- update


def test_update_pins_the_commit_and_a_hash_of_every_component(user, remote, capsys):
    commit = remote.git("rev-parse", "HEAD")
    code, out, _ = run(capsys, user, "update")
    assert code == 0
    assert out == f"{PACKS}: pinned at {commit[:12]} (1 component(s))\nwrote {LOCK_PATH}\n"
    folder = cache_dir() / "trees" / "git.test/acme/packs" / commit / "packs"
    assert lock(user) == {"bondstone": 1, "sources": [{
        "source": PACKS, "commit": commit,
        "components": [{"kind": "pack", "id": "adr", "version": "1.0.0", "sha256": hash_folder(folder / "adr")}]}]}
    assert user.read(LOCK_PATH).startswith("# Written by `bondstone update`; do not edit.")
    assert not (folder.parent / "README.md").exists()  # only the source's folder is kept


def test_check_uses_the_pack_from_the_cache(user, capsys):
    run(capsys, user, "update")
    cfg = load_config(user.root)
    assert cfg.errors == [] and [(c.id, c.manifest) for c in cfg.components] == [("adr", f"{PACKS}:adr/pack.yaml")]
    assert check(user) == []
    user.write("docs/adr/ADR-002-b.md", adr("ADR-002", "proposed", body="## Context\n"))
    assert {d.rule for d in check(user)} == {"bondstone/section-missing"}


def test_check_never_needs_the_remote(user, remote, capsys):
    run(capsys, user, "update")
    shutil.rmtree(remote.root)
    assert run(capsys, user, "check")[0] == 0


def test_update_again_changes_nothing(user, capsys):
    run(capsys, user, "update")
    before = user.read(LOCK_PATH)
    code, out, _ = run(capsys, user, "update")
    assert code == 0 and out.endswith(f"(1 component(s))\n{LOCK_PATH} is up to date\n") and ": still " in out
    assert user.read(LOCK_PATH) == before


def test_a_tag_stays_where_it_is_and_a_branch_moves(user, remote, capsys):
    run(capsys, user, "update")
    first = lock(user)["sources"][0]["commit"]
    remote.pack("adr", ADR_PACK.replace("version: 1.0.0", "version: 1.1.0"), folder="packs")
    second = remote.commit("adr 1.1.0")
    run(capsys, user, "update")
    assert lock(user)["sources"][0]["commit"] == first  # v1 still names the first commit

    branch = "git.test/acme/packs//packs@main"
    user.profile(packs=["adr@1"], sources=[branch], docs=["docs/**/*.md"], overrides=QUIET)
    code, out, _ = run(capsys, user, "update")
    assert f"{branch}: pinned at {second[:12]}" in out and f"{PACKS}: no longer named; removed from the lock" in out
    assert [c.version for c in load_config(user.root).components] == ["1.1.0"]
    remote.pack("adr", ADR_PACK.replace("version: 1.0.0", "version: 1.2.0"), folder="packs")
    third = remote.commit("adr 1.2.0")
    assert [c.version for c in load_config(user.root).components] == ["1.1.0"]  # pinned until the next update
    code, out, _ = run(capsys, user, "update")
    assert f"{branch}: {second[:12]} -> {third[:12]} (1 component(s))\nwrote {LOCK_PATH}\n" == out
    assert [c.version for c in load_config(user.root).components] == ["1.2.0"]


def test_a_source_may_be_one_component(user, remote, capsys):
    single = "git.test/acme/packs//packs/adr@v1"
    user.profile(packs=["adr@1"], sources=[single], docs=["docs/**/*.md"], overrides=QUIET)
    assert run(capsys, user, "update")[0] == 0
    assert [(c["kind"], c["id"]) for c in lock(user)["sources"][0]["components"]] == [("pack", "adr")]
    assert [c.manifest for c in load_config(user.root).components] == [f"{single}:pack.yaml"]


def test_a_local_copy_wins_over_a_git_source(user, capsys):
    run(capsys, user, "update")
    assert [c.version for c in load_config(user.root).components] == ["1.0.0"]
    user.pack("adr", ADR_PACK.replace("version: 1.0.0", "version: 1.5.0"))
    expected = [("1.5.0", ".bondstone/packs/adr/pack.yaml")]
    assert [(c.version, c.manifest) for c in load_config(user.root).components] == expected
    user.profile(packs=["adr@1"], sources=[PACKS, ".bondstone/packs"], docs=["docs/**/*.md"], overrides=QUIET)
    assert [(c.version, c.manifest) for c in load_config(user.root).components] == expected  # whatever the order


def test_the_default_folder_is_searched_next_to_git_sources_only(user, capsys):
    """A profile that names only git sources keeps `.bondstone/packs`."""
    user.pack("capability", CAPABILITY_PACK)
    user.profile(packs=["adr@1", "capability@1"], sources=[PACKS], docs=["docs/**/*.md"], overrides=QUIET)
    run(capsys, user, "update")
    assert sorted(c.id for c in load_config(user.root).components) == ["adr", "capability"]


def test_update_json(user, remote, capsys):
    commit = remote.git("rev-parse", "HEAD")
    code, out, _ = run(capsys, user, "update", "--format", "json")
    assert code == 0 and json.loads(out) == {
        "version": 1, "lock": LOCK_PATH, "changed": True, "removed": [],
        "sources": [{"source": PACKS, "commit": commit, "previous": None, "changed": True,
                     "components": [{"kind": "pack", "id": "adr", "version": "1.0.0"}]}]}


def test_a_profile_without_git_sources(project, capsys):
    project.pack("adr", ADR_PACK).profile(packs=["adr@1"])
    assert run(capsys, project, "update") == (0, "the profile names no git sources\n", "")
    assert not (project.root / LOCK_PATH).exists()
    assert run(capsys, project, "update", "--locked")[:2] == (0, "the profile names no git sources\n")


def test_a_source_that_is_no_longer_named_leaves_the_lock(user, capsys):
    run(capsys, user, "update")
    user.pack("adr", ADR_PACK).profile(packs=["adr@1"], docs=["docs/**/*.md"], overrides=QUIET)
    code, out, _ = run(capsys, user, "update")
    assert out == f"{PACKS}: no longer named; removed from the lock\nwrote {LOCK_PATH}\n"
    assert not (user.root / LOCK_PATH).exists()


def test_a_ref_or_a_folder_that_does_not_exist_stops_update(user, capsys):
    user.profile(packs=["adr@1"], sources=["git.test/acme/packs//packs@v9"])
    code, out, err = run(capsys, user, "update")
    assert (code, out) == (3, "") and "cannot fetch 'v9' from https://git.test/acme/packs" in err
    user.profile(packs=["adr@1"], sources=["git.test/acme/packs//nope@v1"])
    code, _, err = run(capsys, user, "update")
    assert code == 3 and "has no folder 'nope'" in err
    user.profile(packs=["adr@1"], sources=["git.test/acme/missing//packs@v1"])
    assert run(capsys, user, "update")[0] == 3
    assert not (user.root / LOCK_PATH).exists()


def test_a_folder_without_components_is_refused(user, remote, capsys):
    remote.write("empty/notes.txt", "nothing\n")
    remote.commit("a folder without packs")
    user.profile(packs=["adr@1"], sources=["git.test/acme/packs//empty@main"])
    code, _, err = run(capsys, user, "update")
    assert code == 1 and "has no pack, bridge or preset in 'empty'" in err


# --------------------------------------------------------------------------- what check asks for


def test_a_source_that_the_lock_does_not_pin_is_a_configuration_error(user, capsys):
    code, out, err = run(capsys, user, "check")
    assert code == 2 and "the configuration is invalid" in err
    assert (f".bondstone/profile.yaml: error bondstone/profile: sources: git source '{PACKS}' is not in "
            f"{LOCK_PATH}; run `bondstone update` and commit the lock\n") in out
    assert "not found" not in out  # the pack it would hold is not reported as missing


def test_a_cache_that_is_behind_is_an_environment_error(user, capsys, tmp_path):
    run(capsys, user, "update")
    shutil.rmtree(tmp_path / "cache")
    code, out, err = run(capsys, user, "check")
    assert (code, out) == (3, "")
    assert f"{PACKS}: commit " in err and "is not in the cache" in err and "run `bondstone update --locked`" in err
    with pytest.raises(EnvironmentProblem):
        load_config(user.root)


def test_update_locked_fetches_what_the_lock_pins_and_changes_nothing(user, remote, capsys, tmp_path):
    run(capsys, user, "update")
    before = user.read(LOCK_PATH)
    commit = lock(user)["sources"][0]["commit"]
    remote.pack("adr", ADR_PACK.replace("version: 1.0.0", "version: 1.1.0"), folder="packs")
    remote.commit("newer, and not asked for")
    remote.git("tag", "--force", "v1")  # even a moved tag does not move the lock
    shutil.rmtree(tmp_path / "cache")
    code, out, _ = run(capsys, user, "update", "--locked")
    assert (code, out) == (0, f"{PACKS}: {commit[:12]} is in the cache (1 component(s))\n")
    assert user.read(LOCK_PATH) == before
    assert [c.version for c in load_config(user.root).components] == ["1.0.0"]
    assert run(capsys, user, "check")[0] == 0


def test_cached_files_that_changed_are_noticed_and_repaired(user, capsys):
    run(capsys, user, "update")
    commit = lock(user)["sources"][0]["commit"]
    pack = cache_dir() / "trees" / "git.test/acme/packs" / commit / "packs" / "adr" / "pack.yaml"
    pack.write_text(pack.read_text(encoding="utf-8").replace("severity: warn", "severity: ignore"), encoding="utf-8")
    code, _, err = run(capsys, user, "check")
    assert code == 3 and "do not match the lock (pack adr)" in err
    (pack.parent / "extra.txt").write_text("left over\n", encoding="utf-8")
    assert run(capsys, user, "update", "--locked")[0] == 0
    assert run(capsys, user, "check")[0] == 0 and not (pack.parent / "extra.txt").exists()


def test_update_locked_refuses_a_lock_that_does_not_cover_the_profile(user, capsys):
    code, _, err = run(capsys, user, "update", "--locked")
    assert code == 1 and f"{LOCK_PATH} does not pin '{PACKS}'; run `bondstone update`" in err
    assert not (user.root / LOCK_PATH).exists()
    code, _, err = run(capsys, user, "update", "--locked", "adr")
    assert code == 1 and "takes no names" in err


def test_update_locked_refuses_a_hash_that_the_commit_does_not_have(user, capsys):
    run(capsys, user, "update")
    digest = lock(user)["sources"][0]["components"][0]["sha256"]
    user.edit(LOCK_PATH, digest, "f" * 64)
    code, _, err = run(capsys, user, "update", "--locked")
    assert code == 1 and "do not match the lock (pack adr); the lock was edited or is damaged" in err


@pytest.mark.parametrize("text, message", [
    ("bondstone: 1\nsources: [{source: x}]\n", "missing required keys 'commit', 'components'"),
    ("bondstone: 2\nsources: []\n", "expected the format version 1"),
    ("sources: [\n", "invalid YAML"),
])
def test_a_malformed_lock_is_a_configuration_error(user, capsys, text, message):
    user.write(LOCK_PATH, text)
    errors = load_config(user.root).errors
    assert errors[0].path == LOCK_PATH and message in errors[0].message
    assert run(capsys, user, "check")[0] == 2
    assert run(capsys, user, "update")[0] == 1


# --------------------------------------------------------------------------- several sources and presets


@pytest.fixture
def org(tmp_path, remote) -> Project:
    """`git.test/acme/org`: a preset that takes the adr pack from `git.test/acme/packs`."""
    repo = Project(tmp_path / "remotes" / "acme" / "org").init()
    repo.write("presets/team/preset.yaml", f"""
        id: team
        version: 1.0.0
        sources: [{PACKS}]
        packs: [adr@1]
        overrides:
          adr/alternatives-considered: error
    """)
    repo.commit("the team preset")
    repo.git("tag", "v1")
    return repo


def test_a_preset_from_a_git_source_may_name_another(tmp_path, org, capsys):
    presets = "git.test/acme/org//presets@v1"
    user = Project(tmp_path / "user")
    user.profile(extends=["team@1"], sources=[presets], docs=["docs/**/*.md"], overrides=QUIET)
    user.write("docs/adr/ADR-001-a.md", adr("ADR-001", "proposed"))
    code, out, _ = run(capsys, user, "check")
    assert code == 2 and "team" not in out.replace(presets, "")  # only the unpinned source is reported
    code, out, _ = run(capsys, user, "update")
    assert code == 0 and [line.split(":")[0] for line in out.splitlines()[:2]] == [presets, PACKS]
    assert [entry["source"] for entry in lock(user)["sources"]] == [presets, PACKS]  # sorted by source
    cfg = load_config(user.root)
    assert cfg.errors == []
    assert [(c.kind, c.id) for c in cfg.components] == [("pack", "adr"), ("preset", "team")]
    assert cfg.severity("adr/alternatives-considered", "warn") == "error"
    assert run(capsys, user, "check")[0] == 0


def test_a_preset_cannot_name_a_local_folder(project):
    project.write(".bondstone/packs/team/preset.yaml", "id: team\nversion: 1.0.0\nsources: [.bondstone/more]\n")
    project.profile(extends=["team@1"])
    assert ["expected a git source such as" in d.message for d in load_config(project.root).errors] == [True]


def test_update_with_a_name_only_moves_the_source_that_holds_it(tmp_path, remote, capsys):
    other = Project(tmp_path / "remotes" / "acme" / "more").init()
    other.pack("capability", CAPABILITY_PACK, folder="packs")
    other.commit("the capability pack")
    more, packs = "git.test/acme/more//packs@main", "git.test/acme/packs//packs@main"
    user = Project(tmp_path / "user")
    user.profile(packs=["adr@1", "capability@1"], sources=[packs, more], docs=["docs/**/*.md"], overrides=QUIET)
    user.write("docs/capabilities/a.md", capability())
    run(capsys, user, "update")
    pinned = {entry["source"]: entry["commit"] for entry in lock(user)["sources"]}
    remote.write("packs/adr/notes.md", "more\n")
    moved = remote.commit("adr changes")
    other.write("packs/capability/notes.md", "more\n")
    other.commit("capability changes")
    code, out, _ = run(capsys, user, "update", "adr")
    assert code == 0 and f"{more}: still {pinned[more][:12]}" in out
    assert {entry["source"]: entry["commit"] for entry in lock(user)["sources"]} == {packs: moved, more: pinned[more]}
    code, _, err = run(capsys, user, "update", "nope")
    assert code == 1 and "no git source in .bondstone/bondstone.lock holds nope" in err


def test_a_broken_manifest_in_a_git_source_is_named_by_its_source(user, remote, capsys):
    remote.pack("adr", ADR_PACK.replace("types:", "typs:"), folder="packs")
    remote.commit("a typo")
    user.profile(packs=["adr@1"], sources=["git.test/acme/packs//packs@main"])
    run(capsys, user, "update")
    errors = load_config(user.root).errors
    assert errors[0].path == "git.test/acme/packs//packs@main:adr/pack.yaml" and "typs" in errors[0].message


def test_packs_lists_what_a_git_source_holds(user, capsys):
    run(capsys, user, "update")
    code, out, _ = run(capsys, user, "packs", "--format", "json")
    listed = json.loads(out)["components"]
    assert code == 0 and [(c["id"], c["source"], c["in_use"]) for c in listed] == [("adr", PACKS, True)]
