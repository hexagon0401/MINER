# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('ui.html', '.')],
    hiddenimports=[
        "httpx", "httpcore", "h2", "hpack", "certifi",
        "rumps", "objc", "AppKit", "Foundation",
        "asyncio", "asyncio.selector_events",
        "asyncio.unix_events"
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SchoolNetOptimizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements.plist',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SchoolNetOptimizer',
)

app = BUNDLE(
    coll,
    name='SchoolNetOptimizer.app',
    icon=None,
    bundle_identifier='com.schoolnet.optimizer.v5',
    info_plist={
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '3.5.0',
    },
)
