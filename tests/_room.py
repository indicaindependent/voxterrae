"""Throwaway HOME room for live tests: a fresh name per run, so nothing fixed ever appears in the
suite, the renders, or the server. Override with VT_TEST_CHAN if you run against your own network."""
import os, secrets

def throwaway_room() -> str:
    return os.environ.get("VT_TEST_CHAN") or ("#vt-" + secrets.token_hex(4))
