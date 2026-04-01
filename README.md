# ScreenDraw - Live Screen Drawing Overlay

A cross-platform screen annotation app that creates a transparent overlay on your screen, letting you draw, annotate, and highlight anything visible — perfect for **live presentations**, **online teaching**, **video tutorials**, and **business demos**.

Available for **macOS** (Python + Swift) and **Windows** (Python).

## Features

### Drawing Tools
- **Pen** — freehand drawing with pressure sensitivity (macOS)
- **Highlighter** — semi-transparent wide strokes
- **Line** — straight lines
- **Arrow** — lines with arrowheads
- **Rectangle** — outlined rectangles
- **Circle** — outlined ovals
- **Text** — click-to-type text annotations
- **Eraser** — remove strokes by touching them
- **Fading Ink** — strokes that disappear after 3 seconds

### Presentation Features
- **Spotlight** — dims screen except a circular area around cursor
- **Zoom Lens** — magnifies area around cursor (2.5x)
- **Laser Pointer** — red dot with glow follows cursor
- **Click Animations** — expanding ring pulse on left/right click
- **Cursor Highlight** — colored halo around cursor (circle, ring, or squircle shape)
- **Whiteboard / Blackboard** — solid background modes
- **Screenshot** — capture a region to clipboard and Desktop
- **Screen Recording** — record your screen to .mov/.avi

### UI & UX
- **16-color palette** — curated colors for annotations
- **Adjustable stroke width** — slider or keyboard `[` / `]`
- **Undo / Redo** — full stroke history
- **Toggle drawing** — switch between drawing and click-through mode
- **Floating toolbar** — draggable dark-themed panel with all controls
- **System tray / Menu bar** — unobtrusive status icon
- **Hidden from screen sharing** — annotations invisible to Zoom/Teams/Meet (macOS)
- **Minimize / Restore** — hide overlay when not needed

## Keyboard Shortcuts

| Key | Action | Windows |
|-----|--------|---------|
| `D` | Toggle drawing on/off | `D` |
| `0` | Pointer (click-through, use other apps) | `0` |
| `1`–`9` | Select drawing tool | `1`–`9` |
| `Tab` | Next tool | `Tab` |
| `Shift+Tab` | Previous tool | `Shift+Tab` |
| `S` | Screenshot | `S` |
| `W` | Toggle Whiteboard | `W` |
| `B` | Toggle Blackboard | `B` |
| `H` | Toggle Cursor Highlight | `H` |
| `Shift+H` | Cycle Cursor Shape | `Shift+H` |
| `F` | Toggle Spotlight | `F` |
| `Z` | Toggle Zoom Lens | `Z` |
| `L` | Toggle Laser Pointer | `L` |
| `K` | Toggle Click Animations | `K` |
| `R` | Toggle Recording | `R` |
| `M` | Minimize | `M` |
| `C` | Clear All | `C` |
| `[` / `-` | Decrease stroke size | `[` |
| `]` / `+` | Increase stroke size | `]` |
| `Cmd+Z` | Undo | `Ctrl+Z` |
| `Cmd+Shift+Z` | Redo | `Ctrl+Shift+Z` |
| `Cmd+Q` / `Esc` | Quit | `Ctrl+Q` / `Esc` |

## Installation

### macOS (Python)

**Prerequisites:** macOS 13.0+, Python 3.10+

```bash
pip3 install pyobjc-framework-Cocoa pyobjc-framework-Quartz pyobjc-framework-AVFoundation
python3 screendraw.py
```

Or build as a standalone .app:
```bash
pip3 install py2app
python3 setup.py py2app
cp -R dist/ScreenDraw.app ~/Applications/
```

### macOS (Swift)

Open `ScreenDraw.xcodeproj` in Xcode and build (⌘B).

### Windows

**Prerequisites:** Windows 10+, Python 3.9+

**Run from source:**
```bash
pip install -r requirements_windows.txt
python screendraw_windows.py
```

**Build a standalone .exe:**
```bash
pip install pyinstaller pillow
python setup_windows.py
```

**Build a full Windows installer** (with Start Menu, Desktop shortcut, Uninstaller):
```bash
cd windows_installer
build_installer.bat
```
This creates `installer_output/ScreenDraw_Setup_1.0.0.exe` — a professional installer that users can double-click to install. Requires [Inno Setup 6](https://jrsoftware.org/isdl.php) (free).

> **Note:** The `keyboard` package requires admin/elevated privileges for global hotkeys on Windows.

## Usage

1. Launch ScreenDraw — a toolbar panel appears on the right side of your screen
2. The overlay is active by default — start drawing immediately
3. Use the **toolbar** or **keyboard shortcuts** to switch tools, colors, and modes
4. Press **D** to toggle drawing off when you need to interact with your screen
5. Press **D** again to resume drawing
6. Use **F** for spotlight, **Z** for zoom, **L** for laser pointer during presentations
7. Press **K** to enable click animations for tutorials

## Architecture

### macOS Python (`screendraw.py`)
- **DrawingEngine** — Stroke model, undo/redo, Core Graphics rendering
- **DrawingView** — NSView subclass, mouse/pen/pressure input
- **OverlayWindow** — Transparent borderless fullscreen window (hidden from screen sharing)
- **ToolbarPanel** — Floating HUD with SF Symbol icons and tooltips
- **AppDelegate** — Coordinator, status bar, keyboard shortcuts, recording

### macOS Swift (`ScreenDraw/`)
- **DrawingEngine.swift** — Tool types, stroke model, color palette, drawing logic
- **DrawingView.swift** — NSView with all overlay rendering
- **OverlayWindow.swift** — Transparent topmost window
- **ToolbarPanel.swift** — Native toolbar with NSStackView
- **AppDelegate.swift** — App lifecycle, hotkeys, recording, text input

### Windows (`screendraw_windows.py`)
- **DrawingEngine** — Stroke model, undo/redo
- **OverlayWindow** — Transparent fullscreen tkinter canvas with Win32 layered window
- **ToolbarPanel** — Dark-themed tk.Toplevel with scrollable button panel
- **SystemTray** — pystray-based system tray icon
- **ScreenRecorder** — opencv-python screen capture to AVI
- **ScreenDrawApp** — Main controller with global keyboard hotkeys
