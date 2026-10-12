# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH).resolve().parent
SOURCE = ROOT / "outputs" / "VideoGrab"
WORK = ROOT / "work"

datas = [
    (str(SOURCE / "assets"), "assets"),
    (str(SOURCE / "mobile" / "web"), "mobile/web"),
    (str(SOURCE / "README.txt"), "."),
    (str(SOURCE / "THIRD_PARTY_NOTICES.txt"), "."),
]
binaries = [
    (str(SOURCE / "vendor" / "ffmpeg.exe"), "vendor"),
    (str(SOURCE / "vendor" / "node.exe"), "vendor"),
    (str(SOURCE / "vendor" / "cloudflared.exe"), "vendor"),
]
hiddenimports = []

for package in ("yt_dlp", "yt_dlp_ejs", "qrcode"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    [str(SOURCE / "app.py")],
    pathex=[str(SOURCE)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VideoGrab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(SOURCE / "assets" / "videograb.ico"),
    version=str(WORK / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VideoGrab",
)
