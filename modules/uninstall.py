#!/usr/bin/env python3
"""Application uninstallation logic for TallyBook.

Handles the file-system side of uninstalling the application: gathering
all file paths that belong to the app and deleting them.
"""  # noqa: EXE001

import os
import shutil

import dialogs
from PySide6.QtWidgets import QMessageBox, QWidget


def uninstall_app(
    parent_widget: QWidget,
    scale_factor: float,
    db_path: str,
    appimage_path: str | None,
    is_frozen: bool,
    executable_path: str | None,
) -> bool:
    """Run the full uninstall workflow.

    Shows confirmation dialogs, gathers all related paths on the
    filesystem, and deletes them.  The caller is responsible for calling
    ``QApplication.quit()`` after a successful return.

    Args:
        parent_widget: Parent for dialogs.
        scale_factor: DPI scale factor for dialog sizing.
        db_path: Absolute path of the SQLite database file.
        appimage_path: Value of ``APPIMAGE`` env var, or ``None``.
        is_frozen: Whether ``sys.frozen`` is truthy.
        executable_path: ``sys.executable`` when frozen, else ``None``.

    Returns:
        ``True`` if uninstallation completed successfully, ``False`` if
        the user cancelled at any point.
    """
    # --- First warning ---
    reply = dialogs.show_modern_message(
        parent_widget,
        "Uninstall",
        "CRITICAL WARNING:\n\n"
        "Are you sure you want to completely uninstall TallyBook?\n\n"
        "This will permanently delete the application binary, database, "
        "all backups, the desktop entry, and the icon.\n\n"
        "This action CANNOT be undone and the application will close "
        "immediately.",
        QMessageBox.Icon.Warning,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        scale_factor,
    )

    if reply != QMessageBox.StandardButton.Yes:
        return False

    # --- Final text confirmation ---
    text, ok = dialogs.show_modern_input(
        parent_widget,
        "Final Confirmation",
        "To confirm complete uninstallation and data deletion, "
        "please type 'DELETE' in all caps:",
        "",
        scale_factor,
    )

    if not ok or text != "DELETE":
        if ok:
            dialogs.show_modern_message(
                parent_widget,
                "Cancelled",
                "Incorrect confirmation text. Uninstall cancelled.",
                QMessageBox.Icon.Information,
                QMessageBox.StandardButton.Ok,
                scale_factor,
            )
        return False

    # --- Gather paths ---
    to_delete: list[str] = []

    # Application Binary
    if appimage_path and os.path.exists(appimage_path):
        to_delete.append(appimage_path)
    elif is_frozen and executable_path:
        to_delete.append(executable_path)

    # Database & Backups
    app_data_dir: str | None = None
    if db_path:
        to_delete.append(db_path)
        for suffix in ("-journal", "-wal", "-shm"):
            p = db_path + suffix
            if os.path.exists(p):
                to_delete.append(p)

        app_data_dir = os.path.dirname(db_path)
        backup_dir = os.path.join(app_data_dir, "Backups")
        if os.path.exists(backup_dir):
            to_delete.append(backup_dir)

    # Desktop Entry and associated Icon
    desktop_dir = os.path.expanduser("~/.local/share/applications")
    if os.path.exists(desktop_dir):
        for filename in os.listdir(desktop_dir):
            if not filename.endswith(".desktop"):
                continue

            desktop_path = os.path.join(desktop_dir, filename)
            try:
                with open(desktop_path, "r") as f:
                    desktop_content = f.read()
            except OSError:
                continue

            is_ours = False
            if appimage_path and appimage_path in desktop_content:
                is_ours = True
            if "tallybook" in filename.lower():
                is_ours = True

            if not is_ours:
                continue

            to_delete.append(desktop_path)

            # Parse icon path from desktop content
            for line in desktop_content.splitlines():
                if line.startswith("Icon="):
                    icon_val = line.split("=", 1)[1].strip()
                    if os.path.isabs(icon_val) and os.path.exists(icon_val):
                        to_delete.append(icon_val)
                    else:
                        # Search for named icon in common user icon dirs
                        for idir in (
                            os.path.expanduser("~/.local/share/icons"),
                            os.path.expanduser("~/.icons"),
                        ):
                            if not os.path.exists(idir):
                                continue
                            for root, _dirs, files in os.walk(idir):
                                for f_icon in files:
                                    if f_icon.startswith(icon_val):
                                        to_delete.append(
                                            os.path.join(root, f_icon)
                                        )

    # --- Perform deletion ---
    try:
        for path in set(to_delete):
            if not path:
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

        # Final attempt to remove the app data directory if empty
        if app_data_dir and os.path.exists(app_data_dir):
            try:
                os.rmdir(app_data_dir)
            except OSError:
                pass

        dialogs.show_modern_message(
            parent_widget,
            "Uninstall Complete",
            "TallyBook has been successfully uninstalled. "
            "The application will now close.",
            QMessageBox.Icon.Information,
            QMessageBox.StandardButton.Ok,
            scale_factor,
        )
        return True

    except Exception as e:  # noqa: BLE001
        dialogs.show_modern_message(
            parent_widget,
            "Error",
            f"Failed to complete uninstall: {e}",
            QMessageBox.Icon.Critical,
            QMessageBox.StandardButton.Ok,
            scale_factor,
        )
        return False