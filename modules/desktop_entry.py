#!/usr/bin/env python3
"""Desktop entry integration for TallyBook's AppImage.

Handles creation of the ``.desktop`` file so the application appears
in the system launcher with an icon when run as an AppImage.
"""  # noqa: EXE001

import os
import shutil
import sys

import paths


def handle_appimage_integration() -> None:
    """Automatically integrates the AppImage into the system (desktop entry).

    This function is a no-op when the application is *not* running as an
    AppImage (i.e. ``APPIMAGE`` environment variable is not set).

    If a desktop entry already exists at the expected location the
    function returns immediately without modifying anything.
    """
    appimage_path = os.environ.get("APPIMAGE")
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
        with open(desktop_file_path, "w") as f:
            f.write(desktop_content)

    except (OSError, PermissionError) as e:
        # Silently log integration failure; non-critical
        print(f"TallyBook: Failed to create desktop entry: {e}", file=sys.stderr)