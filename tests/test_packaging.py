"""The built wheel ships the library and the engine rule catalog, but no test fixtures."""

import subprocess
import sys
import zipfile

import pytest

from .conftest import REPO


@pytest.fixture(scope="module")
def wheel_files(tmp_path_factory):
    out = tmp_path_factory.mktemp("wheel")
    result = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(out), str(REPO)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"cannot build the wheel here: {result.stderr.strip()[-200:]}")
    [wheel] = out.glob("bondstone-*.whl")
    return zipfile.ZipFile(wheel).namelist()


def test_wheel_contains_library_and_catalog(wheel_files):
    library = REPO / "src" / "bondstone" / "library"
    expected = {f"bondstone/{p.relative_to(REPO / 'src' / 'bondstone').as_posix()}"
                for p in library.rglob("*") if p.is_file() and "fixtures" not in p.parts}
    assert expected - set(wheel_files) == set()
    assert "bondstone/engine_rules.md" in wheel_files


def test_wheel_has_no_fixtures(wheel_files):
    assert [f for f in wheel_files if "/fixtures/" in f] == []
