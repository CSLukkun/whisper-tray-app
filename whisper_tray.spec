# -*- mode: python ; coding: utf-8 -*-
# WhisperTray — PyInstaller one-folder spec (Windows)
#
# Preferred mode: one-folder (COLLECT). faster-whisper / ctranslate2 / onnxruntime
# ship many native DLLs; a folder build starts faster and is easier to debug than
# one-file (which unpacks to a temp dir on every launch).
#
# Usage (Windows):
#   build_windows.bat
#   # or:
#   pip install pyinstaller
#   pyinstaller whisper_tray.spec
#
# Output: dist/WhisperTray/WhisperTray.exe  (+ DLLs beside it)
#
# Known hooks / collection notes:
# - collect_all('faster_whisper') picks up silero_vad *.onnx under assets/
# - collect_all('ctranslate2') / onnxruntime / av / tokenizers bring native libs
# - sounddevice needs its PortAudio binary (_sounddevice_data on Windows wheels)
# - pystray needs pystray._win32 on Windows
# - Hugging Face model weights are NOT bundled; first run still downloads to cache
# - If Analysis misses a DLL, add it via binaries= or collect_dynamic_libs()
# - UPX is disabled: native ML DLLs often break when compressed

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    # App / UI
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'pystray',
    'pystray._win32',
    'pyperclip',
    'plyer',
    'plyer.platforms.win.notification',
    # Audio
    'sounddevice',
    '_sounddevice',
    'numpy',
    # Whisper stack
    'faster_whisper',
    'ctranslate2',
    'onnxruntime',
    'av',
    'tokenizers',
    'huggingface_hub',
    'httpx',
    'tqdm',
]

# Collect package data + binaries for native-heavy deps.
# Each collect_all returns (datas, binaries, hiddenimports).
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
        # Package may be absent on the build machine; Analysis still runs.
        pass

# Extra dynamic libs some wheels put next to the package / in *.libs
for pkg in ('ctranslate2', 'onnxruntime', 'av', 'sounddevice'):
    try:
        binaries += collect_dynamic_libs(pkg)
    except Exception:
        pass

# sounddevice / PortAudio data files (Windows wheel often ships _sounddevice_data)
try:
    from PyInstaller.utils.hooks import collect_data_files
    datas += collect_data_files('sounddevice')
    datas += collect_data_files('_sounddevice_data')
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
        # Keep the frozen tree lean; unused GUI / notebook stacks
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
    exclude_binaries=True,  # one-folder: binaries go into COLLECT
    name='WhisperTray',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed tray app; logs go to %LOCALAPPDATA%\WhisperTray\logs\
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # optional: set to a .ico path
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
