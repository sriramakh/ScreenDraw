"""
Build script for ScreenDraw Windows.

For a simple standalone .exe:
    python setup_windows.py

For a full Windows installer (.exe with Start Menu, Uninstaller, etc.):
    cd windows_installer
    build_installer.bat

Requires: pip install pyinstaller pillow
"""

import subprocess
import sys
import os

def build():
    script = "screendraw_windows.py"
    name = "ScreenDraw"

    if not os.path.exists(script):
        print(f"ERROR: {script} not found in current directory.")
        sys.exit(1)

    # Generate icon if possible
    icon_path = os.path.join("windows_installer", "screendraw.ico")
    if not os.path.exists(icon_path):
        try:
            subprocess.run([sys.executable, os.path.join("windows_installer", "generate_icon.py")], check=True)
        except Exception:
            icon_path = None

    # Generate version info
    version_file = os.path.join("windows_installer", "file_version_info.txt")
    if not os.path.exists(version_file):
        try:
            subprocess.run([sys.executable, os.path.join("windows_installer", "version_info.py")], check=True)
        except Exception:
            version_file = None

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", name,
        "--clean",
        "--noconfirm",
    ]

    if icon_path and os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
    if version_file and os.path.exists(version_file):
        cmd.extend(["--version-file", version_file])

    # Hidden imports for runtime dependencies
    for mod in ["pystray", "pystray._win32", "keyboard", "keyboard._winkeyboard",
                 "pyautogui", "PIL", "PIL.Image", "PIL.ImageDraw"]:
        cmd.extend(["--hidden-import", mod])

    cmd.append(script)

    print(f"Building {name}...")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)
    if result.returncode == 0:
        print()
        print(f"SUCCESS! Executable created at: dist/{name}.exe")
        print(f"You can copy {name}.exe anywhere and run it.")
        print()
        print("For a full Windows installer with Start Menu shortcuts,")
        print("uninstaller, etc., run: windows_installer\\build_installer.bat")
    else:
        print()
        print("BUILD FAILED. Make sure PyInstaller is installed:")
        print("  pip install pyinstaller")
        sys.exit(1)

if __name__ == "__main__":
    build()
