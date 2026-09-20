"""Regression for the v0.1.0 exe crash: PyInstaller runs the entry file as a top-level script, so a
relative import anywhere in the entry module raises "attempted relative import with no known parent
package" the moment the exe starts. Two checks: a static one that always runs, and a real launch of
both entry files as plain scripts (skipped where PySide6 is not installed)."""
import os, re, subprocess, sys, pathlib, pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRY = ROOT / "src" / "voxterrae" / "app" / "__main__.py"
LAUNCHER = ROOT / "build" / "launcher.py"

def test_entry_files_have_no_relative_imports():
    for p in (ENTRY, LAUNCHER):
        bad = [l for l in p.read_text(encoding="utf-8").splitlines() if re.match(r"\s*from\s+\.", l)]
        assert not bad, f"{p.name}: relative import(s) would crash the frozen exe: {bad}"

def test_spec_freezes_the_launcher_not_the_package_main():
    spec = (ROOT / "build" / "voxterrae.spec").read_text(encoding="utf-8")
    assert '"launcher.py"' in spec and '"__main__.py"' not in spec

@pytest.mark.parametrize("entry", [ENTRY, LAUNCHER])
def test_entry_runs_as_a_plain_script(entry, tmp_path):
    pytest.importorskip("PySide6")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), QT_QPA_PLATFORM="offscreen", VOXTERRAE_NO_UPDATE_CHECK="1")
    out = tmp_path / "shot.png"
    r = subprocess.run([sys.executable, str(entry), "--demo", "--shot", str(out), "480x270", "--after", "0.5"],
                       env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    assert out.exists() and out.stat().st_size > 1000
