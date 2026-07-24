#!/bin/bash
set -e

echo "================================"
echo " Running PyInstaller..."
echo "================================"
cd /build
pyinstaller --noconfirm TallyBook.spec

echo "================================"
echo " Building AppImage..."
echo "================================"
APPDIR=TallyBook.AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/metainfo"
cp dist/TallyBook "$APPDIR/usr/bin/TallyBook"

# Create the AppRun wrapper script
cat > "$APPDIR/AppRun" << 'APPRUNEOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export GIO_EXTRA_MODULES=""
export GIO_MODULE_DIR=/nonexistent
export GTK_MODULES=""
export GTK_PATH=""
export NO_AT_BRIDGE=1
exec 2> >(grep -v 'Failed to load module' >&2)
exec "$HERE/usr/bin/TallyBook"
APPRUNEOF
chmod +x "$APPDIR/AppRun"

# Generate AppStream metainfo from template
APP_VERSION=$(grep ^APP_VERSION modules/version.py | cut -d'"' -f2)
echo "Building AppStream metainfo for version $APP_VERSION ..."
sed "s/@APP_VERSION@/$APP_VERSION/g" io.github.dockport.TallyBook.metainfo.xml.in \
    > "$APPDIR/usr/share/metainfo/io.github.dockport.TallyBook.metainfo.xml"

# Validate the metainfo file
appstream-util validate "$APPDIR/usr/share/metainfo/io.github.dockport.TallyBook.metainfo.xml" || true

# Create the required .desktop file for appimagetool
cat > "$APPDIR/io.github.dockport.TallyBook.desktop" << DESKEOF
[Desktop Entry]
Name=TallyBook
Comment=Financial Ledger App
Exec=TallyBook
Icon=tallybook_app_icon
Type=Application
Categories=Finance;Office;
Terminal=false
StartupWMClass=TallyBook
DESKEOF

# Copy icon
cp tallybook_app_icon.png "$APPDIR/tallybook_app_icon.png"

if [ ! -f appimagetool ]; then
    wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool
    chmod +x appimagetool
fi

ARCH=x86_64 ./appimagetool --appimage-extract-and-run "$APPDIR"
echo "✅ AppImage build complete!"