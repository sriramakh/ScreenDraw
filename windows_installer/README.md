# ScreenDraw Windows Installer Build Guide

## Quick Build

Just double-click **`build_installer.bat`** on a Windows machine. It will:

1. Install Python dependencies (PyInstaller, Pillow, etc.)
2. Generate the app icon (`screendraw.ico`)
3. Generate version metadata
4. Bundle the app with PyInstaller
5. Create a professional installer with Inno Setup (if installed)

## Output

| File | Description |
|------|-------------|
| `dist\ScreenDraw\ScreenDraw.exe` | Standalone app (portable) |
| `installer_output\ScreenDraw_Setup_1.0.0.exe` | Windows installer |

## Prerequisites

### Required
- **Python 3.9+** — [python.org](https://python.org)
- **PyInstaller** — `pip install pyinstaller`
- **Pillow** — `pip install pillow`

### Optional (for the installer)
- **Inno Setup 6** — [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
  - Free, widely-used Windows installer creator
  - Without it, you still get a portable `.exe`; with it, you get a proper `Setup.exe`

## Manual Build Steps

### 1. Generate icon
```
python generate_icon.py
```

### 2. Generate version info
```
python version_info.py
```

### 3. Build with PyInstaller
```
cd ..
pyinstaller --clean --noconfirm windows_installer\ScreenDraw.spec
```

### 4. Create installer (requires Inno Setup)
```
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" windows_installer\ScreenDraw_Installer.iss
```

## What the Installer Provides

- ✅ One-click install to `C:\Program Files\ScreenDraw`
- ✅ Start Menu shortcut
- ✅ Desktop shortcut (optional)
- ✅ Auto-start on login (optional)
- ✅ Uninstaller in Add/Remove Programs
- ✅ Kills running instances before upgrade
- ✅ Clean uninstall with config cleanup
- ✅ UAC admin prompt (needed for global hotkeys)
- ✅ Modern wizard-style UI
- ✅ LZMA2 compression (~50-70% smaller)

## Distribution

Distribute `ScreenDraw_Setup_1.0.0.exe` to your users.
They double-click it → Next → Install → Done. That's it.

## Files in this Directory

| File | Purpose |
|------|---------|
| `build_installer.bat` | Automated build script |
| `generate_icon.py` | Creates `screendraw.ico` from code |
| `version_info.py` | Generates Windows exe metadata |
| `ScreenDraw.spec` | PyInstaller bundling config |
| `ScreenDraw_Installer.iss` | Inno Setup installer script |
