# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/amos/Documents/GitHub/local-audio-notes/frontend', 'frontend'), ('/Users/amos/Documents/GitHub/local-audio-notes/backend/whisper.cpp/build/bin/whisper-cli', 'whisper.cpp/build/bin')],
    hiddenimports=[],
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
    name='AudioNotes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/amos/Documents/GitHub/local-audio-notes/backend/app_icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AudioNotes',
)
app = BUNDLE(
    coll,
    name='AudioNotes.app',
    icon='/Users/amos/Documents/GitHub/local-audio-notes/backend/app_icon.icns',
    bundle_identifier=None,
)
