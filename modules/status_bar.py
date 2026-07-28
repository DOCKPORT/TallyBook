"""Status bar module for TallyBook.

Provides the StatusBarManager class that builds and manages
the bottom status bar (version label, donate, report bug,
check for updates buttons) and their associated dialogs.
"""
import os
import subprocess

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from version import APP_VERSION

import paths


class StatusBarManager:
    """Builds and manages the TallyBook status bar and its related dialogs.

    Delegates all UI creation through the parent MainWindow's scaling helpers.
    """

    def __init__(self, main_window):
        self.main_window = main_window
        self.s = main_window.s
        self.scale_factor = main_window.scale_factor

        # Widgets we need to keep references to (currently none, but ready
        # for future expansion like dynamic button state changes).
        self.version_label = None
        self.donate_btn = None
        self.report_bug_btn = None
        self.check_updates_btn = None

    def create_status_bar(self):
        """Build and return a fully configured QStatusBar."""
        status_bar = QStatusBar()
        status_bar.setStyleSheet(
            "QStatusBar { background-color: #1e1e1e; border: none; border-top: 1px solid #333333; }"
            " QStatusBar::item { border: none; }"
        )

        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(self.s(10), 0, self.s(10), 0)
        bottom_layout.setSpacing(self.s(8))

        # Version label
        self.version_label = QLabel(APP_VERSION)
        self.version_label.setStyleSheet(
            f"color: #dddddd; font-size: {self.s(12)}px; font-weight: bold;"
        )
        bottom_layout.addWidget(self.version_label)

        # Donate button
        self.donate_btn = QPushButton("♥ DONATE")
        self.donate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.donate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ff5252;
                border: 1px solid #ff5252;
                border-radius: {self.s(4)}px;
                font-size: {self.s(11)}px;
                font-weight: bold;
                padding: {self.s(2)}px {self.s(8)}px;
            }}
            QPushButton:hover {{
                background-color: #ff5252;
                color: #ffffff;
            }}
        """)
        self.donate_btn.clicked.connect(self._on_donate_clicked)
        bottom_layout.addWidget(self.donate_btn)

        # Report a bug button
        self.report_bug_btn = QPushButton("REPORT A BUG")
        self.report_bug_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.report_bug_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #bbbbbb;
                border: 1px solid #bbbbbb;
                border-radius: {self.s(4)}px;
                font-size: {self.s(11)}px;
                font-weight: bold;
                padding: {self.s(2)}px {self.s(8)}px;
            }}
            QPushButton:hover {{
                background-color: #bbbbbb;
                color: #1e1e1e;
            }}
        """)
        self.report_bug_btn.clicked.connect(self._on_report_bug_clicked)
        bottom_layout.addWidget(self.report_bug_btn)

        # Check for updates button
        self.check_updates_btn = QPushButton("CHECK FOR UPDATES")
        self.check_updates_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_updates_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #bbbbbb;
                border: 1px solid #bbbbbb;
                border-radius: {self.s(4)}px;
                font-size: {self.s(11)}px;
                font-weight: bold;
                padding: {self.s(2)}px {self.s(8)}px;
            }}
            QPushButton:hover {{
                background-color: #bbbbbb;
                color: #1e1e1e;
            }}
        """)
        self.check_updates_btn.clicked.connect(
            lambda: self._safe_open_url("https://github.com/DOCKPORT/TallyBook/releases")
        )
        bottom_layout.addWidget(self.check_updates_btn)

        bottom_layout.addStretch()
        status_bar.addWidget(bottom_container)
        return status_bar

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------
    def _safe_open_url(self, url):
        """Opens a URL in the system browser while escaping AppImage isolation."""
        try:
            env = os.environ.copy()
            if "LD_LIBRARY_PATH" in env:
                del env["LD_LIBRARY_PATH"]
            subprocess.Popen(["xdg-open", url], env=env)
        except (FileNotFoundError, OSError):
            QDesktopServices.openUrl(QUrl(url))

    # ------------------------------------------------------------------
    # Report a bug dialog
    # ------------------------------------------------------------------
    def _on_report_bug_clicked(self):
        """Action when clicking the Report a Bug button."""
        win = self.main_window
        dialog = QDialog(win)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle("Report a Bug / Feedback")
        dialog.setFixedSize(win.s(640), win.s(280))
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #1e1e1e;
                border: 1px solid #ff9800;
                border-radius: {win.s(8)}px;
            }}
            QLabel {{
                color: #ffffff;
                font-family: 'Fira Code', monospace;
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(win.s(20), win.s(15), win.s(20), win.s(15))
        layout.setSpacing(win.s(10))

        message = QLabel(
            "Report any bugs or share your feedback to help us improve TallyBook!\n\n"
            f"Please include your version number ({APP_VERSION})."
        )
        message.setWordWrap(True)
        message.setStyleSheet(f"font-size: {win.s(15)}px; line-height: 1.4; color: #ffffff;")
        layout.addWidget(message)

        details_container = QWidget()
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(win.s(10))

        # GitHub link
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(win.s(8))

        lbl = QLabel("GitHub:")
        lbl.setStyleSheet(
            f"font-size: {win.s(15)}px; font-weight: bold; color: #ff9800; min-width: {win.s(80)}px;"
        )
        row_layout.addWidget(lbl)

        github_url = "https://github.com/DOCKPORT/TallyBook"
        link_label = QLabel(
            f'<a href="{github_url}" style="color: #58a6ff; text-decoration: none;">{github_url}</a>'
        )
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet(f"font-size: {win.s(14)}px; background: transparent;")
        row_layout.addWidget(link_label, 1)

        details_layout.addWidget(row_widget)

        # Email row
        email_row = QWidget()
        email_layout = QHBoxLayout(email_row)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.setSpacing(win.s(8))

        email_lbl = QLabel("Email:")
        email_lbl.setStyleSheet(
            f"font-size: {win.s(15)}px; font-weight: bold; color: #ff9800; min-width: {win.s(80)}px;"
        )
        email_layout.addWidget(email_lbl)

        email_address = "DOCKPORT_DEV@PROTONMAIL.COM"
        addr_field = QLineEdit(email_address)
        addr_field.setReadOnly(True)
        addr_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: {win.s(4)}px;
                padding: {win.s(6)}px;
                font-size: {win.s(14)}px;
                font-family: 'Fira Code', monospace;
            }}
        """)
        email_layout.addWidget(addr_field, 1)

        copy_btn = QPushButton("Copy")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setFixedWidth(win.s(75))
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: {win.s(4)}px;
                font-size: {win.s(12)}px;
                font-weight: bold;
                padding: {win.s(6)}px {win.s(12)}px;
            }}
            QPushButton:hover {{
                background-color: #4caf50;
                border-color: #4caf50;
            }}
        """)

        def on_copy():
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(email_address)
            copy_btn.setText("✅")
            copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2e7d32;
                    color: #ffffff;
                    border: 1px solid #1b5e20;
                    border-radius: {win.s(4)}px;
                    font-size: {win.s(12)}px;
                    font-weight: bold;
                    padding: {win.s(6)}px {win.s(12)}px;
                }}
            """)

            def reset_style():
                copy_btn.setText("Copy")
                copy_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #333333;
                        color: #ffffff;
                        border: 1px solid #555555;
                        border-radius: {win.s(4)}px;
                        font-size: {win.s(12)}px;
                        font-weight: bold;
                        padding: {win.s(6)}px {win.s(12)}px;
                    }}
                    QPushButton:hover {{
                        background-color: #4caf50;
                        border-color: #4caf50;
                    }}
                """)

            QTimer.singleShot(1000, reset_style)

        copy_btn.clicked.connect(on_copy)
        email_layout.addWidget(copy_btn)
        details_layout.addWidget(email_row)
        layout.addWidget(details_container)
        dialog.exec()

    # ------------------------------------------------------------------
    # Donate dialog
    # ------------------------------------------------------------------
    def _on_donate_clicked(self):
        """Action when clicking the Donate button."""
        win = self.main_window
        dialog = QDialog(win)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle("Support TallyBook")
        dialog.setFixedSize(win.s(850), win.s(410))
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #1e1e1e;
                border: 1px solid #ff9800;
                border-radius: {win.s(8)}px;
            }}
            QLabel {{
                color: #ffffff;
                font-family: 'Fira Code', monospace;
            }}
        """)

        from PySide6.QtWidgets import QApplication, QHBoxLayout

        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(win.s(20), win.s(20), win.s(20), win.s(20))
        main_layout.setSpacing(win.s(25))

        # Left side
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(win.s(12))

        message = QLabel(
            "If you find TallyBook useful, you can support its development!\n\n"
            "Your contributions help us build new features and improve stability."
        )
        message.setWordWrap(True)
        message.setStyleSheet(
            f"font-size: {win.s(15)}px; line-height: 1.4; color: #ffffff;"
        )
        left_layout.addWidget(message)

        details_container = QWidget()
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(win.s(10))

        def create_address_row(network, address):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(win.s(8))

            lbl = QLabel(f"{network}:")
            lbl.setStyleSheet(
                f"font-size: {win.s(15)}px; font-weight: bold; color: #ff9800; min-width: {win.s(80)}px;"
            )
            row_layout.addWidget(lbl)

            addr_field = QLineEdit(address)
            addr_field.setReadOnly(True)
            addr_field.setStyleSheet(f"""
                QLineEdit {{
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: {win.s(4)}px;
                    padding: {win.s(6)}px;
                    font-size: {win.s(14)}px;
                    font-family: 'Fira Code', monospace;
                }}
            """)
            row_layout.addWidget(addr_field, 1)

            copy_btn = QPushButton("Copy")
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setFixedWidth(win.s(75))
            copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #333333;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: {win.s(4)}px;
                    font-size: {win.s(12)}px;
                    font-weight: bold;
                    padding: {win.s(6)}px {win.s(12)}px;
                }}
                QPushButton:hover {{
                    background-color: #4caf50;
                    border-color: #4caf50;
                }}
            """)

            def on_copy():
                clipboard = QApplication.clipboard()
                clipboard.setText(address)
                copy_btn.setText("✅")
                copy_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #2e7d32;
                        color: #ffffff;
                        border: 1px solid #1b5e20;
                        border-radius: {win.s(4)}px;
                        font-size: {win.s(12)}px;
                        font-weight: bold;
                        padding: {win.s(6)}px {win.s(12)}px;
                    }}
                """)

                def reset_style():
                    copy_btn.setText("Copy")
                    copy_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #333333;
                            color: #ffffff;
                            border: 1px solid #555555;
                            border-radius: {win.s(4)}px;
                            font-size: {win.s(12)}px;
                            font-weight: bold;
                            padding: {win.s(6)}px {win.s(12)}px;
                        }}
                        QPushButton:hover {{
                            background-color: #4caf50;
                            border-color: #4caf50;
                        }}
                    """)

                QTimer.singleShot(1000, reset_style)

            copy_btn.clicked.connect(on_copy)
            row_layout.addWidget(copy_btn)
            return row_widget

        details_layout.addWidget(
            create_address_row("Bitcoin", "bc1qltty5ezggulw7nkl2dx3vmxvg6flyg5lajpjlp")
        )
        details_layout.addWidget(
            create_address_row("Solana", "2VQucWV3Qe99zKN8wZKfhrTH2YAfs3SCUk6oHr6eBYpF")
        )
        details_layout.addWidget(
            create_address_row("Contact", "DOCKPORT_DEV@PROTONMAIL.COM")
        )

        left_layout.addWidget(details_container)
        main_layout.addWidget(left_widget, 1)

        # Right side (QR codes)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(win.s(15))
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def create_qr_box(network_name, pixmap_path):
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(0, 0, 0, 0)
            box_layout.setSpacing(win.s(4))
            box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl = QLabel(f"{network_name} QR")
            lbl.setStyleSheet(
                f"font-size: {win.s(13)}px; font-weight: bold; color: #ff9800;"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box_layout.addWidget(lbl)

            qr_label = QLabel()
            pixmap = QPixmap(paths.resource_path(pixmap_path))
            if not pixmap.isNull():
                qr_label.setPixmap(
                    pixmap.scaled(
                        win.s(130), win.s(130),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                qr_label.setText("QR not found")
            qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box_layout.addWidget(qr_label)
            return box

        right_layout.addWidget(
            create_qr_box("Bitcoin", "assets/QR/BTC_QR.png")
        )
        right_layout.addWidget(
            create_qr_box("Solana", "assets/QR/SOL_QR.png")
        )

        main_layout.addWidget(right_widget)
        dialog.exec()