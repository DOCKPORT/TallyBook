#!/usr/bin/env python3
"""Centralized path resolution for TallyBook.

All path-related utility functions are collected here so they can be
imported from any module without circular dependencies or duplication.
"""  # noqa: EXE001

import os
import sys
from datetime import datetime


def resource_path(relative_path: str) -> str:
    """Get absolute path to a resource, works for dev and for PyInstaller.

    When bundled with PyInstaller, ``sys._MEIPASS`` points to the temporary
    extraction directory.  During development the working directory is used.
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_db_path() -> str:
    """Return the absolute path of the TallyBook SQLite database.

    Uses QStandardPaths so the location follows the platform convention
    (e.g. ``~/.local/share/TallyBook/tallybook.db`` on Linux).
    """
    from PySide6.QtCore import QStandardPaths

    app_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "tallybook.db")


def get_app_dir() -> str:
    """Return the application's data directory (parent of the database file)."""
    return os.path.dirname(get_db_path())


def get_backup_path(timestamp: str | None = None) -> str:
    """Return a full path suitable for saving a database backup.

    The directory is created if it does not exist yet.  When *timestamp* is
    omitted a local datetime string is generated automatically.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(get_app_dir(), "Backups")
    os.makedirs(backup_dir, exist_ok=True)
    return os.path.join(backup_dir, f"tallybook_backup_{timestamp}.db")


def get_desktop_entry_path() -> str:
    """Return the path of the AppImage desktop entry file."""
    return os.path.join(
        os.path.expanduser("~/.local/share/applications"),
        "tallybook.desktop",
    )