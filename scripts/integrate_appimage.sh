#!/bin/bash

# Configuration
APP_NAME="TallyBook"
APP_IMAGE="TallyBook.AppImage"
ICON_FILE="tallybook_app_icon.png"
INSTALL_DIR="$HOME/Applications"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"

echo "Integrating $APP_NAME with the system..."

# 1. Ensure directories exist
mkdir -p "$INSTALL_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$DESKTOP_DIR"

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

echo "Success! $APP_NAME should now appear in your application menu."
echo "You can find the AppImage at: $INSTALL_DIR/$APP_NAME.AppImage"
