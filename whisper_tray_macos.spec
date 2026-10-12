# -*- mode: python ; coding: utf-8 -*-
# WhisperTray — PyInstaller macOS .app / one-folder spec
#
# MUST be built on macOS (Apple Silicon or Intel). Linux cannot produce a
# working Cocoa/.app bundle. See build_macos.sh.
#
# Usage (on a Mac):
#   ./build_macos.sh
#   # or:
#   pip install pyinstaller
#   pyinstaller whisper_tray_macos.spec
#
# Output: dist/WhisperTray.app  (unsigned; Gatekeeper may require right-click Open)
#
# Notes:
# - pystray uses the Darwin backend (NSStatusItem)
# - sounddevice needs PortAudio (brew install portaudio) at build AND runtime
#   unless the dylib is collected; collect_dynamic_libs helps but users may
#   still need portaudio installed for mic access edge cases
# - Model weights are NOT bundled
# - No codesign / notarization here

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, collect_data_files

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'pystray',
    'pystray._darwin',
    'pyperclip',
    'plyer',
    'plyer.platforms.macosx.notification',
    'sounddevice',
    '_sounddevice',
    'numpy',
    'faster_whisper',
    'ctranslate2',
    'onnxruntime',
    'av',
    'tokenizers',
    'huggingface_hub',
    'httpx',
    'tqdm',
]

for pkg in (
    'faster_whisper',
    'ctranslate2',
    'onnxruntime',
    'tokenizers',
    'av',
):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

for pkg in ('ctranslate2', 'onnxruntime', 'av', 'sounddevice'):
    try:
        binaries += collect_dynamic_libs(pkg)
    except Exception:
        pass

try:
    datas += collect_data_files('sounddevice')
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'notebook',
        'pytest',
    ],
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
    name='WhisperTray',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # macOS: nicer .app argv handling
    target_arch=None,     # native arch of the build Mac
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='WhisperTray',
)

app = BUNDLE(
    coll,
    name='WhisperTray.app',
    icon=None,
    bundle_identifier='com.whispertray.app',
    info_plist={
        'CFBundleName': 'WhisperTray',
        'CFBundleDisplayName': 'WhisperTray',
        'CFBundleShortVersionString': '0.1.1',
        'CFBundleVersion': '0.1.1',
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': (
            'WhisperTray needs the microphone to record speech for local Whisper transcription.'
        ),
        'LSUIElement': True,  # menu-bar agent; no Dock icon
    },
)
