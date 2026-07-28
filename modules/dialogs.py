"""
Styled dialog helpers for TallyBook.

Provides standalone functions for showing styled QMessageBox and QInputDialog
without standard OS button icons, extracted from TallyBookWindow.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QWidget,
)
from scaling import scaled


def show_modern_message(
    parent: QWidget,
    title: str,
    text: str,
    icon_type: QMessageBox.Icon = QMessageBox.Icon.Information,
    buttons: QMessageBox.StandardButtons = QMessageBox.StandardButton.Ok,
    scale_factor: float = 1.0,
) -> int:
    """Shows a styled QMessageBox without standard OS button icons.

    Args:
        parent: Parent widget for the dialog.
        title: Window title.
        text: Message text.
        icon_type: Message box icon type.
        buttons: Standard buttons to show.
        scale_factor: DPI scale factor for sizing.

    Returns:
        The StandardButton value of the clicked button.
    """
    def s(val):
        return scaled(scale_factor, val)

    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(icon_type)
    msg.setStandardButtons(buttons)

    # Style the dialog
    msg.setStyleSheet(f"""
        QMessageBox {{ 
            background-color: #1e1e1e; 
        }}
        QLabel {{ 
            color: #ffffff; 
            font-size: {s(14)}px; 
            padding: {s(10)}px;
        }}
        QPushButton {{ 
            background-color: #444; 
            color: white; 
            border: 1px solid #666; 
            padding: {s(6)}px {s(16)}px; 
            border-radius: {s(4)}px; 
            font-size: {s(13)}px; 
            min-width: {s(80)}px;
            font-weight: bold;
        }}
        QPushButton:hover {{ 
            background-color: #555; 
        }}
    """)

    # Find buttons and remove icons + apply color-coding
    for btn in msg.findChildren(QPushButton):
        btn.setIcon(QIcon())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Color coding for primary actions
        s_btn = msg.standardButton(btn)
        if s_btn in [
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Save,
        ]:
            btn.setStyleSheet(
                f"background-color: #2d5a27; border: 1px solid #3d8c34; "
                f"padding: {s(6)}px {s(16)}px; border-radius: {s(4)}px;"
            )
        elif s_btn in [
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Discard,
            QMessageBox.StandardButton.Close,
        ]:
            btn.setStyleSheet(
                f"background-color: #8a2b2b; border: 1px solid #b71c1c; "
                f"padding: {s(6)}px {s(16)}px; border-radius: {s(4)}px;"
            )

    return msg.exec()


def show_modern_input(
    parent: QWidget,
    title: str,
    label: str,
    default: str = "",
    scale_factor: float = 1.0,
) -> tuple[str, bool]:
    """Shows a styled QInputDialog without standard OS button icons.

    Args:
        parent: Parent widget for the dialog.
        title: Window title.
        label: Prompt label text.
        default: Default input value.
        scale_factor: DPI scale factor for sizing.

    Returns:
        Tuple of (text_value, accepted) where accepted is True if the user
        clicked Confirm/OK.
    """
    def s(val):
        return scaled(scale_factor, val)

    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(default)
    dialog.setOkButtonText("Confirm")
    dialog.setCancelButtonText("Cancel")

    # Style the dialog
    dialog.setStyleSheet(f"""
        QInputDialog {{ 
            background-color: #1e1e1e; 
            border: 1px solid #444;
        }}
        QLabel {{ 
            color: #ffffff; 
            font-size: {s(14)}px; 
            padding: {s(10)}px;
            background-color: transparent;
        }}
        QLineEdit {{
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #444;
            border-radius: {s(4)}px;
            padding: {s(8)}px;
            font-size: {s(14)}px;
            margin: {s(10)}px;
        }}
        QPushButton {{ 
            background-color: #444; 
            color: white; 
            border: 1px solid #666; 
            padding: {s(6)}px {s(16)}px; 
            border-radius: {s(4)}px; 
            font-size: {s(13)}px; 
            min-width: {s(80)}px;
            font-weight: bold;
        }}
        QPushButton:hover {{ 
            background-color: #555; 
        }}
    """)

    # Find buttons and remove icons + apply color-coding
    for btn in dialog.findChildren(QPushButton):
        btn.setIcon(QIcon())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Color coding for actions
        btn_text = btn.text().upper()
        if "CONFIRM" in btn_text or "OK" in btn_text:
            btn.setStyleSheet(
                f"background-color: #2d5a27; border: 1px solid #3d8c34; "
                f"padding: {s(6)}px {s(16)}px; border-radius: {s(4)}px;"
            )
        elif "CANCEL" in btn_text:
            btn.setStyleSheet(
                f"background-color: #8a2b2b; border: 1px solid #b71c1c; "
                f"padding: {s(6)}px {s(16)}px; border-radius: {s(4)}px;"
            )

    ok = dialog.exec()
    return dialog.textValue(), ok == QDialog.Accepted