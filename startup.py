#!/usr/bin/env python3
import os
import sys
import shutil
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
import paths

# Ensure modules directory is on the import path
modules_dir = os.path.join(os.path.dirname(__file__), 'modules')
if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)


def handle_appimage_integration():
    """Automatically integrates the AppImage into the system (desktop entry)."""
    appimage_path = os.environ.get('APPIMAGE')
    if not appimage_path:
        return  # Not running as an AppImage

    desktop_file_path = paths.get_desktop_entry_path()
    if os.path.exists(desktop_file_path):
        return  # Already integrated

    try:
        # 1. Ensure directories exist
        apps_dir = os.path.expanduser("~/.local/share/applications")
        icons_dir = os.path.expanduser("~/.local/share/icons")
        os.makedirs(apps_dir, exist_ok=True)
        os.makedirs(icons_dir, exist_ok=True)

        # 2. Copy icon
        bundled_icon = paths.resource_path("tallybook_app_icon.png")
        target_icon = os.path.join(icons_dir, "tallybook.png")
        
        if os.path.exists(bundled_icon):
            shutil.copy2(bundled_icon, target_icon)

        # 3. Create Desktop Entry
        desktop_content = f"""[Desktop Entry]
Name=TallyBook
Exec={appimage_path}
Icon={target_icon}
Type=Application
Categories=Finance;Office;
Terminal=false
Comment=Financial Ledger App
StartupWMClass=TallyBook
"""
        with open(desktop_file_path, 'w') as f:
            f.write(desktop_content)

    except Exception as e:
        # Silently log integration failure; non-critical
        print(f"TallyBook: Failed to create desktop entry: {e}", file=sys.stderr)

def main():
    """Main entry point for the application."""
    # Import TallyBookWindow here (after sys.path is set) to satisfy ruff E402
    from TallyBook import TallyBookWindow

    # Create the Application instance
    app = QApplication(sys.argv)
    app.setApplicationName("TallyBook")
    
    # Load Bundled Fonts
    font_paths = []
    
    # Check assets/fonts directory
    font_dir = paths.resource_path("assets/fonts")
    if os.path.exists(font_dir):
        for font_file in os.listdir(font_dir):
            if font_file.endswith(".ttf"):
                font_paths.append(os.path.join(font_dir, font_file))

    for fp in set(font_paths):
        QFontDatabase.addApplicationFont(fp)

    # Handle AppImage integration if running as an AppImage
    handle_appimage_integration()

    # Create and show the main window
    window = TallyBookWindow()
    window.showMaximized()

    # Run the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
