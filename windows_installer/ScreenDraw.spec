# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ScreenDraw Windows.
Bundles the app into a single-folder distribution.

Usage (from the ScreenDraw root directory):
    pyinstaller windows_installer/ScreenDraw.spec
"""

import os
import sys

block_cipher = None

# Path to the main script
script_path = os.path.join('..', 'screendraw_windows.py')

# Icon path (generate first with generate_icon.py)
icon_path = os.path.join(os.path.dirname(SPECPATH), 'windows_installer', 'screendraw.ico')
if not os.path.exists(icon_path):
    icon_path = None

a = Analysis(
    [os.path.join(SPECPATH, '..', 'screendraw_windows.py')],
    pathex=[os.path.join(SPECPATH, '..')],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'keyboard',
        'keyboard._winkeyboard',
        'pyautogui',
        'cv2',
        'numpy',
        'win32clipboard',
        'win32con',
        'pywintypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        'gtk',
        'test',
        'unittest',
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
    name='ScreenDraw',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    uac_admin=True,  # Request admin for global hotkeys
    version=os.path.join(SPECPATH, 'file_version_info.txt') if os.path.exists(os.path.join(SPECPATH, 'file_version_info.txt')) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScreenDraw',
)
