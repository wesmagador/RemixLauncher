# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['qt_launcher.py'],
    pathex=['vendor'],
    binaries=[],
    datas=[('launcher.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
from pathlib import Path
# Qt 6.12 requer o runtime MSVC distribuído com ele, mais novo que o do Python.
qt_runtime = Path(SPECPATH) / 'vendor' / 'PySide6'
a.binaries = [(dest, str(qt_runtime / Path(src).name) if Path(src).name.lower().startswith(('vcruntime140', 'msvcp140')) and (qt_runtime / Path(src).name).exists() else src, kind) for dest, src, kind in a.binaries]
# Não incluir o ICU do Poppler presente no PATH da máquina de build.
a.binaries = [(dest, r'C:\Windows\System32\icuuc.dll' if Path(dest).name.lower() == 'icuuc.dll' else src, kind) for dest, src, kind in a.binaries]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RemixLauncher-1.2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['launcher.ico'],
)
