import os
import sys

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

import paths

# Ensure modules directory is on the import path
modules_dir = os.path.join(os.path.dirname(__file__), 'modules')
if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)


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
    from desktop_entry import handle_appimage_integration
    handle_appimage_integration()

    # Create and show the main window
    window = TallyBookWindow()
    window.showMaximized()

    # Run the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
