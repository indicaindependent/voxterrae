"""Frozen entry point for the portable exe. PyInstaller runs the entry file as a plain script, so it must
not live inside the package and must not use relative imports; it just hands off to voxterrae.app."""
import sys
from voxterrae.app.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
