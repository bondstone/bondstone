"""`bondstone packs`, `bondstone pack test` and `bondstone init`."""

import json

import pytest
from conftest import ADR_PACK, LIBRARY_PACKS, Project, standard

from bondstone import resolve as resolver
from bondstone.cli import main
from bondstone.config import load_config
from bondstone.packs import available, to_text


def run(capsys, *argv):
    code = main([str(arg) for arg in argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def no_installed_packages(monkeypatch):
    monkeypatch.setattr(resolver, "entry_points", lambda group: [])


# ----------------------------------------------------------------------- packs


def test_available_lists_local_and_installed_components_and_marks_the_ones_in_use(project):
    standard(project, packs=["adr@1"], bridges=[])
    cfg = load_config(project.root)
    found = [a for a in available(project.root, cfg.profile, cfg.components)
             if a.id in ("adr", "capability", "adr-capability", "starter")]
    assert [(a.kind, a.id, a.source, a.in_use) for a in found] == [
        ("pack", "adr", ".bondstone/packs", True),
        ("pack", "adr", "bondstone-library", False),
        ("pack", "capability", ".bondstone/packs", False),
        ("pack", "capability", "bondstone-library", False),
        ("bridge", "adr-capability", ".bondstone/packs", False),
        ("bridge", "adr-capability", "bondstone-library", False),
        ("preset", "starter", "bondstone-library", False),
    ]
    assert found[0].path == ".bondstone/packs/adr" and found[0].version == "1.0.0"
    assert found[1].path == (LIBRARY_PACKS / "adr").as_posix()
    assert found[1].description.startswith("Architecture Decision Records")


def test_packs_text_output(project, capsys, no_installed_packages):
    standard(project, packs=["adr@1"], bridges=[])
    project.pack("broken", "id: [x\n")
    code, out, _ = run(capsys, "--root", project.root, "packs")
    assert code == 0
    assert out.splitlines() == [
        "in use  pack    adr@1.0.0             .bondstone/packs",
        "        pack    broken@?              .bondstone/packs",
        "        pack    capability@1.0.0      .bondstone/packs",
        "        bridge  adr-capability@1.0.0  .bondstone/packs",
    ]


def test_packs_json_output(project, capsys):
    project.profile(packs=["adr@1"])
    code, out, _ = run(capsys, "--root", project.root, "packs", "--format", "json")
    payload = json.loads(out)
    assert code == 0 and payload["version"] == 1
    assert payload["components"][0] == {
        "kind": "pack", "id": "adr", "version": "1.0.0", "source": "bondstone-library",
        "path": (LIBRARY_PACKS / "adr").as_posix(),
        "description": "Architecture Decision Records with a lifecycle, supersession and immutability.",
        "in_use": True,
    }
    listed = [(c["kind"], c["id"]) for c in payload["components"]]
    assert listed[:2] == [("pack", "adr"), ("pack", "capability")]
    assert ("bridge", "adr-capability") in listed and listed.index(("preset", "starter")) > listed.index(
        ("bridge", "adr-capability"))  # packs, then bridges, then presets


def test_packs_without_a_profile_lists_what_a_new_profile_could_use(tmp_path, capsys, monkeypatch):
    Project(tmp_path).pack("mine", "id: mine\nversion: 0.2.0\ndescription: >-\n  My own\n  pack.\n")
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsys, "packs")
    assert code == 0
    assert ["pack", "mine@0.2.0", ".bondstone/packs", "My", "own", "pack."] in [line.split() for line in out.splitlines()]
    assert "in use" not in out and "bondstone-library" in out


def test_packs_with_nothing_to_list(tmp_path, capsys, no_installed_packages):
    code, out, _ = run(capsys, "--root", tmp_path, "packs")
    assert (code, out) == (0, "no packs, bridges or presets found\n")
    assert to_text([]) == "no packs, bridges or presets found\n"


def test_packs_with_an_unreadable_profile_is_a_configuration_error(project, capsys):
    project.write(".bondstone/profile.yaml", "bondstone: 7\n")
    code, out, _ = run(capsys, "--root", project.root, "packs")
    assert code == 2 and "expected the format version 1" in out


def test_packs_still_lists_when_the_profile_names_a_missing_pack(project, capsys, no_installed_packages):
    standard(project, packs=["adr@1", "nope@1"], bridges=[])
    code, out, _ = run(capsys, "--root", project.root, "packs")
    assert code == 0 and out.startswith("in use  pack    adr@1.0.0")


def test_packs_lists_presets_after_bridges_and_marks_the_ones_extended(project, capsys, no_installed_packages):
    standard(project, packs=[], bridges=[], extends=["base@1"])
    project.write(".bondstone/packs/base/preset.yaml",
                  "id: base\nversion: 1.1.0\ndescription: The team's base.\npacks: [adr@1]\n")
    project.write(".bondstone/packs/other/preset.yaml", "id: other\nversion: 0.1.0\n")
    code, out, _ = run(capsys, "--root", project.root, "packs")
    assert code == 0
    assert out.splitlines() == [
        "in use  pack    adr@1.0.0             .bondstone/packs",
        "        pack    capability@1.0.0      .bondstone/packs",
        "        bridge  adr-capability@1.0.0  .bondstone/packs",
        "in use  preset  base@1.1.0            .bondstone/packs  The team's base.",
        "        preset  other@0.1.0           .bondstone/packs",
    ]


# ----------------------------------------------------------------------- pack test


@pytest.fixture
def pack_with_fixtures(tmp_path) -> Project:
    packs = Project(tmp_path / "packs").pack("adr", ADR_PACK, folder=".")
    packs.write("adr/fixtures/valid/.bondstone/profile.yaml",
                "bondstone: 1\npacks: [adr@1]\noverrides: {bondstone/view-stale: ignore}\n")
    packs.write("adr/fixtures/valid/expected.yaml", "errors: []\n")
    return packs


def test_pack_test_passes(pack_with_fixtures, capsys):
    code, out, _ = run(capsys, "pack", "test", pack_with_fixtures.root / "adr")
    assert (code, out) == (0, "ok   adr/valid\n✓ 1 fixture(s) passed\n")


def test_pack_test_fails_with_exit_code_1(pack_with_fixtures, capsys):
    pack_with_fixtures.write("adr/fixtures/valid/expected.yaml", "errors: [adr/some-rule]\n")
    pack_with_fixtures.pack("bare", "id: bare\nversion: 1.0.0\n", folder=".")
    root = pack_with_fixtures.root
    code, out, _ = run(capsys, "pack", "test", root / "adr", root / "bare", "--format", "json")
    payload = json.loads(out)
    assert code == 1 and payload["version"] == 1 and payload["summary"] == {"passed": 0, "failed": 2}
    assert [(f["component"], f["case"], f["passed"]) for f in payload["fixtures"]] == [
        ("adr", "valid", False), ("bare", None, False)]
    assert payload["fixtures"][0]["problems"] == ["expected error adr/some-rule was not reported"]

    code, out, _ = run(capsys, "pack", "test", root / "bare")
    assert code == 1 and out.startswith(f"FAIL bare ({(root / 'bare').as_posix()})\n     no fixtures:")


def test_pack_test_on_something_else_is_an_environment_error(tmp_path, capsys):
    code, out, err = run(capsys, "pack", "test", tmp_path)
    assert code == 3 and out == "" and "is not a pack, a bridge or a preset" in err


def test_pack_test_runs_the_fixtures_of_the_library(capsys):
    code, out, _ = run(capsys, "pack", "test", *sorted(p for p in LIBRARY_PACKS.iterdir() if p.is_dir()))
    assert code == 0 and "FAIL" not in out and out.endswith(f"✓ {len(out.splitlines()) - 1} fixture(s) passed\n")
    assert len(out.splitlines()) > 20


def test_pack_test_runs_the_fixtures_of_a_preset(tmp_path, capsys):
    packs = Project(tmp_path / "packs").pack("adr", ADR_PACK, folder=".")
    packs.write("base/preset.yaml", "id: base\nversion: 1.0.0\npacks: [adr@1]\n"
                                    "overrides: {bondstone/view-stale: ignore}\n")
    packs.write("base/fixtures/valid/.bondstone/profile.yaml", "bondstone: 1\nextends: [base@1]\n")
    packs.write("base/fixtures/valid/expected.yaml", "errors: []\n")
    code, out, _ = run(capsys, "pack", "test", packs.root / "base", "--format", "json")
    payload = json.loads(out)
    assert code == 0 and [(f["component"], f["kind"], f["passed"]) for f in payload["fixtures"]] == [
        ("base", "preset", True)]


# ----------------------------------------------------------------------- init


def test_init_creates_a_valid_empty_profile(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsys, "init")
    assert code == 0 and out.splitlines()[0] == "created .bondstone/profile.yaml"
    cfg = load_config(tmp_path)
    assert cfg.problems == [] and cfg.components == []
    assert run(capsys, "check")[:2] == (0, "✓ 0 error(s), 0 warning(s), 0 nodes\n")


def test_init_takes_a_root_and_refuses_to_overwrite(tmp_path, capsys):
    target = tmp_path / "repo"
    target.mkdir()
    assert run(capsys, "--root", target, "init")[0] == 0
    (target / ".bondstone/profile.yaml").write_text("bondstone: 1\npacks: [adr@1]\n", encoding="utf-8")
    code, out, err = run(capsys, "init", "--root", target)
    assert code == 1 and out == "" and ".bondstone/profile.yaml already exists" in err
    assert (target / ".bondstone/profile.yaml").read_text(encoding="utf-8") == "bondstone: 1\npacks: [adr@1]\n"
    code, _, err = run(capsys, "--root", tmp_path / "missing", "init")
    assert code == 3 and "is not a directory" in err


def test_init_does_not_look_for_a_profile_in_parent_folders(project, tmp_path, capsys, monkeypatch):
    project.profile()
    nested = tmp_path / "service"
    nested.mkdir()
    monkeypatch.chdir(nested)
    assert run(capsys, "init")[0] == 0
    assert (nested / ".bondstone/profile.yaml").is_file()


def test_init_from_a_preset_of_the_library(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsys, "init", "--preset", "starter")
    assert code == 0 and out.splitlines() == [
        "created .bondstone/profile.yaml",
        "next: list this repository's source files under `code.include`, then run `bondstone agent`"]
    text = (tmp_path / ".bondstone/profile.yaml").read_text(encoding="utf-8")
    assert "extends: [starter@1]\ncode:\n  include: []" in text
    cfg = load_config(tmp_path)
    assert cfg.problems == []
    assert [(c.kind, c.id) for c in cfg.components] == [
        ("pack", "adr"), ("pack", "capability"), ("bridge", "adr-capability"), ("preset", "starter")]
    assert run(capsys, "profile", "check")[0] == 0


def test_init_uses_the_major_version_that_is_available_or_the_range_given(project, tmp_path, capsys,
                                                                         no_installed_packages):
    project.write(".bondstone/packs/base/preset.yaml", "id: base\nversion: 2.3.1\n")
    assert run(capsys, "--root", tmp_path, "init", "--preset", "base")[0] == 0
    assert "extends: [base@2]\n" in project.read(".bondstone/profile.yaml")
    (tmp_path / ".bondstone/profile.yaml").unlink()
    assert run(capsys, "--root", tmp_path, "init", "--preset", "base@>=2.3")[0] == 0
    assert "extends: [base@>=2.3]\n" in project.read(".bondstone/profile.yaml")


def test_init_refuses_a_preset_that_is_not_available(project, tmp_path, capsys, no_installed_packages):
    code, out, err = run(capsys, "--root", tmp_path, "init", "--preset", "starter")
    assert code == 1 and out == "" and "preset 'starter' not found (no presets are available here)" in err
    assert not (tmp_path / ".bondstone/profile.yaml").exists()
    project.write(".bondstone/packs/base/preset.yaml", "id: base\nversion: 1.0.0\n")
    project.pack("adr", ADR_PACK)
    code, _, err = run(capsys, "--root", tmp_path, "init", "--preset", "adr")
    assert code == 1 and "preset 'adr' not found (available: base)" in err
