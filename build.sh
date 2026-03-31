#!/bin/bash
set -e

APP_NAME="ScreenDraw"
BUILD_DIR="build"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
CONTENTS="$APP_BUNDLE/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

SRC_DIR="ScreenDraw"

echo "Building $APP_NAME..."

# Clean
rm -rf "$BUILD_DIR"
mkdir -p "$MACOS" "$RESOURCES"

# Compile
swiftc \
    -swift-version 5 \
    -target arm64-apple-macosx13.0 \
    -sdk $(xcrun --show-sdk-path) \
    -framework Cocoa \
    -o "$MACOS/$APP_NAME" \
    "$SRC_DIR/main.swift" \
    "$SRC_DIR/AppDelegate.swift" \
    "$SRC_DIR/OverlayWindow.swift" \
    "$SRC_DIR/DrawingView.swift" \
    "$SRC_DIR/ToolbarPanel.swift" \
    "$SRC_DIR/DrawingEngine.swift"

# Create Info.plist for the bundle
cat > "$CONTENTS/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>ScreenDraw</string>
    <key>CFBundleDisplayName</key>
    <string>ScreenDraw</string>
    <key>CFBundleIdentifier</key>
    <string>com.screendraw.app</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>ScreenDraw</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
EOF

echo "Build successful! App bundle: $APP_BUNDLE"
echo ""
echo "To run: open $APP_BUNDLE"
