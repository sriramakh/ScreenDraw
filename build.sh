#!/bin/bash
set -e

APP_NAME="ScreenDraw"
VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
BUILD_DIR="build"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
CONTENTS="$APP_BUNDLE/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
SRC_DIR="ScreenDraw"

# Signing identity: set SIGNING_IDENTITY env var for Developer ID,
# otherwise uses ad-hoc signing (fine for direct distribution)
SIGN_ID="${SIGNING_IDENTITY:--}"

echo "============================================"
echo "  Building $APP_NAME v$VERSION (macOS)"
echo "============================================"
echo ""

# ── Step 1: Clean ────────────────────────────────────────────────
echo "[1/6] Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$MACOS" "$RESOURCES"

# ── Step 2: Generate icon if needed ──────────────────────────────
ICNS_FILE="$SRC_DIR/AppIcon.icns"
if [ ! -f "$ICNS_FILE" ]; then
    echo "[2/6] Generating app icon..."
    if command -v python3 &>/dev/null && python3 -c "import PIL" 2>/dev/null; then
        python3 scripts/generate_macos_icon.py
    else
        echo "       WARNING: Pillow not installed, skipping icon generation."
        echo "       Install with: pip3 install pillow"
    fi
else
    echo "[2/6] App icon found."
fi

# ── Step 3: Compile universal binary (arm64 + x86_64) ───────────
echo "[3/6] Compiling universal binary..."

SWIFT_FILES=(
    "$SRC_DIR/main.swift"
    "$SRC_DIR/AppDelegate.swift"
    "$SRC_DIR/OverlayWindow.swift"
    "$SRC_DIR/DrawingView.swift"
    "$SRC_DIR/ToolbarPanel.swift"
    "$SRC_DIR/DrawingEngine.swift"
)

SDK_PATH=$(xcrun --show-sdk-path)

# Build for Apple Silicon (arm64)
echo "       Compiling arm64..."
swiftc \
    -swift-version 5 \
    -target arm64-apple-macosx13.0 \
    -sdk "$SDK_PATH" \
    -framework Cocoa \
    -O \
    -o "$BUILD_DIR/${APP_NAME}_arm64" \
    "${SWIFT_FILES[@]}"

# Build for Intel (x86_64)
echo "       Compiling x86_64..."
swiftc \
    -swift-version 5 \
    -target x86_64-apple-macosx13.0 \
    -sdk "$SDK_PATH" \
    -framework Cocoa \
    -O \
    -o "$BUILD_DIR/${APP_NAME}_x86_64" \
    "${SWIFT_FILES[@]}"

# Merge into universal binary
echo "       Creating universal binary..."
lipo -create \
    "$BUILD_DIR/${APP_NAME}_arm64" \
    "$BUILD_DIR/${APP_NAME}_x86_64" \
    -output "$MACOS/$APP_NAME"

# Clean up arch-specific binaries
rm -f "$BUILD_DIR/${APP_NAME}_arm64" "$BUILD_DIR/${APP_NAME}_x86_64"

# ── Step 4: Create app bundle contents ───────────────────────────
echo "[4/6] Assembling app bundle..."

# Copy icon
if [ -f "$ICNS_FILE" ]; then
    cp "$ICNS_FILE" "$RESOURCES/AppIcon.icns"
fi

# Copy entitlements
if [ -f "$SRC_DIR/ScreenDraw.entitlements" ]; then
    cp "$SRC_DIR/ScreenDraw.entitlements" "$RESOURCES/"
fi

# Create Info.plist
cat > "$CONTENTS/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.screendraw.app</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSScreenCaptureUsageDescription</key>
    <string>ScreenDraw needs screen capture access for the screenshot and screen recording tools.</string>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
</dict>
</plist>
EOF

# ── Step 5: Code sign ────────────────────────────────────────────
echo "[5/6] Code signing (identity: $SIGN_ID)..."
codesign --deep --force --options runtime --sign "$SIGN_ID" "$APP_BUNDLE"

# ── Step 6: Create DMG ───────────────────────────────────────────
echo "[6/6] Creating DMG installer..."

DMG_NAME="${APP_NAME}_v${VERSION}_macOS"
DMG_STAGING="$BUILD_DIR/dmg_staging"
DMG_PATH="$BUILD_DIR/$DMG_NAME.dmg"

# Create staging directory with app + Applications symlink
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R "$APP_BUNDLE" "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Applications"

# Create the DMG
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$DMG_STAGING" \
    -ov \
    -format UDZO \
    -imagekey zlib-level=9 \
    "$DMG_PATH"

# Clean up staging
rm -rf "$DMG_STAGING"

echo ""
echo "============================================"
echo "  BUILD SUCCESSFUL!"
echo "============================================"
echo ""
echo "  App Bundle: $APP_BUNDLE"
echo "  DMG:        $DMG_PATH"
echo ""
echo "  To run:     open $APP_BUNDLE"
echo "  To distribute: share the .dmg file"
echo ""
echo "  Users just open the DMG and drag"
echo "  ScreenDraw to Applications."
echo "============================================"

# ── Optional: Notarization ───────────────────────────────────────
# Set NOTARIZE=true, APPLE_ID, APPLE_TEAM_ID, and APP_PASSWORD
# environment variables to notarize for Gatekeeper.
if [ "${NOTARIZE}" = "true" ] && [ -n "$APPLE_ID" ]; then
    echo ""
    echo "Submitting for notarization..."
    xcrun notarytool submit "$DMG_PATH" \
        --apple-id "$APPLE_ID" \
        --team-id "$APPLE_TEAM_ID" \
        --password "$APP_PASSWORD" \
        --wait

    echo "Stapling notarization ticket..."
    xcrun stapler staple "$DMG_PATH"
    echo "Notarization complete!"
fi
