"""
Setup script to build ScreenDraw as a macOS .app bundle.
Usage: python3 setup.py py2app
"""

from setuptools import setup

APP = ['screendraw.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': 'ScreenDraw',
        'CFBundleDisplayName': 'ScreenDraw',
        'CFBundleIdentifier': 'com.screendraw.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '12.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,  # Hide from Dock (status bar app)
        'NSScreenCaptureUsageDescription': 'ScreenDraw needs screen capture access for the screenshot tool.',
    },
    'packages': [],
    'includes': ['objc', 'AppKit', 'Foundation', 'Quartz'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
