"""Live tests talk to real IRC networks (HOME and EFnet). They are OPT-IN: set VOXTERRAE_LIVE_TESTS=1 to run them.
Without it every test marked `live` is skipped, so `pytest` on a fresh clone never opens a network connection."""
import os
import pytest

def pytest_collection_modifyitems(config, items):
    if os.environ.get("VOXTERRAE_LIVE_TESTS") == "1": return
    skip = pytest.mark.skip(reason="live network test; set VOXTERRAE_LIVE_TESTS=1 to run")
    for it in items:
        if "live" in it.keywords: it.add_marker(skip)
