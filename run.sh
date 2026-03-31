#!/bin/bash
# ScreenDraw - Launch Script
# Draws over your screen for live presentations and demos

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check for PyObjC
python3 -c "import objc, AppKit, Quartz" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required dependencies..."
    pip3 install pyobjc-framework-Cocoa pyobjc-framework-Quartz
fi

echo "Starting ScreenDraw..."
echo "  Press D to toggle drawing on/off"
echo "  Press Cmd+Q to quit"
echo ""

python3 "$SCRIPT_DIR/screendraw.py"
