# PyInstaller spec for the VoxTerrae portable exe (Windows 11). Build with build/build_win.ps1.
# -*- mode: python ; coding: utf-8 -*-
import os
block_cipher = None
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],   # NOT the package __main__.py: run as a script it has no parent package
    pathex=[os.path.join(ROOT, "src")],
    binaries=[],
    datas=[],
    hiddenimports=["qasync", "voxterrae", "voxterrae.app", "voxterrae.app.__main__", "voxterrae.app.main_window", "voxterrae.app.bridge", "voxterrae.app.demo", "voxterrae.app.updates", "voxterrae.app.platform", "voxterrae.app.prefs", "voxterrae.app.composer", "voxterrae.app.roomlist", "voxterrae.app.members", "PySide6.QtNetwork", "voxterrae.irc.session", "voxterrae.irc.networks", "voxterrae.store"],
    hookspath=[], runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtCharts", "PySide6.QtPdf", "tkinter"],
    cipher=block_cipher, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="VoxTerrae",
    icon=os.path.join(SPECPATH, "voxterrae.ico") if os.path.exists(os.path.join(SPECPATH, "voxterrae.ico")) else None,
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False,                 # GUI app: no console window
    onefile=True,                  # portable: one exe, unpacks to %TEMP% at launch
    disable_windowed_traceback=False, target_arch=None,
)
