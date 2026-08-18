# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


root = Path(SPECPATH)
bootstack_datas, bootstack_binaries, bootstack_hiddenimports = collect_all("bootstack")

a = Analysis(
    [str(root / "main_bootstack_about.py")],
    pathex=[str(root)],
    binaries=bootstack_binaries,
    datas=bootstack_datas
    + [
        (str(root / "versionado" / "version.txt"), "versionado"),
        (str(root / "ASSETS" / "Ico_VeriPre.ico"), "ASSETS"),
    ],
    hiddenimports=bootstack_hiddenimports,
    hookspath=[str(root / "build_hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pypyodbc", "vlc"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SmartPrice-Bootstack-About",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(root / "ASSETS" / "Ico_VeriPre.ico")],
)
