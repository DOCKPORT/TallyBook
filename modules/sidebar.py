"""Sidebar module for TallyBook.

Provides the Sidebar widget (a QFrame) with navigation buttons.
Navigation and calculator requests are emitted as Qt signals so the
Sidebar stays decoupled from the main window.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout
from scaling import scaled


class Sidebar(QFrame):
    """Left navigation sidebar with page buttons and the calculator shortcut."""

    navigation_requested = Signal(int)
    calculator_requested = Signal()

    def __init__(self, parent=None, scale_factor=1.0):
        super().__init__(parent)
        self.scale_factor = scale_factor
        self.s = lambda val: scaled(self.scale_factor, val)
        self.nav_buttons = {}  # idx -> button

        self.setFixedWidth(self.s(120))
        self.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #3d3d3d;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Add Navigation Buttons
        buttons = ["Accounts", "Receipts", "Payments", "Transfers", "Analytics", "Budgeter", "Calculator", "Settings"]

        # Button Style with Borders and Hover Effects
        button_style = f"""
            QPushButton {{
                text-align: center;
                padding: {self.s(6)}px;
                border: 1px solid #444;
                border-radius: {self.s(4)}px;
                color: #ffffff;
                background-color: #333;
                margin-bottom: {self.s(5)}px;
            }}
            QPushButton:hover {{
                background-color: #444;
                border-color: #666;
            }}
            QPushButton:pressed {{
                background-color: #222;
            }}
            QPushButton[selected="true"] {{
                background-color: #666666;
                color: #ffffff;
                font-weight: bold;
                border-color: #888888;
            }}
        """

        for text in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(button_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            if text == "Calculator":
                btn.clicked.connect(self.calculator_requested)
            else:
                # We need to calculate the correct index for navigation pages
                # since "Calculator" is in the buttons list but not in the stacked widget pages
                nav_pages = ["Accounts", "Receipts", "Payments", "Transfers", "Analytics", "Budgeter", "Settings"]
                if text in nav_pages:
                    idx = nav_pages.index(text)
                    self.nav_buttons[idx] = btn
                    btn.clicked.connect(lambda checked, index=idx: self.navigation_requested.emit(index))

            layout.addWidget(btn)

    def set_selected_index(self, index):
        """Highlights the navigation button matching the given page index."""
        for idx, btn in self.nav_buttons.items():
            is_selected = (idx == index)
            btn.setProperty("selected", "true" if is_selected else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
