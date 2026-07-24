#!/usr/bin/env python3
import os
import sys
import shutil
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFontDatabase
import paths

# Ensure modules directory is on the import path
modules_dir = os.path.join(os.path.dirname(__file__), 'modules')
if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)


def handle_appimage_integration():
    """Checks if running as an AppImage and handles desktop integration."""
    appimage_path = os.environ.get('APPIMAGE')
    if not appimage_path:
        return  # Not running as an AppImage

    desktop_file_path = paths.get_desktop_entry_path()
    if os.path.exists(desktop_file_path):
        return  # Already integrated

    # Calculate scale factor for standalone dialog
    screen = QApplication.primaryScreen()
    screen_geometry = screen.geometry()
    scale_factor = max(0.8, min(screen_geometry.width() / 1920, screen_geometry.height() / 1080))
    def s(val):
        return int(val * scale_factor)

    def show_styled_msg(title, text, info_text=None, icon=QMessageBox.Icon.Question, buttons=QMessageBox.StandardButton.Ok):
        msg = QMessageBox()
        msg.setWindowIcon(QIcon(paths.resource_path("tallybook_app_icon.png")))
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        if info_text:
            msg.setInformativeText(info_text)
        msg.setStandardButtons(buttons)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes if buttons & QMessageBox.StandardButton.Yes else QMessageBox.StandardButton.Ok)
        
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: #1e1e1e; }}
            QLabel {{ color: #ffffff; font-size: {s(14)}px; padding: {s(10)}px; }}
            QPushButton {{ 
                background-color: #444; color: white; border: 1px solid #666; 
                padding: {s(6)}px {s(16)}px; border-radius: {s(4)}px; 
                font-size: {s(13)}px; min-width: {s(80)}px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #555; }}
        """)
        
        for btn in msg.findChildren(QPushButton):
            btn.setIcon(QIcon())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            s_btn = msg.standardButton(btn)
            if s_btn in [QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.Yes]:
                btn.setStyleSheet(f"background-color: #2d5a27; border: 1px solid #3d8c34; padding: {s(6)}px {s(16)}px; border-radius: {s(4)}px;")
            elif s_btn in [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Close]:
                btn.setStyleSheet(f"background-color: #8a2b2b; border: 1px solid #b71c1c; padding: {s(6)}px {s(16)}px; border-radius: {s(4)}px;")
        
        return msg.exec()

    # Prompt user for integration
    if show_styled_msg(
        "System Integration", 
        "TallyBook is not integrated with your system.",
        "Would you like to add it to your application menu and dock?",
        QMessageBox.Icon.Question,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    ) == QMessageBox.StandardButton.Yes:
        try:
            # 1. Ensure directories exist
            apps_dir = os.path.expanduser("~/.local/share/applications")
            icons_dir = os.path.expanduser("~/.local/share/icons")
            os.makedirs(apps_dir, exist_ok=True)
            os.makedirs(icons_dir, exist_ok=True)

            # 2. Extract/Save Icon
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
                
            show_styled_msg("Success", "TallyBook has been integrated with your system!", icon=QMessageBox.Icon.Information)
        except Exception as e:
            show_styled_msg("Error", f"Failed to integrate: {str(e)}", icon=QMessageBox.Icon.Warning)

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
