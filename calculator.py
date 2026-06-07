import math
from asteval import Interpreter
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPlainTextEdit, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut


STYLESHEET_TEMPLATE = """
    QDialog {{
        background-color: #1a1a1a;
        border: {border}px solid #ff9800;
        border-radius: {radius}px;
    }}
    QLabel {{
        color: #ff9800;
        font-family: 'Fira Code', 'DejaVu Sans Mono', 'Ubuntu Mono', monospace;
        font-size: {label_font}px;
        font-weight: bold;
        border: none;
    }}
    QPlainTextEdit {{
        background-color: #121212;
        color: #ffffff;
        border: 1px solid #333;
        border-radius: {rounding}px;
        font-family: 'Fira Code', 'Courier New', 'DejaVu Sans Mono', monospace;
        font-size: {output_font}px;
        padding: {pad}px;
    }}
    QScrollBar:vertical {{
        border: none;
        background: #1a1a1a;
        width: {scroll_w}px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: #444;
        min-height: {scroll_h}px;
        border-radius: {scroll_r}px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #555;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    QLineEdit {{
        background-color: #2b2b2b;
        color: #ffffff;
        border: 1px solid #444;
        border-radius: {edit_r}px;
        font-family: 'Fira Code', 'DejaVu Sans Mono', 'Ubuntu Mono', monospace;
        font-size: {edit_font}px;
        padding: {edit_pad}px;
    }}
    QPushButton {{
        background-color: #333;
        color: #ff9800;
        border: 1px solid #ff9800;
        border-radius: {btn_r}px;
        font-weight: bold;
        padding: {btn_pad_v}px {btn_pad_h}px;
    }}
    QPushButton:hover {{
        background-color: #ff9800;
        color: #ffffff;
    }}
"""


BUILTIN_VARS = {
    'sqrt': math.sqrt, 'abs': abs, 'round': round,
    'pi': math.pi, 'e': math.e, 'pow': pow,
    'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
}


class CalculatorWindow(QDialog):
    """
    A standalone window for the Terminal Calculator.
    Uses asteval for safe math expression evaluation.
    """
    def __init__(self, parent=None, scale_factor=1.0):
        """Standalone Terminal Calculator Window."""
        super().__init__(parent)
        self.scale_factor = scale_factor
        self.s = lambda val: int(val * self.scale_factor)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("TallyBook")
        self.setMinimumSize(self.s(500), self.s(600))

        self._apply_stylesheet()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # History
        self.calc_history = QPlainTextEdit()
        self.calc_history.setReadOnly(True)
        self.layout.addWidget(self.calc_history)

        # Input Row
        input_container = QWidget()
        input_container.setStyleSheet("background: transparent; border: none;")
        input_row = QHBoxLayout(input_container)
        input_row.setContentsMargins(0, 0, 0, 0)

        self.prompt = QLabel("> ")
        self.calc_input = QLineEdit()
        self.calc_input.setPlaceholderText("Enter math (e.g. x=10)...")
        self.calc_input.returnPressed.connect(self._on_calc_enter)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setAutoDefault(False)
        self.clear_btn.setDefault(False)
        self.clear_btn.clicked.connect(self._clear_history)

        input_row.addWidget(self.prompt)
        input_row.addWidget(self.calc_input)
        input_row.addWidget(self.clear_btn)
        self.layout.addWidget(input_container)

        # Ctrl+L shortcut for Clear
        QShortcut(Qt.Key.Key_L | Qt.Modifier.CTRL, self, self._clear_history)

        # Safe math interpreter
        self.interp = Interpreter(usersyms=BUILTIN_VARS.copy())

        self.calc_history.appendPlainText("TallyBook terminal calculator")
        self.calc_history.appendPlainText("---")

    def _apply_stylesheet(self):
        s = self.s
        self.setStyleSheet(STYLESHEET_TEMPLATE.format(
            border=s(2), radius=s(12),
            label_font=s(20),
            output_font=s(18), pad=s(10),
            rounding=s(6),
            scroll_w=s(6), scroll_h=s(20), scroll_r=s(3),
            edit_font=s(20), edit_pad=s(8), edit_r=s(4),
            btn_r=s(4), btn_pad_v=s(8), btn_pad_h=s(15),
        ))

    def _clear_history(self):
        self.calc_history.clear()
        self.calc_history.appendPlainText("Terminal Reset")
        self.calc_history.appendPlainText("---")
        # Reset interpreter but keep builtins
        self.interp = Interpreter(usersyms=BUILTIN_VARS.copy())

    def _format_result(self, val: float | int) -> str:
        """Format a numeric result nicely."""
        if isinstance(val, float):
            return f"{val:g}"
        return str(val)

    def _on_calc_enter(self):
        text = self.calc_input.text().strip()
        if not text:
            return

        self.calc_history.appendPlainText(f"> {text}")

        # Special vars command
        if text.lower() == 'vars':
            user_vars = {
                k: v for k, v in self.interp.symtable.items()
                if not callable(v) and k != '__builtins__'
            }
            if user_vars:
                for k, v in user_vars.items():
                    self.calc_history.appendPlainText(f"  {k} = {self._format_result(v)}")
            else:
                self.calc_history.appendPlainText("  (No variables)")
            self.calc_input.clear()
            self.calc_input.setFocus()
            return

        try:
            # Handle percentage: convert standalone "50%" → "50/100"
            # but leave "10 % 3" (modulo) alone
            # Only match percent at end of a number
            import re
            processed = re.sub(r'(\d+(?:\.\d+)?)%', r'(\1)/100', text)

            result = self.interp(processed)

            # asteval returns None for assignment statements
            if result is None:
                # Check if this was an assignment by looking for '='
                if '=' in text:
                    var_name = text.split('=', 1)[0].strip()
                    if var_name in self.interp.symtable:
                        val = self.interp.symtable[var_name]
                        self.calc_history.appendPlainText(
                            f"  {var_name} = {self._format_result(val)}"
                        )
            else:
                self.calc_history.appendPlainText(f"  = {self._format_result(result)}")

        except Exception as e:
            msg = str(e)
            # Clean up asteval's verbose error messages
            if msg.startswith("NameError: name '") and msg.endswith("' is not defined"):
                # Already readable
                pass
            self.calc_history.appendPlainText(f"  Error: {msg}")

        self.calc_input.clear()
        self.calc_input.setFocus()
        self.calc_history.verticalScrollBar().setValue(
            self.calc_history.verticalScrollBar().maximum()
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.calc_input.setFocus()