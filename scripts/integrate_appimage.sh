#!/bin/bash

# Configuration
APP_NAME="TallyBook"
APP_ID="io.github.dockport.TallyBook"
APP_IMAGE="TallyBook.AppImage"
ICON_FILE="tallybook_app_icon.png"
METAINFO_TEMPLATE="io.github.dockport.TallyBook.metainfo.xml.in"
INSTALL_DIR="$HOME/Applications"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"
METAINFO_DIR="$HOME/.local/share/metainfo"

echo "Integrating $APP_NAME with the system..."

# 1. Ensure directories exist
mkdir -p "$INSTALL_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$METAINFO_DIR"

# 2. Copy AppImage to a stable location
cp "$APP_IMAGE" "$INSTALL_DIR/$APP_NAME.AppImage"
chmod +x "$INSTALL_DIR/$APP_NAME.AppImage"

# 3. Copy Icon
cp "$ICON_FILE" "$ICON_DIR/tallybook.png"

# 4. Create Desktop Entry
cat > "$DESKTOP_DIR/tallybook.desktop" <<EOF
[Desktop Entry]
Name=$APP_NAME
Exec=$INSTALL_DIR/$APP_NAME.AppImage
Icon=$ICON_DIR/tallybook.png
Type=Application
Categories=Finance;Office;
Terminal=false
Comment=Financial Ledger App
StartupWMClass=TallyBook
EOF

# 5. Install AppStream metainfo (for software center discovery)
if [ -f "$METAINFO_TEMPLATE" ]; then
    # Extract version from modules/version.py
    APP_VERSION=$(grep ^APP_VERSION modules/version.py 2>/dev/null | cut -d'"' -f2)
    if [ -z "$APP_VERSION" ]; then
        APP_VERSION="1.0.0"
    fi
    echo "Generating AppStream metainfo for version $APP_VERSION ..."
    sed "s/@APP_VERSION@/$APP_VERSION/g" "$METAINFO_TEMPLATE" > "$METAINFO_DIR/$APP_ID.metainfo.xml"
    echo "  -> $METAINFO_DIR/$APP_ID.metainfo.xml"
else
    echo "Warning: $METAINFO_TEMPLATE not found — skipping AppStream metainfo installation"
fi

echo ""
echo "Success! $APP_NAME should now appear in your application menu."
echo "You can find the AppImage at: $INSTALL_DIR/$APP_NAME.AppImage"
