"""
Setup script to build ScreenDraw (Python version) as a macOS .app bundle.

Usage:
    pip3 install py2app pyobjc-framework-Cocoa pyobjc-framework-Quartz
    python3 setup.py py2app

This bundles Python + all dependencies into a standalone .app.
For the native Swift version (recommended), use build.sh instead.
"""

import os
from setuptools import setup

VERSION = open("VERSION").read().strip() if os.path.exists("VERSION") else "1.0.0"

# Use generated .icns if available
ICNS_PATH = os.path.join("ScreenDraw", "AppIcon.icns")
if not os.path.exists(ICNS_PATH):
    ICNS_PATH = None

APP = ['screendraw.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': ICNS_PATH,
    'plist': {
        'CFBundleName': 'ScreenDraw',
        'CFBundleDisplayName': 'ScreenDraw',
        'CFBundleIdentifier': 'com.screendraw.app',
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'LSMinimumSystemVersion': '12.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,
        'NSScreenCaptureUsageDescription': 'ScreenDraw needs screen capture access for the screenshot tool.',
    },
    'packages': ['objc', 'AppKit', 'Foundation', 'Quartz'],
    'includes': [
        'objc', 'AppKit', 'Foundation', 'Quartz',
        'Cocoa', 'CoreFoundation', 'CoreGraphics',
        'PyObjCTools', 'PyObjCTools.Conversion',
    ],
    'frameworks': [],
    'excludes': [
        'matplotlib', 'scipy', 'pandas', 'numpy',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'wx', 'gtk', 'tkinter', 'test', 'unittest',
    ],
}

setup(
    name='ScreenDraw',
    version=VERSION,
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
