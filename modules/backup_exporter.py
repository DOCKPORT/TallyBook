"""
Database backup utilities for TallyBook.

Provides pure file-copy and path-generation functions for backing
up the TallyBook SQLite database.  No Qt imports, no UI.
"""

import os
import shutil
from datetime import datetime


def get_default_backup_path(db_dir: str, timestamp: str | None = None) -> str:
    """Generate a default backup file path inside a Backups subdirectory.

    Creates the ``Backups/`` directory inside *db_dir* if it doesn't exist.

    Args:
        db_dir: Directory containing the active database file.
        timestamp: Optional timestamp string (e.g. ``'2026-06-06_23-30-00'``).
            If omitted, the current local time is used.

    Returns:
        Absolute path like ``{db_dir}/Backups/tallybook_backup_{timestamp}.db``.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(db_dir, "Backups")
    os.makedirs(backup_dir, exist_ok=True)
    return os.path.join(backup_dir, f"tallybook_backup_{timestamp}.db")


def create_backup(source_db_path: str, dest_path: str) -> None:
    """Copy a database file to *dest_path* and set its modification time.

    Args:
        source_db_path: Path to the active database file.
        dest_path: Destination path for the backup.

    Raises:
        FileNotFoundError: If *source_db_path* does not exist.
        OSError: If the file copy or ``utime`` call fails.
    """
    shutil.copy(source_db_path, dest_path)
    os.utime(dest_path, (datetime.now().timestamp(), datetime.now().timestamp()))