"""Live tests talk to real IRC networks (HOME and EFnet). They are OPT-IN: set VOXTERRAE_LIVE_TESTS=1 to run them.
Without it every test marked `live` is skipped, so `pytest` on a fresh clone never opens a network connection."""
import os
import pytest

def pytest_collection_modifyitems(config, items):
    if os.environ.get("VOXTERRAE_LIVE_TESTS") == "1": return
    skip = pytest.mark.skip(reason="live network test; set VOXTERRAE_LIVE_TESTS=1 to run")
    for it in items:
        if "live" in it.keywords: it.add_marker(skip)

@pytest.fixture(autouse=True, scope="session")
def _isolated_qsettings(tmp_path_factory):
    """Tests must never write the developer's real VoxTerrae settings (the window saves prefs on construction)."""
    from PySide6.QtCore import QSettings
    d = str(tmp_path_factory.mktemp("qsettings"))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    for fmt in (QSettings.IniFormat, QSettings.NativeFormat): QSettings.setPath(fmt, QSettings.UserScope, d)
    os.environ["LOCALAPPDATA"] = d   # profile dir (db, logs) too
    yield
