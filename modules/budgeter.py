"""Budgeter page module for TallyBook.

Provides the BudgeterPage widget: a projected-income planner with per-account
allocation spinboxes, percentage indicators, and an allocated/remaining summary.
"""
from color_system import color_for_percentage
from currency import format_percentage
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from scaling import scaled
from widgets import QuantitySpinBox


class BudgeterPage(QWidget):
    """Projected-income allocation planner with a per-account budget table."""

    def __init__(self, parent=None, scale_factor=1.0):
        super().__init__(parent)
        self.scale_factor = scale_factor
        self.s = lambda val: scaled(self.scale_factor, val)
        self.currency_symbol = "$"
        self.currency_decimals = 2
        self._is_built = False
        self.budget_inputs = {}

    def set_currency_settings(self, symbol, decimals):
        """Updates currency formatting for the income spinbox and allocation inputs."""
        self.currency_symbol = symbol
        self.currency_decimals = decimals

        if getattr(self, 'budget_income_spin', None):
            self.budget_income_spin.setPrefix(f"{symbol} ")
            self.budget_income_spin.setDecimals(decimals)

            for item in self.budget_inputs.values():
                if item and len(item) > 0:
                    spin = item[0]
                    spin.setPrefix(f"{symbol} ")
                    spin.setDecimals(decimals)

        self.update_chart()

    def build(self):
        """Builds the budgeter page UI. Call once before load_data."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        header = QLabel("Budget Planner")
        header.setStyleSheet(f"font-size: {self.s(20)}px; font-weight: bold; color: white; margin-bottom: {self.s(10)}px;")
        layout.addWidget(header)

        # Income Input
        income_container = QWidget()
        income_layout = QHBoxLayout(income_container)
        income_layout.setContentsMargins(0, 0, 0, 0)

        lbl_income = QLabel("Projected Income:")
        lbl_income.setStyleSheet(f"font-size: {self.s(16)}px; color: #cccccc;")

        self.budget_income_spin = QuantitySpinBox()
        self.budget_income_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.budget_income_spin.setRange(0.00, 1000000000000000.00)
        self.budget_income_spin.setDecimals(self.currency_decimals)
        self.budget_income_spin.setPrefix(f"{self.currency_symbol} ")
        self.budget_income_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                padding: {self.s(8)}px; 
                font-size: {self.s(16)}px; 
                background-color: #333; 
                color: white; 
                border: 1px solid #555; 
                border-radius: {self.s(4)}px;
            }}
        """)
        self.budget_income_spin.setFixedWidth(self.s(200))
        self.budget_income_spin.valueChanged.connect(self.update_chart)

        self.budget_income_spin.setSpecialValueText(" ")
        self.budget_income_spin.setValue(0.00)  # Reset to show blank

        income_layout.addWidget(lbl_income)
        income_layout.addWidget(self.budget_income_spin)
        income_layout.addStretch()
        layout.addWidget(income_container)

        # Summary Label
        self.budget_summary_lbl = QLabel(f"Allocated: {self.currency_symbol} 0.00 / Remaining: {self.currency_symbol} 0.00")
        self.budget_summary_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.budget_summary_lbl.setStyleSheet(f"font-size: {self.s(16)}px; font-weight: bold; color: white; margin: {self.s(10)}px 0;")
        layout.addWidget(self.budget_summary_lbl)

        # Table Frame
        table_frame = QFrame()
        table_frame.setStyleSheet(".QFrame { border: 1px solid #ff9800; border-radius: 4px; background-color: #2b2b2b; }")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(1, 1, 1, 1)

        # Accounts Table
        self.budget_table = QTableWidget()
        self.budget_table.setColumnCount(4)
        self.budget_table.setHorizontalHeaderLabels(["", "Account", "Allocation", "%"])
        self.budget_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.budget_table.setColumnWidth(0, self.s(40))
        self.budget_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.budget_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.budget_table.setColumnWidth(2, self.s(160))
        self.budget_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.budget_table.setColumnWidth(3, self.s(120))
        self.budget_table.verticalHeader().setVisible(False)
        self.budget_table.setAlternatingRowColors(True)
        self.budget_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.budget_table.setShowGrid(False)
        self.budget_table.verticalHeader().setDefaultSectionSize(self.s(50))
        self.budget_table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: #2b2b2b; 
                alternate-background-color: #383838; 
                border: none; 
                color: white; 
                font-size: {self.s(16)}px; 
                font-weight: bold;
            }}
            QHeaderView::section {{ 
                background-color: #2b2b2b; 
                color: white; 
                padding: {self.s(5)}px; 
                border: none;
                border-bottom: {self.s(2)}px solid #3d3d3d;
                font-size: {self.s(16)}px; 
            }}
            QTableWidget::item {{ padding: {self.s(10)}px; border: none; }}
            QTableWidget::item:hover {{ background-color: transparent; }}
            QScrollBar:vertical {{
                border: none;
                background: #2b2b2b;
                width: {self.s(6)}px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #555;
                min-height: {self.s(20)}px;
                border-radius: {self.s(3)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #666;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        table_layout.addWidget(self.budget_table)
        table_frame.setFixedWidth(self.s(750))
        layout.addWidget(table_frame, alignment=Qt.AlignmentFlag.AlignLeft)

        self.budget_inputs = {}  # acc_id -> (spinbox, pct_label, name)

    def load_data(self, cursor):
        """Loads accounts into the budgeter table using the given DB cursor."""
        self.budget_table.setRowCount(0)
        self.budget_inputs.clear()

        cursor.execute("SELECT id, name FROM accounts")
        accounts = cursor.fetchall()

        for acc_id, name in accounts:
            row = self.budget_table.rowCount()
            self.budget_table.insertRow(row)

            # Dot Label (Visual only)
            dot_label = QLabel("●")
            dot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot_label.setStyleSheet(f"color: #555555; font-size: {self.s(17)}px; background-color: transparent;")
            self.budget_table.setCellWidget(row, 0, dot_label)

            # Name
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.budget_table.setItem(row, 1, name_item)

            spin = QuantitySpinBox()
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setRange(0.00, 1000000000000000.00)
            spin.setDecimals(self.currency_decimals)
            spin.setPrefix(f"{self.currency_symbol} ")
            spin.setStyleSheet(f"background-color: #444; color: white; border: 1px solid #555; border-radius: {self.s(4)}px; font-size: {self.s(16)}px; padding: {self.s(5)}px;")
            spin.setSpecialValueText(" ")  # Make blank when 0
            spin.setValue(0.00)
            spin.valueChanged.connect(self.update_chart)
            self.budget_table.setCellWidget(row, 2, spin)

            pct_lbl = QLabel("0.00%")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pct_lbl.setStyleSheet(f"color: white; font-weight: bold; font-size: {self.s(16)}px; background-color: transparent; border: none;")
            self.budget_table.setCellWidget(row, 3, pct_lbl)

            self.budget_inputs[acc_id] = (spin, pct_lbl, name, dot_label, row)

        self.update_chart()

    def update_chart(self):
        """Updates the budget totals."""
        if not getattr(self, 'budget_income_spin', None):
            return

        income = self.budget_income_spin.value()
        total_allocated = 0.0

        # Calculate totals first for percentage accuracy
        for item in self.budget_inputs.values():
            spin = item[0]
            total_allocated += spin.value()

        remaining = income - total_allocated
        total_for_pct = income if income > 0 else (total_allocated if total_allocated > 0 else 1.0)

        # Update data for the table
        for item in self.budget_inputs.values():
            spin = item[0]
            pct_lbl = item[1]
            dot_label = item[3] if len(item) > 3 else None
            row = item[4] if len(item) > 4 else None

            val = spin.value()
            pct = (val / total_for_pct) * 100
            pct_lbl.setText(format_percentage(pct))  # Update table label

            accent_color = color_for_percentage(pct)

            if dot_label:
                dot_label.setStyleSheet(f"color: {accent_color}; font-size: {self.s(17)}px; background-color: transparent;")

            spin.setStyleSheet(f"background-color: #444; color: white; border: 1px solid #555; border-radius: {self.s(4)}px; font-size: {self.s(16)}px; padding: {self.s(5)}px;")
            pct_lbl.setStyleSheet(f"color: white; font-weight: bold; font-size: {self.s(16)}px; background-color: transparent; border: none;")

            if row is not None:
                name_item = self.budget_table.item(row, 1)
                if name_item:
                    name_item.setForeground(QColor("white"))

        # Update Summary Bar
        self.budget_summary_lbl.setText(f"Allocated: {self.currency_symbol} {total_allocated:,.{self.currency_decimals}f} / Remaining: {self.currency_symbol} {remaining:,.{self.currency_decimals}f}")
        if remaining < 0:
            self.budget_summary_lbl.setStyleSheet(f"font-size: {self.s(16)}px; font-weight: bold; color: #ff5252; margin: {self.s(10)}px 0;")
        else:
            self.budget_summary_lbl.setStyleSheet(f"font-size: {self.s(16)}px; font-weight: bold; color: white; margin: {self.s(10)}px 0;")


