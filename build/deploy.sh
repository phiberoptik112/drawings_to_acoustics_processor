#!/bin/bash
# Deployment script for Acoustic Analysis Tool - macOS Version
# Creates distributable DMG file or ZIP archive

set -e  # Exit on error

echo "=========================================="
echo "Acoustic Analysis Tool - macOS Deployment"
echo "=========================================="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEPLOY_DIR="$SCRIPT_DIR/deploy"
APP_PATH="$DEPLOY_DIR/AcousticAnalysisTool.app"

# Check if the app bundle exists
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: Application bundle not found at $APP_PATH"
    echo "Please run build.sh first to create the application bundle"
    exit 1
fi

echo "Found application bundle: $APP_PATH"

# Get app size
APP_SIZE=$(du -sh "$APP_PATH" | awk '{print $1}')
echo "Bundle size: $APP_SIZE"

# Read build info if available
BUILD_INFO="$DEPLOY_DIR/build_info.json"
if [ -f "$BUILD_INFO" ]; then
    echo ""
    echo "Build Information:"
    if command -v jq &> /dev/null; then
        VERSION=$(jq -r '.version' "$BUILD_INFO")
        BUILD_NUM=$(jq -r '.build_number' "$BUILD_INFO")
        BUILD_DATE=$(jq -r '.build_date' "$BUILD_INFO")
        echo "  Version: $VERSION.$BUILD_NUM"
        echo "  Build Date: $BUILD_DATE"
    else
        cat "$BUILD_INFO"
    fi
fi

echo ""
echo "Choose deployment format:"
echo "  1) DMG (macOS Disk Image - recommended for distribution)"
echo "  2) ZIP (Archive - simple and compatible)"
echo "  3) Both DMG and ZIP"
echo ""
read -p "Enter choice [1-3]: " CHOICE

case $CHOICE in
    1|"")
        CREATE_DMG=true
        CREATE_ZIP=false
        ;;
    2)
        CREATE_DMG=false
        CREATE_ZIP=true
        ;;
    3)
        CREATE_DMG=true
        CREATE_ZIP=true
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Create ZIP archive
if [ "$CREATE_ZIP" = true ]; then
    echo ""
    echo "Creating ZIP archive..."
    ZIP_NAME="AcousticAnalysisTool-macOS.zip"
    cd "$DEPLOY_DIR"
    
    # Remove old zip if exists
    [ -f "$ZIP_NAME" ] && rm "$ZIP_NAME"
    
    # Create zip with proper permissions preserved
    zip -r -y "$ZIP_NAME" "AcousticAnalysisTool.app" > /dev/null
    
    ZIP_SIZE=$(du -sh "$ZIP_NAME" | awk '{print $1}')
    echo "✓ ZIP created: $DEPLOY_DIR/$ZIP_NAME ($ZIP_SIZE)"
fi

# Create DMG disk image
if [ "$CREATE_DMG" = true ]; then
    echo ""
    echo "Creating DMG installer..."
    
    DMG_NAME="AcousticAnalysisTool-macOS.dmg"
    DMG_TEMP="$DEPLOY_DIR/dmg_temp"
    
    # Remove old DMG and temp directory if they exist
    [ -f "$DEPLOY_DIR/$DMG_NAME" ] && rm "$DEPLOY_DIR/$DMG_NAME"
    [ -d "$DMG_TEMP" ] && rm -rf "$DMG_TEMP"
    
    # Create temporary directory for DMG contents
    mkdir -p "$DMG_TEMP"
    
    # Copy app bundle to temp directory
    cp -R "$APP_PATH" "$DMG_TEMP/"
    
    # Create symbolic link to Applications folder
    ln -s /Applications "$DMG_TEMP/Applications"
    
    # Create README file for DMG
    cat > "$DMG_TEMP/README.txt" << 'EOF'
Acoustic Analysis Tool - Installation Instructions

To install:
1. Drag "AcousticAnalysisTool.app" to the "Applications" folder
2. Open from your Applications folder
3. On first launch, you may need to right-click → Open to bypass Gatekeeper

For LEED acoustic certification analysis.

© 2025 Acoustic Solutions
EOF

    # Check if create-dmg is available
    if command -v create-dmg &> /dev/null; then
        echo "Using create-dmg for professional DMG creation..."
        create-dmg \
            --volname "Acoustic Analysis Tool" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "AcousticAnalysisTool.app" 175 120 \
            --hide-extension "AcousticAnalysisTool.app" \
            --app-drop-link 425 120 \
            --no-internet-enable \
            "$DEPLOY_DIR/$DMG_NAME" \
            "$DMG_TEMP" || {
                echo "Warning: create-dmg failed, falling back to hdiutil"
                # Fallback to basic DMG creation
                hdiutil create -volname "Acoustic Analysis Tool" \
                    -srcfolder "$DMG_TEMP" \
                    -ov -format UDZO \
                    "$DEPLOY_DIR/$DMG_NAME"
            }
    else
        echo "Using hdiutil for basic DMG creation..."
        echo "Tip: Install create-dmg for professional DMG layout: brew install create-dmg"
        
        # Basic DMG creation using hdiutil
        hdiutil create -volname "Acoustic Analysis Tool" \
            -srcfolder "$DMG_TEMP" \
            -ov -format UDZO \
            "$DEPLOY_DIR/$DMG_NAME"
    fi
    
    # Clean up temp directory
    rm -rf "$DMG_TEMP"
    
    DMG_SIZE=$(du -sh "$DEPLOY_DIR/$DMG_NAME" | awk '{print $1}')
    echo "✓ DMG created: $DEPLOY_DIR/$DMG_NAME ($DMG_SIZE)"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="

if [ "$CREATE_ZIP" = true ]; then
    echo "ZIP: $DEPLOY_DIR/$ZIP_NAME"
fi

if [ "$CREATE_DMG" = true ]; then
    echo "DMG: $DEPLOY_DIR/$DMG_NAME"
fi

echo ""
echo "Next Steps:"
echo "1. Test the installation on a clean macOS system"
echo "2. For distribution, consider:"
echo "   - Code signing with Apple Developer certificate"
echo "   - Notarization for Gatekeeper approval"
echo "   - stapling the notarization ticket to the DMG"
echo ""
echo "Code signing command (if you have a certificate):"
echo "  codesign --deep --force --verify --verbose --sign \"Developer ID Application: Your Name\" AcousticAnalysisTool.app"
echo ""
echo "Notarization command (requires Apple ID):"
echo "  xcrun notarytool submit AcousticAnalysisTool-macOS.dmg --apple-id your@email.com --team-id TEAMID --wait"

