#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil
import sqlite3
import ledger_db
from version import APP_VERSION
from calculator import CalculatorWindow
from color_system import color_for_percentage
from scaling import calculate_scale_factor, scaled
import CSV_EXPORTER as csv_exporter
import backup_exporter
from currency import format_number_as_currency, format_percentage, to_internal, from_internal
import paths
import dialogs
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QStatusBar,
    QFrame,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QAbstractItemView,
    QDialog,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
    QDoubleSpinBox,
    QDateEdit,
    QAbstractSpinBox,
    QCheckBox,
    QScrollArea,
    QGridLayout,
    QSpinBox,
    QToolTip,
    QFileDialog,
    QSizePolicy,
    QSplitter,
    QListView,
    QCalendarWidget,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QDate, QDateTime, QUrl, QRect, QRectF, QPointF, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import (
    QColor, QPainter, QPen, QCursor, QDesktopServices, 
    QLinearGradient, QPainterPath, QIcon, QFont, QPixmap
)
from PySide6.QtCharts import QChart, QChartView, QValueAxis, QBarSeries, QBarSet, QBarCategoryAxis

class QuantitySpinBox(QDoubleSpinBox):
    """Custom SpinBox that displays integers with thousands separator commas and handles negative zero."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDecimals(6)

    def textFromValue(self, value):
        # Handle zero if special value text is requested to be blank
        if self.specialValueText() and abs(value) < 1e-9:
            return ""
            
        # Handle negative zero for display
        if abs(value) < 1e-9:  # Treat very small numbers as zero
            return "0" if self.decimals() == 0 else f"0.{'0' * self.decimals()}"
        
        # Format the number with commas
        if value == int(value):
            return f"{int(value):,}"
            
        formatted = f"{value:,.{self.decimals()}f}"
        if '.' in formatted:
            parts = formatted.split('.')
            integer_part = parts[0]
            decimal_part = parts[1].rstrip('0').rstrip('.')
            if decimal_part:
                return f"{integer_part}.{decimal_part}"
            else:
                return integer_part
        return formatted

    def valueFromText(self, text):
        clean_text = text.replace(",", "")
        if self.prefix():
            clean_text = clean_text.replace(self.prefix(), "")
        if self.suffix():
            clean_text = clean_text.replace(self.suffix(), "")
        clean_text = clean_text.strip()
        try:
            return float(clean_text)
        except ValueError:
            return 0.0

    def validate(self, input_str, pos):
        clean_text = input_str.replace(",", "")
        if self.prefix():
            clean_text = clean_text.replace(self.prefix(), "")
        if self.suffix():
            clean_text = clean_text.replace(self.suffix(), "")
        clean_text = clean_text.strip()
        if not clean_text:
            from PySide6.QtGui import QValidator
            return QValidator.State.Acceptable, input_str, pos
        return super().validate(input_str, pos)

    def focusOutEvent(self, event):
        text = self.lineEdit().text()
        clean_text = text.replace(",", "")
        if self.prefix():
            clean_text = clean_text.replace(self.prefix(), "")
        if self.suffix():
            clean_text = clean_text.replace(self.suffix(), "")
        clean_text = clean_text.strip()
        if not clean_text:
            self.setValue(0.0)
        super().focusOutEvent(event)



class ModernDateEdit(QDateEdit):
    """Custom QDateEdit with a sleek, modern dark-themed calendar popup."""
    def __init__(self, parent=None, scale_factor=1.0):
        super().__init__(parent)
        self.scale_factor = scale_factor
        self.s = lambda val: scaled(self.scale_factor, val)
        self.setCalendarPopup(True)
        self._style_calendar()

    def _style_calendar(self):
        calendar = self.calendarWidget()
        if not calendar:
            return
            
        calendar.setNavigationBarVisible(True)
        calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        
        # Modern dark theme for the calendar
        calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: #1e1e1e;
                border: none;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: #2b2b2b;
                border: 2px solid #666;
                border-bottom: none;
            }}
            QCalendarWidget QAbstractItemView {{
                border: 2px solid #666;
                border-top: none;
                background-color: #1e1e1e;
            }}
            QCalendarWidget QToolButton {{
                color: white;
                background-color: transparent;
                border: none;
                font-size: {self.s(14)}px;
                font-weight: bold;
                padding: {self.s(4)}px;
                margin: {self.s(2)}px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: #444;
                border-radius: {self.s(4)}px;
            }}
            QCalendarWidget QToolButton#qt_calendar_prevmonth {{
                qproperty-icon: none;
                qproperty-text: "<";
            }}
            QCalendarWidget QToolButton#qt_calendar_nextmonth {{
                qproperty-icon: none;
                qproperty-text: ">";
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: #1e1e1e;
                color: #ddd;
                selection-background-color: #ff9800;
                selection-color: black;
                font-size: {self.s(13)}px;
                outline: none;
            }}
            QCalendarWidget QAbstractItemView::item:hover:!selected {{
                background-color: #333;
                border-radius: {self.s(4)}px;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: #444;
            }}
            QCalendarWidget QMenu {{
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #444;
                font-size: {self.s(14)}px;
            }}
            QCalendarWidget QMenu::item:selected {{
                background-color: #ff9800;
                color: black;
            }}
            QCalendarWidget QHeaderView {{
                background-color: #1e1e1e;
            }}
            QCalendarWidget QHeaderView::section {{
                background-color: #1e1e1e;
                color: #ff9800;
                padding: {self.s(2)}px;
                border: none;
                font-weight: bold;
            }}
        """)


class ModernTooltip(QWidget):
    """A sleek, modern tooltip for charts and other elements."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.frame = QFrame()
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel()
        self.frame_layout.addWidget(self.label)
        self.main_layout.addWidget(self.frame)
        self.hide()

    def show_at(self, pos, text, scale_factor=1.0):
        self.label.setText(text)
        self.frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(43, 43, 43, 245);
                border: 1px solid white;
                border-radius: {scaled(scale_factor, 8)}px;
            }}
        """)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: white;
                padding: {scaled(scale_factor, 10)}px;
                font-family: 'Fira Code', monospace;
                font-size: {scaled(scale_factor, 14)}px;
                background: transparent;
                border: none;
            }}
        """)
        self.adjustSize()
        
        # Calculate screen boundaries to prevent going off-screen
        screen = QApplication.primaryScreen().geometry()
        
        # Position centered above the target point
        x = pos.x() - self.width() // 2
        y = pos.y() - self.height() - 10 # 10px gap
        
        # Boundary checks to prevent going off-screen
        if x < 0:
            x = 10
        if x + self.width() > screen.right():
            x = screen.right() - self.width() - 10
            
        if y < 0:
            # If no space above, show below the point
            y = pos.y() + 20
            
        self.move(x, y)
        self.show()
        self.raise_()

class TransactionItemTable(QWidget):
    def __init__(self, parent=None, editable=True, currency_formatter=None, scale_factor=1.0):
        super().__init__(parent)
        self.editable = editable
        self.scale_factor = scale_factor
        self.s = lambda val: scaled(self.scale_factor, val)
        self.currency_symbol = "$"
        self.currency_decimals = 2
        self.currency_formatter = currency_formatter # Store the formatter function
        self._setup_ui()

    def _get_bold_font(self):
        """Helper to get a bold font object."""
        font = self.font()
        font.setPixelSize(self.s(16))
        font.setBold(True)
        return font

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Enable Quantity (Top)
        top_layout = QHBoxLayout()
        top_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        top_layout.setContentsMargins(0, 0, 0, 5)
        self.enable_qty_cb = QCheckBox("Enable Quantity")
        self.enable_qty_cb.setChecked(False)
        self.enable_qty_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.enable_qty_cb.setStyleSheet(f"color: #ffffff; font-size: {self.s(16)}px;")
        self.enable_qty_cb.stateChanged.connect(self._toggle_quantity_column)
        top_layout.addWidget(self.enable_qty_cb)
        layout.addLayout(top_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Item", "Quantity", "Unit Price", "Total", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, self.s(30))
        
        # Set fixed widths for numeric columns to ensure headers fit
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, self.s(100)) # Quantity
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, self.s(125)) # Unit Price
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, self.s(125)) # Total
        
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: #333; color: white; border: none; font-size: {self.s(16)}px; }}
            QHeaderView::section {{ background-color: #444; color: white; padding: {self.s(4)}px; border: 1px solid #555; font-size: {self.s(16)}px; }}
        """)

        # Frame for Table
        table_frame = QFrame()
        table_frame.setStyleSheet(".QFrame { border: 1px solid #ff9800; border-radius: 4px; }")
        frame_layout = QVBoxLayout(table_frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.setSpacing(0)
        frame_layout.addWidget(self.table)

        # Add Row Buttons (Inside Frame)
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(0)
        btns_layout.setContentsMargins(0, 0, 0, 0)

        self.add_row_btn = QPushButton("+ Add Item")
        self.add_row_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_row_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #333; color: #aaaaaa; border: none; border-top: 1px solid #555;
                padding: {self.s(12)}px; font-weight: bold; border-right: 1px solid #555;
            }}
            QPushButton:hover {{ background-color: #444; color: white; }}
        """)
        self.add_row_btn.clicked.connect(lambda: self.add_row())
        btns_layout.addWidget(self.add_row_btn)

        self.add_5_btn = QPushButton("+ Add 5 Items")
        self.add_5_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_5_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #333; color: #aaaaaa; border: none; border-top: 1px solid #555;
                padding: {self.s(12)}px; font-weight: bold; border-right: 1px solid #555;
            }}
            QPushButton:hover {{ background-color: #444; color: white; }}
        """)
        self.add_5_btn.clicked.connect(lambda: [self.add_row() for _ in range(5)])
        btns_layout.addWidget(self.add_5_btn)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #333; color: #ff5252; border: none; border-top: 1px solid #555;
                padding: {self.s(12)}px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #444; color: #ff8a80; }}
        """)
        self.clear_all_btn.clicked.connect(self.clear_table)
        btns_layout.addWidget(self.clear_all_btn)

        frame_layout.addLayout(btns_layout)

        layout.addWidget(table_frame)

        self.set_editable(self.editable)
        self._toggle_quantity_column()

    def set_editable(self, editable):
        self.editable = editable
        self.add_row_btn.setVisible(editable)
        self.add_5_btn.setVisible(editable)
        self.clear_all_btn.setVisible(editable)
        self.enable_qty_cb.setVisible(editable)
        self.table.setColumnHidden(4, not editable)
        # Refresh rows to apply editable state
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == "TOTAL_ROW":
                continue # Skip total row
            
            desc_item = self.table.item(row, 0)
            if desc_item:
                if not editable:
                    desc_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                else:
                    desc_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)

            qty_widget = self.table.cellWidget(row, 1)
            if qty_widget:
                qty_widget.setReadOnly(not editable)
            
            price_widget = self.table.cellWidget(row, 2)
            if price_widget:
                price_widget.setReadOnly(not editable)

            del_widget = self.table.cellWidget(row, 4)
            if del_widget:
                del_widget.setVisible(editable)

    def clear_table(self):
        self.table.setRowCount(0)
        if self.editable:
            self.add_row()
        self.update_total()
        import gc
        gc.collect()

    def set_rows(self, items, editable=True):
        self.table.setRowCount(0)
        self.set_editable(editable)
        for item in items:
            self.add_row(
                desc=item.get('description', ''),
                qty=item.get('quantity', 1.0),
                price=item.get('price', 0.0)
            )
        if not items and editable:
            self.add_row() # Add one empty row if list is empty and editable
        self.update_total()

    def _toggle_quantity_column(self):
        if self.enable_qty_cb.isChecked():
            self.table.showColumn(1)
            item = self.table.horizontalHeaderItem(2)
            if item:
                item.setText("Unit Price")
        else:
            self.table.hideColumn(1)
            item = self.table.horizontalHeaderItem(2)
            if item:
                item.setText("Amount")
        self.update_total()

    def add_row(self, desc="", qty=1.0, price=0.0):
        row_count = self.table.rowCount()
        insert_row = row_count
        
        if row_count > 0:
            item = self.table.item(row_count - 1, 0)
            if item and item.data(Qt.UserRole) == "TOTAL_ROW":
                insert_row = row_count - 1
        
        self.table.insertRow(insert_row)
        row = insert_row

        desc_item = QTableWidgetItem(desc)
        if not self.editable:
            desc_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.table.setItem(row, 0, desc_item)
        
        qty_spin = QuantitySpinBox()
        qty_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        qty_spin.setRange(0.00, 1000000000.0)
        qty_spin.setValue(qty)
        qty_spin.setStyleSheet(f"background-color: #555; color: white; border: none; font-size: {self.s(16)}px;")
        qty_spin.setReadOnly(not self.editable)
        qty_spin.valueChanged.connect(self.update_total)
        self.table.setCellWidget(row, 1, qty_spin)
        
        price_spin = QuantitySpinBox()
        price_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        price_spin.setRange(0.00, 1000000000000000.00)
        price_spin.setSpecialValueText(" ")
        price_spin.setValue(price)
        price_spin.setStyleSheet(f"background-color: #555; color: white; border: none; font-size: {self.s(16)}px;")
        price_spin.setReadOnly(not self.editable)
        price_spin.valueChanged.connect(self.update_total)
        self.table.setCellWidget(row, 2, price_spin)

        total_item = QTableWidgetItem("0.00")
        total_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, 3, total_item)

        if self.editable:
            del_btn = QPushButton("X")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("background-color: transparent; color: #d32f2f; border: none; font-weight: bold;")
            del_btn.clicked.connect(self._delete_row)
            self.table.setCellWidget(row, 4, del_btn)
        else:
            # Add a placeholder so column isn't empty
            placeholder = QWidget()
            placeholder.setFixedWidth(self.s(30))
            self.table.setCellWidget(row, 4, placeholder)
        
        self.update_total()

    def _delete_row(self):
        button = self.sender()
        if button:
            index = self.table.indexAt(button.pos())
            if index.isValid():
                self.table.removeRow(index.row())
                self.update_total()

    def update_total(self):
        grand_total = 0.0
        row_count = self.table.rowCount()
        
        has_total_row = False
        if row_count > 0:
            item = self.table.item(row_count - 1, 0)
            if item and item.data(Qt.UserRole) == "TOTAL_ROW":
                has_total_row = True
        
        limit = row_count - 1 if has_total_row else row_count
        
        for row in range(limit):
            qty_widget = self.table.cellWidget(row, 1)
            price_widget = self.table.cellWidget(row, 2)
            
            if qty_widget and price_widget:
                if self.enable_qty_cb.isChecked():
                    qty = qty_widget.value()
                else:
                    qty = 1.0
                price = price_widget.value()
                row_total = qty * price
                
                total_item = self.table.item(row, 3)
                if total_item and self.currency_formatter:
                    total_item.setText(self.currency_formatter(row_total, include_symbol=False))
                
                grand_total += row_total
                
        total_text = self.currency_formatter(grand_total) if self.currency_formatter else f"{self.currency_symbol} {grand_total:,.{self.currency_decimals}f}"

        if not has_total_row:
            self.table.insertRow(row_count)
            total_row = row_count
            
            item = QTableWidgetItem(total_text)
            item.setFont(self._get_bold_font()) # Font is fine
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setForeground(QColor("white"))
            item.setData(Qt.UserRole, "TOTAL_ROW")
            self.table.setItem(total_row, 0, item)
            self.table.setSpan(total_row, 0, 1, 5)
        else:
            total_row = row_count - 1
            item = self.table.item(total_row, 0)
            item.setText(total_text)
            
        return grand_total # This return value is used by TallyBookWindow, so it should be the raw number

    def set_currency_settings(self, symbol, decimals, formatter_func):
        self.currency_symbol = symbol
        self.currency_decimals = decimals
        self.currency_formatter = formatter_func
        
        # Update existing rows
        # We don't update price_widget decimals here because Unit Price should not be limited by preference (uses 6)
        
        self.update_total()

    def get_total(self):
        return self.update_total()

    def get_items(self):
        items = []
        row_count = self.table.rowCount()
        limit = row_count
        if row_count > 0:
            item = self.table.item(row_count - 1, 0)
            if item and item.data(Qt.UserRole) == "TOTAL_ROW":
                limit = row_count - 1

        for row in range(limit):
            desc_item = self.table.item(row, 0)
            description = desc_item.text() if desc_item else ""
            
            qty_widget = self.table.cellWidget(row, 1)
            price_widget = self.table.cellWidget(row, 2)
            
            if self.enable_qty_cb.isChecked():
                quantity = qty_widget.value() if qty_widget else 0.0
            else:
                quantity = 1.0
            
            unit_price = price_widget.value() if price_widget else 0.0
            line_total = quantity * unit_price

            items.append({
                'description': description,
                'quantity': quantity,
                'price': unit_price,
                'total': line_total
            })
        return items

class SankeyWidget(QWidget):
    """
    A custom widget to render a Sankey-style flow chart.
    """
    def __init__(self, parent=None, scale_factor=1.0):
        super().__init__(parent)
        self.scale_factor = scale_factor
        self.s = lambda val: scaled(self.scale_factor, val)
        self.setMinimumHeight(self.s(300))
        self.data = []  # List of (account_name, volume)
        self.total_receipts = 0.0
        self.currency_symbol = "$"
        self.currency_decimals = 2
        self.setMouseTracking(True)
        self.source_label_rect = QRect()
        self.account_zones = []  # List of (QRect, name, volume_str)
        self.selected_account = None

    def _format_percentage(self, value):
        """Formats a numeric value as a percentage string, handling negative zero."""
        return format_percentage(value)

    def setData(self, total_receipts, account_data, symbol, decimals):
        self.total_receipts = total_receipts
        self.data = account_data
        self.currency_symbol = symbol
        self.currency_decimals = decimals
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        # Update cursor if hovering over interactive zones
        is_hovering = self.source_label_rect.contains(pos)
        if not is_hovering:
            for rect, _, _ in self.account_zones:
                if rect.contains(pos):
                    is_hovering = True
                    break
        self.setCursor(Qt.CursorShape.PointingHandCursor if is_hovering else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            clicked_account = None
            for rect, name, _ in self.account_zones:
                if rect.contains(pos):
                    clicked_account = name
                    break
            
            # Toggle selection if clicking the same one, otherwise select new, or clear if clicking empty space
            if clicked_account:
                self.selected_account = None if self.selected_account == clicked_account else clicked_account
            else:
                self.selected_account = None
            self.update()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        margin_left = self.s(5)
        margin_right = self.s(180)
        margin_top = self.s(20)
        margin_bottom = self.s(40)

        # Sort all data
        data = sorted(self.data, key=lambda x: x[1], reverse=True)
        
        total_payment_volume = sum(v for _, v in data)

        if not data:
            painter.setPen(QColor("#888888"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No account data available")
            return

        # Positions
        source_x = margin_left
        target_x = rect.width() - margin_right
        
        available_height = rect.height() - margin_top - margin_bottom
        
        source_y = margin_top
        source_h = available_height
        
        # Label for Source (Inline, Bold, White)
        painter.setPen(QColor("white"))
        font = QFont("Fira Code")
        font.setBold(True)
        font.setPointSize(self.s(20))
        painter.setFont(font)
        metrics = painter.fontMetrics()
        
        full_source_label = ""
        
        # Calculate tight bounding rect for the icon for better hover detection
        icon_width = metrics.horizontalAdvance(full_source_label)
        icon_height = metrics.height()
        icon_x = source_x - 10 - icon_width
        icon_y = int(source_y + (source_h - icon_height) / 2)
        self.source_label_rect = QRect(icon_x, icon_y, icon_width, icon_height)
        
        painter.drawText(self.source_label_rect, Qt.AlignmentFlag.AlignCenter, full_source_label)

        # Draw Targets and Flows
        gap = 15
        total_gaps = (len(data) - 1) * gap
        available_target_height = available_height - total_gaps
        
        current_target_y = margin_top
        current_source_flow_y = source_y
        self.account_zones = []
        
        for name, volume in data:
            # Calculate heights
            if total_payment_volume > 0:
                target_h = max(2, (volume / total_payment_volume) * available_target_height)
                flow_h = max(1, (volume / total_payment_volume) * source_h)
            else:
                target_h = available_target_height / len(data)
                flow_h = source_h / len(data)

            # Flow Path (Bezier)
            path = QPainterPath()
            path.moveTo(source_x, current_source_flow_y)
            
            # Control points for smooth curve
            cp1_x = source_x + (target_x - source_x) / 2
            arrow_w = max(5, min(20, target_h))
            
            path.cubicTo(
                cp1_x, current_source_flow_y,
                cp1_x, current_target_y,
                target_x - arrow_w, current_target_y
            )
            path.lineTo(target_x, current_target_y + target_h / 2)
            path.lineTo(target_x - arrow_w, current_target_y + target_h)
            path.cubicTo(
                cp1_x, current_target_y + target_h,
                cp1_x, current_source_flow_y + flow_h,
                source_x, current_source_flow_y + flow_h
            )
            path.closeSubpath()
            
            # Determine color based on % (Centralized source of truth)
            pct = (volume / self.total_receipts * 100) if self.total_receipts > 0 else 0.0
            accent_color = color_for_percentage(pct)

            # Flow Gradient (Black to dynamic accent color)
            flow_gradient = QLinearGradient(source_x, 0, target_x, 0)
            if volume > 0:
                c2 = QColor(accent_color)
                c1 = c2.darker(180)  # Same color but darker
            else:
                c1 = QColor("#555555")  # Muted Grey for 0 volume
                c2 = QColor("#444444")  # Muted Grey for 0 volume
            
            # Adjust alpha based on selection
            if self.selected_account:
                if self.selected_account == name:
                    alpha = 210 # Highlight selected
                else:
                    alpha = 30  # Dim others
            else:
                alpha = 90      # Default

            c1.setAlpha(alpha)
            c2.setAlpha(alpha)
            
            flow_gradient.setColorAt(0.0, c1)
            flow_gradient.setColorAt(0.10, c2)
            flow_gradient.setColorAt(1.0, c2)
            
            # Wider border for the flow definition
            border_pen = QPen(QColor(255, 255, 255, 60), 1.0)
            painter.setPen(border_pen)
            
            painter.setBrush(flow_gradient)
            painter.drawPath(path)
            
            # Target Label
            if volume > 0:
                painter.setPen(QColor("#eeeeee"))
            else:
                painter.setPen(QColor("#777777")) # Muted grey for text
            font = QFont("Fira Code")
            font.setBold(True)
            font.setPointSize(self.s(10))
            painter.setFont(font)
            
            # pct already calculated above
            label_text = f"{name} {self._format_percentage(pct)}"
            label_vol = f"{self.currency_symbol} {volume:,.{self.currency_decimals}f}"
            
            # Measure label and elide if necessary to prevent going off-screen
            metrics = painter.fontMetrics()
            max_label_w = margin_right - 20 # Leave a small buffer at the very edge
            elided_label = metrics.elidedText(label_text, Qt.TextElideMode.ElideRight, max_label_w)
            
            # Draw name and %, centered vertically relative to the flow path
            label_y = int(current_target_y + target_h/2 + 4)
            label_x = target_x + 10
            
            # Measure label for hit zone
            label_rect = QRect(label_x, label_y - metrics.height(), metrics.horizontalAdvance(elided_label), metrics.height() + 5)
            self.account_zones.append((label_rect, name, label_vol))
            
            painter.drawText(label_x, label_y, elided_label)
            
            # Draw detailed overlay if selected
            if self.selected_account == name:
                # Calculate center of the flow curve
                mid_x = source_x + (target_x - source_x) / 2
                # Average of source center Y and target center Y
                source_center_y = current_source_flow_y + flow_h / 2
                target_center_y = current_target_y + target_h / 2
                mid_y = (source_center_y + target_center_y) / 2
                
                overlay_text = f"{self._format_percentage(pct)} • {label_vol}"
                
                overlay_font = QFont("Fira Code")
                overlay_font.setPointSize(self.s(10))
                overlay_font.setBold(True)
                painter.setFont(overlay_font)
                metrics_ov = painter.fontMetrics()
                ov_w = metrics_ov.horizontalAdvance(overlay_text)
                ov_h = metrics_ov.height()
                
                bg_rect = QRectF(mid_x - ov_w/2 - 8, mid_y - ov_h/2 - 4, ov_w + 16, ov_h + 8)
                painter.setBrush(QColor(0, 0, 0, 200))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bg_rect, 6, 6)
                
                painter.setPen(QColor("#ffffff"))
                painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, overlay_text)
            
            current_target_y += target_h + gap
            current_source_flow_y += flow_h


class TallyBookWindow(QMainWindow):
    """
    The main application window for TallyBook.
    Inherits from QMainWindow to provide a standard application layout
    (Menu bar, Status bar, Central widget area).
    """
    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'calc_input'):
            self.calc_input.setFocus()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not hasattr(self, '_fade_in_done'):
            self._fade_in_done = True
            QTimer.singleShot(100, self.start_fade_in)



    def start_fade_in(self):
        if hasattr(self, 'page_opacity_effect'):
            self.fade_animation = QPropertyAnimation(self.page_opacity_effect, b"opacity")
            self.fade_animation.setDuration(1000)
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.fade_animation.start()

    def __init__(self):
        super().__init__()

        # 1. Window Configuration
        self.setWindowTitle("TallyBook")
        
        # Calculate scale factor based on screen resolution
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        # Base scale on 1920x1080 as reference
        self.scale_factor = calculate_scale_factor(screen_geometry.width(), screen_geometry.height())
        
        self.resize(scaled(self.scale_factor, 1000), scaled(self.scale_factor, 700))
        
        # Set Application Icon
        self.setWindowIcon(QIcon(paths.resource_path("tallybook_app_icon.png")))

        # Scaling Helper
        self.s = lambda val: scaled(self.scale_factor, val)
        
        # Initialize Database
        self._init_database()
        self.current_edit_id = None
        self.current_view_account_id = None
        self.current_edit_tx_id = None
        self.calculator_window = None
        self.modern_tooltip = ModernTooltip(self)
        
        # Apply Dark Mode Stylesheet with global Fira Code font
        self.setStyleSheet(f"""
            * {{ font-family: 'Fira Code', 'DejaVu Sans Mono', monospace; font-size: {scaled(self.scale_factor, 12)}px; }}
            QMainWindow {{ background-color: #1e1e1e; color: #ffffff; }}
            QWidget {{ background-color: #1e1e1e; color: #ffffff; }}
        """)
        QToolTip.setFont(QFont("Fira Code", scaled(self.scale_factor, 10)))

        # 2. Setup the Central Widget
        # QMainWindow needs a central widget to hold the layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 3. Setup Layout
        # Use Horizontal Layout to hold Sidebar (Left) and Content (Right)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Setup Content Area (Stacked Widget)
        self.stacked_widget = QStackedWidget()
        self.page_opacity_effect = QGraphicsOpacityEffect(self.stacked_widget)
        self.page_opacity_effect.setOpacity(0.0)
        self.stacked_widget.setGraphicsEffect(self.page_opacity_effect)

        # Add Sidebar
        self.sidebar = self._create_sidebar()
        self.main_layout.addWidget(self.sidebar)

        # Add Content Area to Layout
        self.main_layout.addWidget(self.stacked_widget)

        # 4. Initialize Pages
        self._create_pages()
        self._apply_currency_settings()

        # 5. Setup UI Elements (Status Bar, Menus, etc.)
        self._create_status_bar()
        
        self.stacked_widget.currentChanged.connect(self._on_page_changed)
        self._on_page_changed(0) # Trigger initial highlight and load data

    def _format_number_as_currency(self, value, include_symbol=True):
        """Formats a numeric value as a currency string, handling negative zero."""
        return format_number_as_currency(value, self.currency_symbol, self.currency_decimals, include_symbol)

    def _format_percentage(self, value):
        """Formats a numeric value as a percentage string, handling negative zero."""
        return format_percentage(value)

    def _show_modern_message(self, title, text, icon_type=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok):
        """Shows a styled QMessageBox without standard OS button icons."""
        return dialogs.show_modern_message(self, title, text, icon_type, buttons, self.scale_factor)

    def _show_modern_input(self, title, label, text=""):
        """Shows a styled QInputDialog without standard OS button icons."""
        return dialogs.show_modern_input(self, title, label, text, self.scale_factor)

    def _create_sidebar(self):
        """Creates the left sidebar with navigation buttons."""
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(self.s(120)) 
        self.sidebar.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #3d3d3d;")
        
        layout = QVBoxLayout(self.sidebar)
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

        self.nav_buttons = {} # idx -> button

        for i, text in enumerate(buttons):
            btn = QPushButton(text)
            btn.setStyleSheet(button_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            if text == "Calculator":
                btn.clicked.connect(self._show_calculator_window)
            else:
                # We need to calculate the correct index for navigation pages
                # since "Calculator" is in the buttons list but not in the stacked widget pages
                nav_pages = ["Accounts", "Receipts", "Payments", "Transfers", "Analytics", "Budgeter", "Settings"]
                if text in nav_pages:
                    idx = nav_pages.index(text)
                    self.nav_buttons[idx] = btn
                    btn.clicked.connect(lambda checked, index=idx: self.stacked_widget.setCurrentIndex(index))
            
            layout.addWidget(btn)
            
        return self.sidebar

    def resizeEvent(self, event):
        """Handle adaptive UI scaling on window resize."""
        super().resizeEvent(event)
        width = self.width()
        
        # 1. Adjust Sidebar (Thinner look if too narrow)
        if hasattr(self, 'sidebar'):
            if width < self.s(1100):
                self.sidebar.setFixedWidth(self.s(60))
            else:
                self.sidebar.setFixedWidth(self.s(120))

        # 2. Adjust Accounts Page Splitter
        if hasattr(self, 'accounts_splitter'):
            if width < 1000:
                self.accounts_splitter.setOrientation(Qt.Orientation.Vertical)
            else:
                self.accounts_splitter.setOrientation(Qt.Orientation.Horizontal)

    def _to_internal(self, amount_float):
        """Converts a UI float to a database integer (cents)."""
        return to_internal(amount_float)

    def _from_internal(self, amount_int):
        """Converts a database integer (cents) to a UI float."""
        return from_internal(amount_int)

    def _init_database(self):
        """Initializes the SQLite database via the external backend module."""
        self.db = ledger_db.LedgerDB()
        self.db_path = self.db.db_path
        self.conn = self.db.conn
        self.cursor = self.db.cursor
        self._load_app_settings()

    def _ensure_setting(self, key, default_value):
        self.db.ensure_setting(key, default_value)

    def _load_app_settings(self):
        self.currency_symbol = self.db.get_setting('currency_symbol', '$')
        self.currency_decimals = int(self.db.get_setting('currency_decimals', '2'))
        self._apply_currency_settings()


    def _apply_currency_settings(self):
        """Propagates currency settings to all relevant components."""
        # Update TransactionItemTables if they exist
        if hasattr(self, 'receipt_item_table'): # Pass the formatter function
            self.receipt_item_table.set_currency_settings(self.currency_symbol, self.currency_decimals, self._format_number_as_currency)
        if hasattr(self, 'payment_item_table'): # Pass the formatter function
            self.payment_item_table.set_currency_settings(self.currency_symbol, self.currency_decimals, self._format_number_as_currency)
        if hasattr(self, 'tx_item_table'): # Pass the formatter function
            self.tx_item_table.set_currency_settings(self.currency_symbol, self.currency_decimals, self._format_number_as_currency)
            
        # Update Budgeter Page widgets if they exist
        if hasattr(self, 'budget_income_spin'):
            self.budget_income_spin.setPrefix(f"{self.currency_symbol} ")
            self.budget_income_spin.setDecimals(self.currency_decimals)
            
        if hasattr(self, 'budget_inputs'):
            for acc_id, item in self.budget_inputs.items():
                if item and len(item) > 0:
                    spin = item[0]
                    spin.setPrefix(f"{self.currency_symbol} ")
                    spin.setDecimals(self.currency_decimals)

        if hasattr(self, 'axis_y'):
            self.axis_y.setTitleVisible(False)
                
        # If any page is currently visible, refresh it
        if hasattr(self, 'stacked_widget'):
            idx = self.stacked_widget.currentIndex()
            if idx >= 0:
                self._on_page_changed(idx)

    def _load_accounts(self):
        """Loads accounts from the database into the table."""
        self.accounts_table.setRowCount(0)
        
        raw_accounts_data = self.db.get_accounts()
        accounts_data = [(acc[0], acc[1], self._from_internal(acc[2])) for acc in raw_accounts_data]
        total_balance = sum(acc[2] for acc in accounts_data)

        
        # Add Total Row at the TOP of the table
        self.accounts_table.insertRow(0)
        total_label_item = QTableWidgetItem("Total Balance")
        total_font = self._get_bold_font()
        total_label_item.setFont(total_font)
        self.accounts_table.setItem(0, 1, total_label_item)
        
        total_val_text = self._format_number_as_currency(total_balance)
        total_val_item = QTableWidgetItem(total_val_text)
        total_val_item.setFont(total_font)
        total_val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        total_val_item.setForeground(QColor("white"))
        self.accounts_table.setItem(0, 3, total_val_item)
        
        self.accounts_table.setRowHeight(0, self.s(60))
        
        # Add Divider
        self.accounts_table.insertRow(1)
        self.accounts_table.setRowHeight(1, self.s(2))
        self.accounts_table.setSpan(1, 0, 1, 5)
        div_item = QTableWidgetItem()
        div_item.setBackground(QColor("#555555"))
        div_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.accounts_table.setItem(1, 0, div_item)

        # Update Receipt Combo
        if hasattr(self, 'receipt_account_combo'):
            current_data = self.receipt_account_combo.currentData()
            self.receipt_account_combo.clear()
            for account_id, name, _ in accounts_data:
                self.receipt_account_combo.addItem(name, account_id)
            if current_data is not None:
                index = self.receipt_account_combo.findData(current_data)
                if index >= 0:
                    self.receipt_account_combo.setCurrentIndex(index)

        for account_id, name, balance in accounts_data:
            row = self.accounts_table.rowCount()
            self.accounts_table.insertRow(row)
            
            # Dot Label (Visual only)
            percentage = (balance / total_balance * 100) if total_balance > 0 else 0.0
            accent_color = color_for_percentage(percentage)
            
            dot_label = QLabel("●")
            dot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot_label.setStyleSheet(f"color: {accent_color}; font-size: {self.s(17)}px; background-color: transparent;")
            
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, account_id)
            name_item.setForeground(QColor(0, 0, 0, 0))
            
            # Name Button (Clickable)
            name_btn = QPushButton(name)
            name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            name_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: white;
                    border: none;
                    text-align: left;
                    font-size: {self.s(16)}px;
                    font-weight: bold;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    color: #cccccc;
                }}
            """)
            name_btn.clicked.connect(self._open_account_view)
            
            balance_item = QTableWidgetItem(self._format_number_as_currency(balance))
            balance_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Percentage Item (Subtle)
            percentage = (balance / total_balance * 100) if total_balance > 0 else 0.0
            pct_item = QTableWidgetItem(self._format_percentage(percentage))
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            pct_item.setForeground(QColor("#888888"))
            pct_font = self.font()
            pct_font.setPixelSize(self.s(16))
            pct_font.setBold(False)
            pct_item.setFont(pct_font)
            
            # Actions Container (Payment, Transfer, Edit)
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(self.s(30), 0, 0, 0)
            actions_layout.setSpacing(5)

            btn_style = f"""
                QPushButton {{
                    background-color: #444444;
                    color: #ffffff;
                    border: 1px solid #666666;
                    border-radius: {self.s(4)}px;
                    font-size: {self.s(12)}px;
                    padding: {self.s(4)}px {self.s(8)}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #555555;
                    border-color: #999999;
                }}
            """

            pay_btn = QPushButton("Payment")
            pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pay_btn.setStyleSheet(btn_style)
            pay_btn.clicked.connect(self._open_payment_page_from_table)

            transfer_btn = QPushButton("Transfer")
            transfer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            transfer_btn.setStyleSheet(btn_style)
            transfer_btn.clicked.connect(self._open_transfer_dialog)

            actions_layout.addWidget(pay_btn)
            actions_layout.addWidget(transfer_btn)
            
            self.accounts_table.setCellWidget(row, 0, dot_label)
            self.accounts_table.setItem(row, 1, name_item)
            self.accounts_table.setCellWidget(row, 1, name_btn)
            self.accounts_table.setItem(row, 2, pct_item)
            self.accounts_table.setItem(row, 3, balance_item)
            self.accounts_table.setCellWidget(row, 4, actions_widget)
        
        # Total row removed as it's now always on top
        pass
            
        # Also update analytics charts including Sankey (since it depends on all time data)
        self._update_analytics_data()


    def _get_bold_font(self):
        """Helper to get a bold font object."""
        font = self.font()
        font.setPixelSize(self.s(16))
        font.setBold(True)
        return font

    def _setup_create_receipt_page(self, page):
        """Sets up the layout for the create receipt page."""
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Back Button
        back_btn = QPushButton("← Back to Accounts")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(f"background-color: transparent; color: #aaaaaa; border: none; text-align: left; font-size: {self.s(14)}px; margin-bottom: {self.s(20)}px;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)

        # Title
        title = QLabel("Create Receipt")
        title.setStyleSheet(f"font-size: {self.s(24)}px; font-weight: bold; color: white; margin-bottom: {self.s(20)}px;")
        layout.addWidget(title)
        
        # Top Form
        top_form = QFormLayout()
        
        self.receipt_account_combo = QComboBox()
        self.receipt_account_combo.setView(QListView())
        self.receipt_account_combo.setFixedWidth(self.s(300))
        self.receipt_account_combo.setStyleSheet(f"""
            QComboBox {{ padding: {self.s(8)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px; }}
            QComboBox QAbstractItemView {{ background-color: #2b2b2b; color: white; outline: none; border: 1px solid #444; font-size: {self.s(18)}px; }}
            QComboBox QAbstractItemView::item {{ padding: {self.s(10)}px; color: white; }}
            QComboBox QAbstractItemView::item:hover {{ background-color: #333; }}
            QComboBox QAbstractItemView::item:selected {{ background-color: #ff9800; color: black; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{ image: none; }}
        """)
        lbl_acc = QLabel("Deposit To:")
        lbl_acc.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        top_form.addRow(lbl_acc, self.receipt_account_combo)

        # TXID (Hidden from UI)
        self.receipt_txid = QLabel()
        self.receipt_txid.setVisible(False)

        # Date
        self.receipt_date = ModernDateEdit(scale_factor=self.scale_factor)
        self.receipt_date.setFixedWidth(self.s(200))
        self.receipt_date.setDisplayFormat("MM/dd/yyyy")
        self.receipt_date.setDate(QDate.currentDate())
        self.receipt_date.setStyleSheet(f"QDateEdit {{ padding: {self.s(8)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px; }}")
        lbl_date = QLabel("Date:")
        lbl_date.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        top_form.addRow(lbl_date, self.receipt_date)
        
        self.receipt_desc = QLineEdit()
        self.receipt_desc.setFixedWidth(self.s(300))
        self.receipt_desc.setPlaceholderText("")
        self.receipt_desc.setStyleSheet(f"padding: {self.s(8)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px;")
        lbl_desc = QLabel("Description:")
        lbl_desc.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        top_form.addRow(lbl_desc, self.receipt_desc)

        layout.addLayout(top_form)

        # Item Table
        self.receipt_item_table = TransactionItemTable(currency_formatter=self._format_number_as_currency, scale_factor=self.scale_factor)
        self.receipt_item_table.setMaximumWidth(650)
        split_layout = QHBoxLayout()
        split_layout.addWidget(self.receipt_item_table, 1)
        split_layout.addStretch(1)
        layout.addLayout(split_layout)

        # Record Button
        record_btn = QPushButton("Create Receipt")
        record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        record_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(15)}px {self.s(30)}px; background-color: #009688; color: white;
                border: none; border-radius: {self.s(6)}px; font-weight: bold; font-size: {self.s(16)}px;
                margin-top: {self.s(15)}px;
            }}
            QPushButton:hover {{ background-color: #00796b; }}
        """)
        record_btn.clicked.connect(self._perform_receipt)
        layout.addWidget(record_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.receipt_item_table.clear_table()
        self._generate_receipt_txid()

    def _setup_create_payment_page(self, page):
        """Sets up the layout for the create payment page."""
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Back Button
        back_btn = QPushButton("← Back to Accounts")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(f"background-color: transparent; color: #aaaaaa; border: none; text-align: left; font-size: {self.s(14)}px; margin-bottom: {self.s(20)}px;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)

        # Title
        title = QLabel("Create Payment")
        title.setStyleSheet(f"font-size: {self.s(24)}px; font-weight: bold; color: white; margin-bottom: {self.s(10)}px;")
        layout.addWidget(title)
        
        # Account Info Container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 20)
        info_layout.setSpacing(2)
        
        self.payment_account_name_label = QLabel("Select an account")
        self.payment_account_name_label.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: white;")
        
        self.payment_account_balance_label = QLabel("")
        self.payment_account_balance_label.setStyleSheet(f"font-size: {self.s(14)}px; color: #cccccc; font-weight: bold;")
        
        info_layout.addWidget(self.payment_account_name_label)
        info_layout.addWidget(self.payment_account_balance_label)
        
        layout.addWidget(info_container)
        
        # Top Form
        top_form = QFormLayout()

        # Date
        self.payment_date = ModernDateEdit(scale_factor=self.scale_factor)
        self.payment_date.setFixedWidth(self.s(200))
        self.payment_date.setDisplayFormat("MM/dd/yyyy")
        self.payment_date.setDate(QDate.currentDate())
        self.payment_date.setStyleSheet(f"QDateEdit {{ padding: {self.s(8)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px; }}")
        lbl_date = QLabel("Date:")
        lbl_date.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        top_form.addRow(lbl_date, self.payment_date)
        
        self.payment_desc = QLineEdit()
        self.payment_desc.setFixedWidth(self.s(300))
        self.payment_desc.setPlaceholderText("")
        self.payment_desc.setStyleSheet(f"padding: {self.s(8)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px;")
        lbl_desc = QLabel("Description:")
        lbl_desc.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        top_form.addRow(lbl_desc, self.payment_desc)

        layout.addLayout(top_form)

        # Item Table
        self.payment_item_table = TransactionItemTable(currency_formatter=self._format_number_as_currency, scale_factor=self.scale_factor)
        self.payment_item_table.setMaximumWidth(650)
        split_layout = QHBoxLayout()
        split_layout.addWidget(self.payment_item_table, 1)
        split_layout.addStretch(1)
        layout.addLayout(split_layout)

        # Record Button
        record_btn = QPushButton("Create Payment")
        record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        record_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(15)}px {self.s(30)}px; background-color: #009688; color: white;
                border: none; border-radius: {self.s(6)}px; font-weight: bold; font-size: {self.s(16)}px;
                margin-top: {self.s(15)}px;
            }}
            QPushButton:hover {{ background-color: #00796b; }}
        """)
        record_btn.clicked.connect(self._perform_payment)
        layout.addWidget(record_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.payment_item_table.clear_table()

    def _create_pages(self):
        """Creates a placeholder page for each sidebar section."""
        pages = ["Accounts", "Receipts", "Payments", "Transfers", "Analytics", "Budgeter", "Settings"]
        for page_name in pages:
            page = QWidget()
            layout = QVBoxLayout(page)

            if page_name == "Accounts":
                self.accounts_page = page
                
                # Header
                header = QLabel("Accounts Management")
                header.setStyleSheet(f"font-size: {self.s(20)}px; font-weight: bold; color: white; margin-bottom: {self.s(10)}px;")
                layout.addWidget(header)

                # Main content Splitter for Adaptive Layout
                self.accounts_splitter = QSplitter(Qt.Orientation.Horizontal)
                self.accounts_splitter.setHandleWidth(2)
                self.accounts_splitter.setStyleSheet("QSplitter::handle { background-color: #3d3d3d; }")
                
                # Top Actions Row for Alignment
                top_actions_row = QHBoxLayout()
                layout.addLayout(top_actions_row)

                layout.addWidget(self.accounts_splitter, 1)

                # Left side container (Table Only)
                left_container = QWidget()
                left_layout = QVBoxLayout(left_container)
                left_layout.setContentsMargins(0, 0, 0, 0)
                self.accounts_splitter.addWidget(left_container)

                # Right side container (Flow Chart Only)
                right_container = QWidget()
                right_layout = QVBoxLayout(right_container)
                right_layout.setContentsMargins(20, 0, 0, 0)
                self.accounts_splitter.addWidget(right_container)

                # Row 0, Col 0: Account Actions (Buttons + Form)
                actions_container = QWidget()
                actions_layout = QVBoxLayout(actions_container)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                top_actions_row.addWidget(actions_container, 1)

                # Header Buttons Layout
                header_btns_layout = QHBoxLayout()
                header_btns_layout.setContentsMargins(0, 0, 0, 10)
                header_btns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
                actions_layout.addLayout(header_btns_layout)

                self.create_account_btn = QPushButton("+ Create Account")
                self.create_account_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.create_account_btn.setStyleSheet(f"""
                    QPushButton {{ 
                        padding: {self.s(6)}px {self.s(12)}px; 
                        background-color: #333333; 
                        color: #ffffff; 
                        border: 1px solid #555555; 
                        border-radius: {self.s(4)}px; 
                        font-size: {self.s(14)}px;
                    }}
                    QPushButton:hover {{ background-color: #444444; border-color: #777777; }}
                """)
                self.create_account_btn.clicked.connect(self._show_account_form)
                header_btns_layout.addWidget(self.create_account_btn)

                receipt_btn = QPushButton("+ Receipt")
                receipt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                receipt_btn.setStyleSheet(f"""
                    QPushButton {{ 
                        padding: {self.s(6)}px {self.s(12)}px; 
                        background-color: #333333; 
                        color: #ffffff; 
                        border: 1px solid #555555; 
                        border-radius: {self.s(4)}px; 
                        margin-left: {self.s(10)}px; 
                        font-size: {self.s(14)}px;
                    }}
                    QPushButton:hover {{ background-color: #444444; border-color: #777777; }}
                """)
                receipt_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.create_receipt_page))
                header_btns_layout.addWidget(receipt_btn)

                # Account Form
                self.account_form_container = QWidget()
                self.account_form_container.setVisible(False)
                form_layout_inner = QHBoxLayout(self.account_form_container)
                form_layout_inner.setContentsMargins(0, 0, 0, 10)
                
                self.account_input = QLineEdit()
                self.account_input.setFixedWidth(self.s(300))
                self.account_input.setPlaceholderText("New Account Name")
                self.account_input.setStyleSheet(f"padding: {self.s(8)}px; border: 1px solid #555; border-radius: {self.s(4)}px; background-color: #333; color: white; font-size: {self.s(16)}px;")
                
                create_btn = QPushButton("Create")
                create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                create_btn.setStyleSheet("""
                    QPushButton { padding: 8px 15px; background-color: transparent; color: #4caf50; border: 1px solid #4caf50; border-radius: 4px; font-weight: bold; }
                    QPushButton:hover { background-color: #4caf50; color: white; }
                """)
                create_btn.clicked.connect(self._add_account)

                cancel_btn = QPushButton("Cancel")
                cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                cancel_btn.setStyleSheet("""
                    QPushButton { padding: 8px 15px; background-color: transparent; color: #aaaaaa; border: 1px solid #aaaaaa; border-radius: 4px; font-weight: bold; }
                    QPushButton:hover { background-color: #444444; color: white; }
                """)
                cancel_btn.clicked.connect(self._hide_account_form)
                
                form_layout_inner.addWidget(self.account_input)
                form_layout_inner.addWidget(create_btn)
                form_layout_inner.addWidget(cancel_btn)
                actions_layout.addWidget(self.account_form_container, alignment=Qt.AlignmentFlag.AlignLeft)



                # Row 1, Col 0: Account Table Card
                table_frame = QFrame()
                table_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                table_frame.setObjectName("tableFrame")
                table_frame.setStyleSheet("#tableFrame { border: 1px solid #ff9800; border-radius: 4px; background-color: #2b2b2b; }")
                card_layout = QVBoxLayout(table_frame)
                card_layout.setContentsMargins(1, 1, 1, 1)

                # Table
                self.accounts_table = QTableWidget()
                self.accounts_table.setColumnCount(5)
                self.accounts_table.horizontalHeader().setVisible(False)
                self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
                self.accounts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
                self.accounts_table.setColumnWidth(0, self.s(40))
                self.accounts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                self.accounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
                self.accounts_table.setColumnWidth(2, self.s(100))
                self.accounts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
                self.accounts_table.setColumnWidth(4, self.s(260))
                self.accounts_table.verticalHeader().setVisible(False)
                self.accounts_table.verticalHeader().setDefaultSectionSize(self.s(60))
                self.accounts_table.setShowGrid(False)
                self.accounts_table.setAlternatingRowColors(True)
                self.accounts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                self.accounts_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
                self.accounts_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                self.accounts_table.setAutoScroll(False)
                self.accounts_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
                self.accounts_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                self.accounts_table.setStyleSheet(f"""
                    QTableWidget {{ background-color: #2b2b2b; alternate-background-color: #383838; border: none; color: white; font-size: {self.s(16)}px; font-weight: bold; }}
                    QHeaderView::section {{ background-color: #2b2b2b; color: white; padding: {self.s(5)}px; border: none; border-bottom: 2px solid #3d3d3d; font-size: {self.s(16)}px; }}
                    QTableWidget::item {{ padding: {self.s(15)}px; border: none; }}
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
                
                card_layout.addWidget(self.accounts_table)
                left_layout.addWidget(table_frame)

                flow_frame = QFrame()
                flow_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                flow_frame.setStyleSheet(".QFrame { border: 1px solid #ff9800; border-radius: 4px; background-color: #2b2b2b; }")
                flow_frame_layout = QVBoxLayout(flow_frame)
                flow_frame_layout.setContentsMargins(10, 10, 10, 10)
                flow_frame_layout.setSpacing(0)
                
                # Centered Title & Show Data Button inside the card
                inner_header_layout = QHBoxLayout()
                inner_header_layout.setContentsMargins(0, 0, 0, 0)
                inner_header_layout.addStretch(1)
                
                self.sankey_title = QLabel("Payment Flow of Net Receipts")
                self.sankey_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.sankey_title.setStyleSheet(f"font-size: {self.s(16)}px; font-weight: normal; color: white; border: none; background-color: transparent;")
                inner_header_layout.addWidget(self.sankey_title)
                inner_header_layout.addStretch(1)
                

                
                flow_frame_layout.addLayout(inner_header_layout)
                
                self.sankey_chart = SankeyWidget(scale_factor=self.scale_factor)
                self.sankey_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self.sankey_chart.setMinimumHeight(self.s(200)) 
                flow_frame_layout.addWidget(self.sankey_chart)
                right_layout.addWidget(flow_frame)

                self.accounts_splitter.setStretchFactor(0, 1)
                self.accounts_splitter.setStretchFactor(1, 1)
                self.accounts_splitter.setSizes([self.s(600), self.s(600)])
                
                self._load_accounts()
            elif page_name == "Receipts":
                self.receipts_list_page = page
            elif page_name == "Payments":
                self.payments_list_page = page
            elif page_name == "Transfers":
                self.transfers_list_page = page
            elif page_name == "Analytics":
                self.analytics_page = page
            elif page_name == "Budgeter":
                self.budgeter_page = page
            elif page_name == "Settings":
                self.settings_page = page
            else:
                label = QLabel(f"{page_name} View")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                font = label.font()
                font.setPointSize(self.s(20))
                label.setFont(font)
                layout.addWidget(label)

            self.stacked_widget.addWidget(page)

        # Add Create Receipt Page (not in sidebar)
        self.create_receipt_page = QWidget()
        self._setup_create_receipt_page(self.create_receipt_page)
        self.stacked_widget.addWidget(self.create_receipt_page)

        # Add Create Payment Page (not in sidebar)
        self.create_payment_page = QWidget()
        self._setup_create_payment_page(self.create_payment_page)
        self.stacked_widget.addWidget(self.create_payment_page)

        # Add Account Detail Page (Hidden from sidebar navigation)
        self.account_detail_page = QWidget()
        self._setup_account_detail_page(self.account_detail_page)
        self.stacked_widget.addWidget(self.account_detail_page)

        # Add Account View Page (Hidden from sidebar navigation)
        self.account_view_page = QWidget()
        self._setup_account_view_page(self.account_view_page)
        self.stacked_widget.addWidget(self.account_view_page)

        # Add Transaction Detail Page (Hidden from sidebar navigation)
        self.transaction_detail_page = QWidget()
        self._setup_transaction_detail_page(self.transaction_detail_page)
        self.stacked_widget.addWidget(self.transaction_detail_page)



    def _setup_settings_page(self, page):
        """Sets up the layout for the settings page."""
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)

        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header = QLabel("Application Settings")
        header.setStyleSheet(f"font-size: {self.s(20)}px; font-weight: bold; color: white; margin-bottom: {self.s(5)}px; background-color: transparent;")
        layout.addWidget(header)

        subtitle = QLabel("Adjust your preferences and application defaults here.")
        subtitle.setStyleSheet(f"font-size: {self.s(14)}px; color: #bbbbbb; margin-bottom: {self.s(25)}px; background-color: transparent;")
        layout.addWidget(subtitle)

        # Cards Container
        cards_container = QHBoxLayout()
        cards_container.setSpacing(self.s(20))
        cards_container.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addLayout(cards_container)

        # Native Currency Section
        currency_card = QFrame()
        currency_card.setStyleSheet(f".QFrame {{ border: 1px solid #ff9800; border-radius: {self.s(8)}px; background-color: #2b2b2b; }}")
        currency_card.setMaximumWidth(self.s(450))
        card_layout = QVBoxLayout(currency_card)
        card_layout.setContentsMargins(self.s(20), self.s(15), self.s(20), self.s(20))
        card_layout.setSpacing(15)

        section_title = QLabel("Ledger Currency")
        section_title.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: #ff9800; border: none; background-color: transparent;")
        card_layout.addWidget(section_title)

        # Form
        form_container = QWidget()
        form_container.setStyleSheet("border: none; background-color: transparent;")
        form_layout = QGridLayout(form_container)
        form_layout.setSpacing(10)

        # Symbol
        lbl_symbol = QLabel("Currency Symbol:")
        lbl_symbol.setStyleSheet(f"font-size: {self.s(16)}px; color: #dddddd; border: none; background-color: transparent;")
        self.settings_symbol_input = QLineEdit()
        self.settings_symbol_input.setText(self.currency_symbol)
        self.settings_symbol_input.setPlaceholderText("e.g. $, DOP, CHF")
        self.settings_symbol_input.setStyleSheet(f"padding: {self.s(8)}px; background-color: #2b2b2b; color: white; border: 1px solid #444; border-radius: {self.s(4)}px; font-size: {self.s(16)}px;")
        self.settings_symbol_input.setFixedWidth(self.s(200))

        # Decimals
        lbl_decimals = QLabel("Decimal Places:")
        lbl_decimals.setStyleSheet(f"font-size: {self.s(16)}px; color: #dddddd; border: none; background-color: transparent;")
        self.settings_decimals_spin = QSpinBox()
        self.settings_decimals_spin.setRange(0, 4)
        self.settings_decimals_spin.setValue(self.currency_decimals)
        self.settings_decimals_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.settings_decimals_spin.setStyleSheet(f"padding: {self.s(8)}px; background-color: #2b2b2b; color: white; border: 1px solid #444; border-radius: {self.s(4)}px; font-size: {self.s(16)}px;")
        self.settings_decimals_spin.setFixedWidth(self.s(200))

        form_layout.addWidget(lbl_symbol, 0, 0)
        form_layout.addWidget(self.settings_symbol_input, 0, 1)
        form_layout.addWidget(lbl_decimals, 1, 0)
        form_layout.addWidget(self.settings_decimals_spin, 1, 1)
        form_layout.setColumnStretch(2, 1)

        card_layout.addWidget(form_container)

        # Save Button
        save_layout = QHBoxLayout()
        save_btn = QPushButton("Apply")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(10)}px {self.s(20)}px;
                background-color: transparent;
                color: #ff9800;
                border: 1px solid #ff9800;
                border-radius: {self.s(4)}px;
                font-weight: bold;
                font-size: {self.s(16)}px;
            }}
            QPushButton:hover {{
                background-color: #ff9800;
                color: white;
            }}
        """)
        save_btn.clicked.connect(self._save_app_settings)
        save_layout.addWidget(save_btn)
        save_layout.addStretch()
        
        card_layout.addLayout(save_layout)
        # We will add currency_card to cards_container later

        # Data Management Section
        data_card = QFrame()
        data_card.setStyleSheet(f".QFrame {{ border: 1px solid #ff9800; border-radius: {self.s(8)}px; background-color: #2b2b2b; }}")
        data_card.setMaximumWidth(self.s(350))
        data_layout = QVBoxLayout(data_card)
        data_layout.setContentsMargins(self.s(20), self.s(20), self.s(20), self.s(20))
        data_layout.setSpacing(15)

        data_title = QLabel("Data Management")
        data_title.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: #ff9800; border: none; background-color: transparent;")
        data_layout.addWidget(data_title)

        backup_btn = QPushButton("Backup Database")
        backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        backup_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(10)}px {self.s(20)}px;
                background-color: transparent;
                color: white;
                border: 1px solid #555;
                border-radius: {self.s(4)}px;
                font-weight: bold;
                font-size: {self.s(14)}px;
            }}
            QPushButton:hover {{
                background-color: #444;
                border-color: #888;
            }}
        """)
        backup_btn.clicked.connect(self._backup_database)
        data_layout.addWidget(backup_btn)

        open_folder_btn = QPushButton("Import Backup")
        open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_folder_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(10)}px {self.s(20)}px;
                background-color: transparent;
                color: white;
                border: 1px solid #555;
                border-radius: {self.s(4)}px;
                font-weight: bold;
                font-size: {self.s(14)}px;
            }}
            QPushButton:hover {{
                background-color: #444;
                border-color: #888;
            }}
        """)
        open_folder_btn.clicked.connect(self._import_backup)
        data_layout.addWidget(open_folder_btn)

        export_csv_btn = QPushButton("Export Data as CSV")
        export_csv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_csv_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(10)}px {self.s(20)}px;
                background-color: transparent;
                color: #00bcd4;
                border: 1px solid #00bcd4;
                border-radius: {self.s(4)}px;
                font-weight: bold;
                font-size: {self.s(14)}px;
            }}
            QPushButton:hover {{
                background-color: #00bcd4;
                color: white;
            }}
        """)
        export_csv_btn.clicked.connect(self._export_data_as_csv)
        data_layout.addWidget(export_csv_btn)

        open_data_folder_btn = QPushButton("Open Data Folder")
        open_data_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_data_folder_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(10)}px {self.s(20)}px;
                background-color: transparent;
                color: #ff9800;
                border: 1px solid #ff9800;
                border-radius: {self.s(4)}px;
                font-weight: bold;
                font-size: {self.s(14)}px;
            }}
            QPushButton:hover {{
                background-color: #ff9800;
                color: white;
            }}
        """)
        open_data_folder_btn.clicked.connect(self._open_data_folder)
        data_layout.addWidget(open_data_folder_btn)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(10)}px {self.s(20)}px;
                background-color: transparent;
                color: #ff5252;
                border: 1px solid #ff5252;
                border-radius: {self.s(4)}px;
                font-weight: bold;
                font-size: {self.s(14)}px;
                margin-top: {self.s(10)}px;
            }}
            QPushButton:hover {{
                background-color: #ff5252;
                color: white;
            }}
        """)
        reset_btn.clicked.connect(self._reset_to_defaults)
        data_layout.addWidget(reset_btn)

        destruct_btn = QPushButton("Uninstall")
        destruct_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        destruct_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(10)}px {self.s(20)}px;
                background-color: transparent;
                color: #d32f2f;
                border: 1px solid #d32f2f;
                border-radius: {self.s(4)}px;
                font-weight: bold;
                font-size: {self.s(14)}px;
                margin-top: {self.s(10)}px;
            }}
            QPushButton:hover {{
                background-color: #d32f2f;
                color: white;
            }}
        """)
        destruct_btn.clicked.connect(self._self_destruct_app)
        data_layout.addWidget(destruct_btn)

        # Add cards to horizontal container
        cards_container.addWidget(data_card, alignment=Qt.AlignmentFlag.AlignTop)
        cards_container.addWidget(currency_card, alignment=Qt.AlignmentFlag.AlignTop)
        cards_container.addStretch()

    def _backup_database(self):
        """Creates a backup of the database file."""
        if not hasattr(self, 'db_path') or not os.path.exists(self.db_path):
            self._show_modern_message("Error", "Database file not found.", QMessageBox.Icon.Critical)
            return

        # Create a beautiful QDialog to prompt the user
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle("Backup Database")
        dialog.setMinimumWidth(self.s(450))
        
        # Style it beautifully
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: {self.s(8)}px;
            }}
            QLabel {{
                color: #ffffff;
                font-size: {self.s(14)}px;
            }}
            QPushButton {{
                padding: {self.s(12)}px {self.s(20)}px;
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #ff9800;
                border-radius: {self.s(6)}px;
                font-weight: bold;
                font-size: {self.s(14)}px;
            }}
            QPushButton:hover {{
                background-color: #ff9800;
                color: #1e1e1e;
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.s(25), self.s(25), self.s(25), self.s(25))
        layout.setSpacing(self.s(18))
        
        title_label = QLabel("Database Backup Options")
        title_label.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: #ff9800;")
        layout.addWidget(title_label)
        
        desc_label = QLabel("Select where you would like to save the backup of your database:")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Create buttons
        default_btn = QPushButton("Save in Default Location (.local)")
        default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        custom_btn = QPushButton("Select Custom Destination...")
        custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout.addWidget(default_btn)
        layout.addWidget(custom_btn)
        
        # Track choice
        self._backup_choice = None
        
        def pick_default():
            self._backup_choice = "default"
            dialog.accept()
            
        def pick_custom():
            self._backup_choice = "custom"
            dialog.accept()
            
        default_btn.clicked.connect(pick_default)
        custom_btn.clicked.connect(pick_custom)
        
        if dialog.exec() != QDialog.Accepted:
            return

        try:
            now = QDateTime.currentDateTime()
            timestamp = now.toString("yyyy-MM-dd_HH-mm-ss")
            
            if self._backup_choice == "default":
                app_dir = os.path.dirname(self.db_path)
                file_name = backup_exporter.get_default_backup_path(app_dir, timestamp)
            else:
                # Custom destination dialog
                default_filename = f"tallybook_backup_{timestamp}.db"
                file_name, _ = QFileDialog.getSaveFileName(self, "Backup Database", default_filename, "Database Files (*.db)")
                if not file_name:
                    return

            # Flush any pending writes
            self.conn.commit()
            
            # Copy file via backup_exporter
            backup_exporter.create_backup(self.db_path, file_name)
            self._show_modern_message("Success", f"Backup saved successfully to:\n{file_name}")
        except Exception as e:
            self._show_modern_message("Error", f"Failed to save backup: {e}", QMessageBox.Icon.Critical)

    def _export_data_as_csv(self):
        """Exports all transactions to a CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Data", "tallybook_export.csv", "CSV Files (*.csv)")
        if not file_path:
            return

        success, message = csv_exporter.export_data_as_csv(file_path, self.conn)
        if success:
            self._show_modern_message("Success", message)
        else:
            self._show_modern_message("Error", message, QMessageBox.Icon.Critical)

    def _validate_database(self, file_path):
        """Checks if a file is a valid TallyBook database by verifying the schema."""
        try:
            # Try to open as a SQLite database
            temp_conn = sqlite3.connect(file_path)
            cursor = temp_conn.cursor()
            
            # Check for essential tables
            required_tables = {'accounts', 'transactions', 'settings'}
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            temp_conn.close()
            
            # Check if all required tables are present
            return required_tables.issubset(existing_tables)
        except Exception:
            return False

    def _import_backup(self):
        """Imports a database backup file."""
        start_dir = ""
        if hasattr(self, 'db_path'):
            app_dir = os.path.dirname(self.db_path)
            backup_dir = os.path.join(app_dir, "Backups")
            if os.path.exists(backup_dir):
                start_dir = backup_dir
            else:
                start_dir = app_dir

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File",
            start_dir,
            "SQLite Database (*.db);;All Files (*)"
        )

        if file_name:
            # 1. Validate the file BEFORE doing anything else
            if not self._validate_database(file_name):
                self._show_modern_message(
                    "Unrecognizable File", 
                    "The selected file is not a valid TallyBook database backup.\n\nPlease select a proper .db file created by TallyBook.",
                    QMessageBox.Icon.Critical
                )
                return

            # 2. Proceed with warning
            reply = self._show_modern_message(
                "Confirm Import",
                "Importing a backup will OVERWRITE all current data.\n\nAre you sure you want to proceed?",
                QMessageBox.Icon.Warning,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.Yes:
                try:
                    self.conn.close()
                    shutil.copy2(file_name, self.db_path)
                    # Re-initialize the entire database backend to sync the new connection
                    self._init_database()
                    self._load_accounts()
                    self.settings_symbol_input.setText(self.currency_symbol)
                    self.settings_decimals_spin.setValue(self.currency_decimals)
                    self._show_modern_message("Success", "Backup imported successfully.")
                except Exception as e:
                    # In case of failure, try to recover the connection
                    self._init_database()
                    self._show_modern_message("Error", f"Failed to import backup: {e}", QMessageBox.Icon.Critical)

    def _open_data_folder(self):
        """Opens the folder where the database and backups are stored."""
        if hasattr(self, 'db_path'):
            app_dir = os.path.dirname(self.db_path)
            if os.path.exists(app_dir):
                QDesktopServices.openUrl(QUrl.fromLocalFile(app_dir))
            else:
                self._show_modern_message("Warning", "Data folder does not exist.", QMessageBox.Icon.Warning)
        else:
            self._show_modern_message("Error", "Database path not found.", QMessageBox.Icon.Critical)

    def _reset_to_defaults(self):
        """Resets the application to its initial state by deleting the database file."""
        reply = self._show_modern_message(
            "Reset to Defaults", 
            "Are you sure you want to reset everything? This will delete ALL accounts, transactions, and settings.\n\nThis action cannot be undone.",
            QMessageBox.Icon.Warning,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Close connection and delete database file to ensure a completely clean start
                # This wipes all data and resets all auto-increment sequences.
                self.conn.close()
                
                # Also remove temporary SQLite files if they exist
                for suffix in ['', '-journal', '-wal', '-shm']:
                    p = self.db_path + suffix
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                
                # Re-initialize database (this recreates tables and default settings)
                self._init_database()
                
                # Update Settings UI inputs
                self.settings_symbol_input.setText(self.currency_symbol)
                self.settings_decimals_spin.setValue(self.currency_decimals)
                
                self._show_modern_message("Reset Complete", "Application has been reset to defaults.")
                
            except Exception as e:
                # Attempt to reconnect if something went wrong
                try:
                    self.conn = sqlite3.connect(self.db_path)
                    self.cursor = self.conn.cursor()
                except Exception:
                    pass
                self._show_modern_message("Error", f"Failed to reset application: {e}", QMessageBox.Icon.Critical)

    def _self_destruct_app(self):
        """Uninstalls the application by dynamically detecting and deleting all related files."""
        reply = self._show_modern_message(
            "Uninstall", 
            "CRITICAL WARNING:\n\nAre you sure you want to completely uninstall TallyBook? "
            "This will permanently delete the application binary, database, all backups, the desktop entry, and the icon.\n\n"
            "This action CANNOT be undone and the application will close immediately.",
            QMessageBox.Icon.Warning,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.Yes:
            # Final text confirmation
            text, ok = self._show_modern_input(
                "Final Confirmation", 
                "To confirm complete uninstallation and data deletion, please type 'DELETE' in all caps:"
            )
            
            if not ok or text != "DELETE":
                if ok:
                    self._show_modern_message("Cancelled", "Incorrect confirmation text. Uninstall cancelled.")
                return

            try:
                # 1. Gather all paths to delete
                to_delete = []
                
                # Application Binary (AppImage or Frozen Binary)
                appimage_path = os.environ.get('APPIMAGE')
                if appimage_path and os.path.exists(appimage_path):
                    to_delete.append(appimage_path)
                elif getattr(sys, 'frozen', False):
                    to_delete.append(sys.executable)
                
                # Database & Backups
                app_data_dir = None
                if hasattr(self, 'db_path'):
                    to_delete.append(self.db_path)
                    for suffix in ['-journal', '-wal', '-shm']:
                        p = self.db_path + suffix
                        if os.path.exists(p):
                            to_delete.append(p)
                    
                    app_data_dir = os.path.dirname(self.db_path)
                    backup_dir = os.path.join(app_data_dir, "Backups")
                    if os.path.exists(backup_dir):
                        to_delete.append(backup_dir)
                
                # Search for Desktop Entry and Icon
                # We look in the standard user applications directory
                desktop_dir = os.path.expanduser("~/.local/share/applications")
                if os.path.exists(desktop_dir):
                    for filename in os.listdir(desktop_dir):
                        if filename.endswith(".desktop"):
                            desktop_path = os.path.join(desktop_dir, filename)
                            try:
                                is_ours = False
                                with open(desktop_path, 'r') as f:
                                    desktop_content = f.read()
                                    # Check if this desktop file points to our current binary
                                    if appimage_path and appimage_path in desktop_content:
                                        is_ours = True
                                    elif "tallybook" in filename.lower():
                                        is_ours = True
                                
                                if is_ours:
                                    to_delete.append(desktop_path)
                                    # Parse icon from content we already read
                                    for line in desktop_content.splitlines():
                                        if line.startswith("Icon="):
                                            icon_val = line.split("=", 1)[1].strip()
                                            if os.path.isabs(icon_val) and os.path.exists(icon_val):
                                                to_delete.append(icon_val)
                                            else:
                                                # Search for named icon in common user icon dirs
                                                for idir in [os.path.expanduser("~/.local/share/icons"), os.path.expanduser("~/.icons")]:
                                                    if not os.path.exists(idir):
                                                        continue
                                                    for root, dirs, files in os.walk(idir):
                                                        for f_icon in files:
                                                            if f_icon.startswith(icon_val):
                                                                to_delete.append(os.path.join(root, f_icon))
                            except Exception:
                                pass

                # 2. Close connection
                self.conn.close()
                
                # 3. Perform Deletion
                for path in set(to_delete):
                    if not path:
                        continue
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        elif os.path.exists(path):
                            os.remove(path)
                    except Exception:
                        pass
                
                # 4. Final attempt to remove the app data directory if empty
                if app_data_dir and os.path.exists(app_data_dir):
                    try:
                        os.rmdir(app_data_dir)
                    except Exception:
                        pass

                self._show_modern_message("Uninstall Complete", "TallyBook has been successfully uninstalled. The application will now close.")
                QApplication.quit()
                
            except Exception as e:
                self._show_modern_message("Error", f"Failed to complete uninstall: {e}", QMessageBox.Icon.Critical)

    def _save_app_settings(self):
        symbol = self.settings_symbol_input.text().strip()
        decimals = self.settings_decimals_spin.value()
        
        if not symbol:
            symbol = "$" # Fallback
            
        self.db.update_setting('currency_symbol', symbol)
        self.db.update_setting('currency_decimals', str(decimals))
        
        self.currency_symbol = symbol
        self.currency_decimals = decimals

        
        # Propagate changes to all UI components immediately
        self._apply_currency_settings()
        
        # Show success message box
        self._show_modern_message("Applied", "Currency settings have been applied successfully!")
        


    def _setup_budgeter_page(self, page):
        """Sets up the layout for the budgeter page."""
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
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
        self.budget_income_spin.valueChanged.connect(self._update_budget_chart)
        
        self.budget_income_spin.setSpecialValueText(" ")
        self.budget_income_spin.setValue(0.00) # Reset to show blank
        
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
        
        self.budget_inputs = {} # acc_id -> (spinbox, pct_label, name)

    def _load_budgeter_data(self):
        """Loads accounts into the budgeter table."""
        self.budget_table.setRowCount(0)
        self.budget_inputs.clear()
        
        self.cursor.execute("SELECT id, name FROM accounts")
        accounts = self.cursor.fetchall()
        
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
            spin.setSpecialValueText(" ") # Make blank when 0
            spin.setValue(0.00)
            spin.valueChanged.connect(self._update_budget_chart)
            self.budget_table.setCellWidget(row, 2, spin)
            
            pct_lbl = QLabel("0.00%")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pct_lbl.setStyleSheet(f"color: white; font-weight: bold; font-size: {self.s(16)}px; background-color: transparent; border: none;")
            self.budget_table.setCellWidget(row, 3, pct_lbl)
            
            self.budget_inputs[acc_id] = (spin, pct_lbl, name, dot_label, row)
            
        self._update_budget_chart()

    def _update_budget_chart(self):
        """Updates the budget totals."""
        income = self.budget_income_spin.value()
        total_allocated = 0.0
        
        # Calculate totals first for percentage accuracy
        for acc_id, item in self.budget_inputs.items():
            spin = item[0]
            total_allocated += spin.value()
            
        remaining = income - total_allocated
        total_for_pct = income if income > 0 else (total_allocated if total_allocated > 0 else 1.0)
        
        # Update data for the table
        for acc_id, item in self.budget_inputs.items():
            spin = item[0]
            pct_lbl = item[1]
            dot_label = item[3] if len(item) > 3 else None
            row = item[4] if len(item) > 4 else None
            
            val = spin.value()
            pct = (val / total_for_pct) * 100
            pct_lbl.setText(self._format_percentage(pct)) # Update table label
            
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

    def _show_calculator_window(self):
        """Shows a fresh instance of the standalone calculator window."""
        # Always create a new instance for a fresh start
        self.calculator_window = CalculatorWindow(self, scale_factor=self.scale_factor)
        self.calculator_window.show()
        self.calculator_window.raise_()
        self.calculator_window.activateWindow()

    def _setup_analytics_page(self, page):
        """Sets up the layout for the analytics page with a scroll area for multiple charts."""
        main_layout = page.layout()
        if main_layout is None:
            main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e1e;")
        self.analytics_layout = QVBoxLayout(container)
        self.analytics_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.analytics_layout.setContentsMargins(self.s(20), self.s(20), self.s(20), self.s(20))
        self.analytics_layout.setSpacing(self.s(30))
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # 1. Receipts Analytics (Global)
        receipts_section = QWidget()
        receipts_layout = QVBoxLayout(receipts_section)
        receipts_layout.setContentsMargins(0, 0, 0, 0)
        
        header = QLabel("Receipts Analytics (All Accounts)")
        header.setStyleSheet(f"font-size: {self.s(20)}px; font-weight: bold; color: white; margin-bottom: {self.s(10)}px;")
        receipts_layout.addWidget(header)
        
        chart_frame = QFrame()
        chart_frame.setStyleSheet(".QFrame { border: 1px solid #ff9800; border-radius: 4px; background-color: #2b2b2b; }")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(1, 1, 1, 1)

        chart_font = QFont("Fira Code")
        chart_font.setPointSize(self.s(10))
        bold_chart_font = QFont("Fira Code")
        bold_chart_font.setBold(True)
        bold_chart_font.setPointSize(self.s(12))

        self.receipts_chart = QChart()
        self.receipts_chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        self.receipts_chart.setBackgroundBrush(QColor("#2b2b2b"))
        self.receipts_chart.setTitle("Monthly Receipts Over Time")
        self.receipts_chart.setTitleFont(bold_chart_font)
        self.receipts_chart.setTitleBrush(QColor("white"))
        self.receipts_chart.legend().hide()
        
        self.receipts_series = QBarSeries()
        self.receipts_series.hovered.connect(self._on_bar_hovered)
        self.receipts_chart.addSeries(self.receipts_series)
        
        self.axis_x = QBarCategoryAxis()
        self.axis_x.setTitleVisible(False)
        self.axis_x.setLabelsColor(QColor("white"))
        self.axis_x.setLabelsFont(chart_font)
        self.axis_x.setTitleFont(chart_font)
        self.axis_x.setTitleBrush(QColor("white"))
        self.axis_x.setGridLineVisible(False)
        self.receipts_chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.receipts_series.attachAxis(self.axis_x)
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleVisible(False)
        self.axis_y.setLabelsColor(QColor("white"))
        self.axis_y.setLabelsFont(chart_font)
        self.axis_y.setTitleFont(chart_font)
        self.axis_y.setTitleBrush(QColor("white"))
        self.axis_y.setLabelFormat("%.2f")
        self.axis_y.setGridLineColor(QColor("#444444"))
        self.receipts_chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.receipts_series.attachAxis(self.axis_y)
        
        chart_view = QChartView(self.receipts_chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setStyleSheet("background-color: #2b2b2b; border: none;")
        chart_view.setMinimumHeight(self.s(400))
        chart_layout.addWidget(chart_view)
        
        receipts_layout.addWidget(chart_frame)
        self.analytics_layout.addWidget(receipts_section)
        
        # 3. Account Payments Analytics
        self.payments_header = QLabel("Monthly Payments by Account")
        self.payments_header.setStyleSheet(f"font-size: {self.s(20)}px; font-weight: bold; color: white; margin-top: {self.s(20)}px; margin-bottom: {self.s(10)}px;")
        self.analytics_layout.addWidget(self.payments_header)
        
        self.account_payments_container = QWidget()
        self.account_payments_layout = QGridLayout(self.account_payments_container)
        self.account_payments_layout.setContentsMargins(0, 0, 0, 0)
        self.account_payments_layout.setSpacing(self.s(20))
        self.account_payments_layout.setColumnStretch(0, 1)
        self.account_payments_layout.setColumnStretch(1, 1)
        self.analytics_layout.addWidget(self.account_payments_container)
        
        self.account_payment_charts = {} # acc_id -> (series, axis_x, axis_y)

    def _update_analytics_data(self):
        """Queries database and updates the analytics charts with a 12-month rolling window."""
        # 1. Determine the last 12 months (including current)
        today = QDate.currentDate()
        month_keys = []
        categories = []
        for i in range(11, -1, -1):
            target = today.addMonths(-i)
            m_date = QDate(target.year(), target.month(), 1)
            month_keys.append(m_date.toString("yyyy-MM"))
            categories.append(m_date.toString("MMM"))
            
        start_date_str = month_keys[0] + "-01"

        # 2. Update Global Receipts
        if not hasattr(self, 'receipts_series'):
            if hasattr(self, 'sankey_chart'):
                self.cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Receipt'")
                raw_total = self.cursor.fetchone()[0] or 0
                total_receipts_all_time = self._from_internal(raw_total)
                
                self.cursor.execute("SELECT id, name FROM accounts")
                accounts = self.cursor.fetchall()
                
                sankey_data = []
                for acc_id, acc_name in accounts:
                    self.cursor.execute("""
                        SELECT SUM(amount) FROM transactions 
                        WHERE type = 'Payment' AND account_id = ?
                    """, (acc_id,))
                    raw_vol = self.cursor.fetchone()[0] or 0
                    vol = self._from_internal(raw_vol)
                    sankey_data.append((acc_name, vol))
                
                self.sankey_chart.setData(total_receipts_all_time, sankey_data, self.currency_symbol, self.currency_decimals)
                if hasattr(self, 'sankey_title'):
                    total_str = f"— {self.currency_symbol} {total_receipts_all_time:,.{self.currency_decimals}f}"
                    self.sankey_title.setText(f"Payment Flow of Net Receipts {total_str}")
                

            return

        self.receipts_series.clear()
        self.cursor.execute("""
            SELECT strftime('%Y-%m', date) as month, SUM(amount)
            FROM transactions
            WHERE type = 'Receipt' AND date >= ?
            GROUP BY month
        """, (start_date_str,))
        
        db_results = {row[0]: self._from_internal(row[1]) for row in self.cursor.fetchall()}
        
        bar_set_receipts = QBarSet("Receipts")
        bar_set_receipts.setColor(QColor("#ff9800"))
        bar_set_receipts.setPen(QPen(Qt.PenStyle.NoPen))
        
        max_val_receipts = 0
        for key in month_keys:
            total_amount = db_results.get(key, 0.0)
            bar_set_receipts.append(total_amount)
            if total_amount > max_val_receipts:
                max_val_receipts = total_amount
            
        self.receipts_series.append(bar_set_receipts)
        self.axis_x.clear()
        self.axis_x.append(categories)
        self.axis_y.setRange(0, max_val_receipts * 1.1 if max_val_receipts > 0 else 100)
            
        # 3. Update Account Payments
        self.cursor.execute("SELECT id, name FROM accounts")
        accounts = self.cursor.fetchall()
        self.payments_header.setVisible(len(accounts) > 0)
        new_acc_ids = sorted([acc[0] for acc in accounts])
        
        # Determine if we need to rebuild the grid (only if accounts changed)
        if not hasattr(self, '_prev_acc_ids') or self._prev_acc_ids != new_acc_ids:
            # Rebuild grid
            while self.account_payments_layout.count():
                item = self.account_payments_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.account_payment_charts.clear()
            self._prev_acc_ids = new_acc_ids
            rebuild_needed = True
        else:
            rebuild_needed = False
        
        for i, (acc_id, acc_name) in enumerate(accounts):
            # Query monthly payments for this account (no transfers)
            self.cursor.execute("""
                SELECT strftime('%Y-%m', date) as month, SUM(amount)
                FROM transactions
                WHERE type = 'Payment' AND account_id = ? AND date >= ?
                GROUP BY month
            """, (acc_id, start_date_str))
            
            p_results = {row[0]: self._from_internal(row[1]) for row in self.cursor.fetchall()}
            
            if rebuild_needed:
                # Create Chart
                chart_frame, series, ax, ay = self._create_account_payment_chart(acc_name)
                self.account_payments_layout.addWidget(chart_frame, i // 2, i % 2)
                self.account_payment_charts[acc_id] = (series, ax, ay)
            else:
                series, ax, ay = self.account_payment_charts[acc_id]
                series.clear()
            
            bar_set_p = QBarSet("Payments")
            bar_set_p.setColor(QColor("#ff9800"))
            bar_set_p.setPen(QPen(Qt.PenStyle.NoPen))
            
            max_val_p = 0
            for key in month_keys:
                total_amount = p_results.get(key, 0.0)
                bar_set_p.append(total_amount)
                if total_amount > max_val_p:
                    max_val_p = total_amount
                
            series.append(bar_set_p)
            ax.clear()
            ax.append(categories)
            ay.setRange(0, max_val_p * 1.1 if max_val_p > 0 else 100)

        # 4. Update Sankey Chart (Flow from Total Receipts to Account Payments - All Time)
        self.cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Receipt'")
        raw_tr = self.cursor.fetchone()[0] or 0
        total_receipts_all_time = self._from_internal(raw_tr)
        
        sankey_data = []
        for acc_id, acc_name in accounts:
            self.cursor.execute("""
                SELECT SUM(amount) 
                FROM transactions 
                WHERE type = 'Payment' 
                AND account_id = ?
            """, (acc_id,))
            raw_v = self.cursor.fetchone()[0] or 0
            vol = self._from_internal(raw_v)
            sankey_data.append((acc_name, vol))
            
        if hasattr(self, 'sankey_chart'):
            self.sankey_chart.setData(total_receipts_all_time, sankey_data, self.currency_symbol, self.currency_decimals)
            if hasattr(self, 'sankey_title'):
                total_str = f"— {self.currency_symbol} {total_receipts_all_time:,.{self.currency_decimals}f}"
                self.sankey_title.setText(f"Payment Flow of Net Receipts {total_str}")
            


    def _create_account_payment_chart(self, acc_name):
        """Helper to create a formatted payment chart for an account."""
        chart_frame = QFrame()
        chart_frame.setStyleSheet(".QFrame { border: 1px solid #ff9800; border-radius: 4px; background-color: #2b2b2b; }")
        layout = QVBoxLayout(chart_frame)
        layout.setContentsMargins(1, 1, 1, 1)
        
        chart_font = QFont("Fira Code")
        chart_font.setPointSize(self.s(9))
        bold_chart_font = QFont("Fira Code")
        bold_chart_font.setBold(True)
        bold_chart_font.setPointSize(self.s(11))

        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        chart.setBackgroundBrush(QColor("#2b2b2b"))
        chart.setTitle(acc_name)
        chart.setTitleFont(bold_chart_font)
        chart.setTitleBrush(QColor("white"))
        chart.legend().hide()
        
        series = QBarSeries()
        series.hovered.connect(self._on_bar_hovered)
        chart.addSeries(series)
        
        ax = QBarCategoryAxis()
        ax.setTitleVisible(False)
        ax.setLabelsColor(QColor("white"))
        ax.setLabelsFont(chart_font)
        ax.setTitleFont(chart_font)
        ax.setTitleBrush(QColor("white"))
        ax.setGridLineVisible(False)
        chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(ax)
        
        ay = QValueAxis()
        ay.setTitleVisible(False)
        ay.setLabelsColor(QColor("white"))
        ay.setLabelsFont(chart_font)
        ay.setTitleFont(chart_font)
        ay.setTitleBrush(QColor("white"))
        ay.setLabelFormat("%.2f")
        ay.setGridLineColor(QColor("#444444"))
        chart.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(ay)
        
        view = QChartView(chart)
        view.setMinimumHeight(self.s(350))
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setStyleSheet("background-color: #2b2b2b; border: none;")
        layout.addWidget(view)
        
        return chart_frame, series, ax, ay

    def _on_bar_hovered(self, status, index, barset):
        """Shows a modern tooltip when hovering over a bar in any analytics chart."""
        if status:
            series = self.sender()
            if not isinstance(series, QBarSeries):
                return
                
            chart = series.chart()
            axis_x = None
            for ax in chart.axes(Qt.Orientation.Horizontal):
                if isinstance(ax, QBarCategoryAxis):
                    axis_x = ax
                    break
            
            if axis_x:
                val = barset.at(index)
                categories = axis_x.categories()
                cat = categories[index] if index < len(categories) else "Unknown"
                
                # Convert abbreviated month to full month name
                month_map = {
                    "Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
                    "May": "May", "Jun": "June", "Jul": "July", "Aug": "August",
                    "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December"
                }
                cat = month_map.get(cat, cat)
                
                text = f"{cat}\n{self.currency_symbol} {val:,.{self.currency_decimals}f}"
                
                # Calculate bar center position
                # For QBarSeries, the X-coordinate is the index of the category
                pos_in_chart = chart.mapToPosition(QPointF(index, val), series)
                
                # Get the chart view to map to global coordinates
                views = chart.scene().views() if chart.scene() else []
                if views:
                    view = views[0]
                    # Map from chart/scene coordinates to global screen coordinates
                    global_pos = view.mapToGlobal(view.mapFromScene(pos_in_chart))
                    self.modern_tooltip.show_at(global_pos, text, self.scale_factor)
                else:
                    self.modern_tooltip.show_at(QCursor.pos(), text, self.scale_factor)
        else:
            self.modern_tooltip.hide()

    def _on_page_changed(self, index):
        """Handler for when the stacked_widget's current page changes."""
        widget = self.stacked_widget.widget(index)
        if widget is None:
            return

        # Using hasattr to be safe in case pages aren't initialized yet
        if hasattr(self, 'accounts_page') and widget == self.accounts_page:
            self._load_accounts()
        elif hasattr(self, 'receipts_list_page') and widget == self.receipts_list_page:
            if not getattr(widget, '_is_built', False):
                self.receipts_list_table = self._create_transaction_list_view(widget.layout(), "Receipts")
                widget._is_built = True
            self._load_all_transactions("Receipt")
        elif hasattr(self, 'payments_list_page') and widget == self.payments_list_page:
            if not getattr(widget, '_is_built', False):
                self.payments_list_table = self._create_transaction_list_view(widget.layout(), "Payments")
                widget._is_built = True
            self._load_all_transactions("Payment")
        elif hasattr(self, 'transfers_list_page') and widget == self.transfers_list_page:
            if not getattr(widget, '_is_built', False):
                self.transfers_list_table = self._create_transaction_list_view(widget.layout(), "Transfers")
                widget._is_built = True
            self._load_all_transactions("Transfer")
        elif hasattr(self, 'budgeter_page') and widget == self.budgeter_page:
            if not getattr(widget, '_is_built', False):
                self._setup_budgeter_page(widget)
                widget._is_built = True
            self._load_budgeter_data()
        elif hasattr(self, 'analytics_page') and widget == self.analytics_page:
            if not getattr(widget, '_is_built', False):
                self._setup_analytics_page(widget)
                widget._is_built = True
            self._update_analytics_data()
        elif hasattr(self, 'settings_page') and widget == self.settings_page:
            if not getattr(widget, '_is_built', False):
                self._setup_settings_page(widget)
                widget._is_built = True
            
        # Update Sidebar Button Highlights
        for idx, btn in self.nav_buttons.items():
            is_selected = (idx == index)
            btn.setProperty("selected", "true" if is_selected else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _load_all_transactions(self, page_type):
        """Loads all transactions of a specific type into the corresponding list view."""
        search_text = ""
        if page_type == "Receipt" and hasattr(self, 'receipts_search_input'):
            search_text = self.receipts_search_input.text().strip().lower()
        elif page_type == "Payment" and hasattr(self, 'payments_search_input'):
            search_text = self.payments_search_input.text().strip().lower()
        elif page_type == "Transfer" and hasattr(self, 'transfers_search_input'):
            search_text = self.transfers_search_input.text().strip().lower()

        params = []
        wildcard = f"%{search_text}%"

        if page_type == "Receipt":
            table = self.receipts_list_table
            query = """
                SELECT
                    MAX(t.id), t.date, a.name, t.type, t.payment_description,
                    MAX(t.description), SUM(t.amount), COUNT(t.id)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'Receipt'
            """
            if search_text:
                query += " AND (lower(ifnull(t.payment_description, '')) LIKE ? OR lower(ifnull(t.description, '')) LIKE ?)"
                params = [wildcard, wildcard]
            
            query += """
                GROUP BY t.txid, t.type, t.date, a.name
                ORDER BY t.date DESC, MAX(t.id) DESC
            """
            if hasattr(self, 'receipts_page_num'):
                limit = 50
                offset = (self.receipts_page_num - 1) * limit
                query += f" LIMIT {limit} OFFSET {offset}"
        elif page_type == "Payment":
            table = self.payments_list_table
            query = """
                SELECT
                    MAX(t.id), t.date, a.name, t.type, t.payment_description,
                    MAX(t.description), SUM(t.amount), COUNT(t.id)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'Payment'
            """
            if search_text:
                query += " AND (lower(ifnull(t.payment_description, '')) LIKE ? OR lower(ifnull(t.description, '')) LIKE ?)"
                params = [wildcard, wildcard]
            
            query += """
                GROUP BY t.txid, t.type, t.date, a.name
                ORDER BY t.date DESC, MAX(t.id) DESC
            """
            if hasattr(self, 'payments_page_num'):
                limit = 50
                offset = (self.payments_page_num - 1) * limit
                query += f" LIMIT {limit} OFFSET {offset}"
        elif page_type == "Transfer":
            table = self.transfers_list_table
            query = """
                SELECT
                    t_out.id, t_out.date, a_from.name, t_out.amount, a_to.name, t_out.description
                FROM transactions t_out
                JOIN accounts a_from ON t_out.account_id = a_from.id
                LEFT JOIN transactions t_in ON t_out.txid = t_in.txid AND t_in.type = 'Transfer In'
                LEFT JOIN accounts a_to ON t_in.account_id = a_to.id
                WHERE t_out.type = 'Transfer Out'
            """
            if search_text:
                query += " AND lower(ifnull(t_out.description, '')) LIKE ?"
                params = [wildcard]
            
            query += """
                ORDER BY t_out.date DESC, t_out.id DESC
            """
            if hasattr(self, 'transfers_page_num'):
                limit = 50
                offset = (self.transfers_page_num - 1) * limit
                query += f" LIMIT {limit} OFFSET {offset}"
        else:
            return

        table.setRowCount(0)
        import gc
        gc.collect()
        self.cursor.execute(query, params)
        transactions = self.cursor.fetchall()

        for row_data in transactions:
            row = table.rowCount()
            table.insertRow(row)

            if page_type == "Transfer":
                tx_id, date, from_name, amount_internal, to_name, user_desc = row_data
                amount = self._from_internal(amount_internal)
                to_name = to_name if to_name else "N/A"

                date_item = QTableWidgetItem(QDate.fromString(date, "yyyy-MM-dd").toString("MM/dd/yyyy"))
                date_item.setData(Qt.UserRole, tx_id)
                table.setItem(row, 0, date_item)
                table.setItem(row, 1, QTableWidgetItem("Transfer"))
                table.setItem(row, 2, QTableWidgetItem(f"{from_name} → {to_name}"))
                table.setItem(row, 3, QTableWidgetItem(user_desc if user_desc else ""))
                
                amt_item = QTableWidgetItem(f"{self.currency_symbol} {amount:,.{self.currency_decimals}f}")
                amt_item = QTableWidgetItem(self._format_number_as_currency(amount))
                amt_item.setForeground(QColor("#ffeb3b")) # Vibrant Yellow
                font = self._get_bold_font()
                font.setItalic(True)
                amt_item.setFont(font)
                amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 4, amt_item)

                # Actions Container
                actions_widget = QWidget()
                actions_widget.setStyleSheet("background-color: transparent; border: none;")
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                actions_layout.setSpacing(5)

                btn_style = """
                    QPushButton {
                        background-color: #444444; color: #ffffff; border: 1px solid #666666;
                        border-radius: 4px; font-size: 12px; padding: 4px 8px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #555555; border-color: #999999; color: white; }
                """

                view_btn = QPushButton("View")
                view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                view_btn.setStyleSheet(btn_style)
                current_tx_id = row_data[0]
                view_btn.clicked.connect(lambda checked, tx_id=current_tx_id: self._open_transaction_detail_by_id(tx_id, "view"))
                actions_layout.addWidget(view_btn)

                edit_btn = QPushButton("Edit")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.setStyleSheet(btn_style)
                edit_btn.clicked.connect(lambda checked, tx_id=current_tx_id: self._open_transaction_detail_by_id(tx_id, "edit"))
                actions_layout.addWidget(edit_btn)

                table.setCellWidget(row, 5, actions_widget)

            else: # Payments and Receipts
                tx_id, date, acc_name, type_, pay_desc, item_desc, amount_internal, count = row_data
                amount = self._from_internal(amount_internal)
                
                desc = pay_desc if pay_desc else ""
                if count == 1:
                    if desc and item_desc:
                        desc = f"{desc} - {item_desc}"
                    elif item_desc:
                        desc = item_desc
                else:
                    if not desc:
                        desc = f"Transaction ({count} items)"

                date_item = QTableWidgetItem(QDate.fromString(date, "yyyy-MM-dd").toString("MM/dd/yyyy"))
                date_item.setData(Qt.UserRole, tx_id)
                table.setItem(row, 0, date_item)
                table.setItem(row, 1, QTableWidgetItem(type_))
                table.setItem(row, 2, QTableWidgetItem(acc_name))
                table.setItem(row, 3, QTableWidgetItem(desc))
                
                if type_ == "Payment": # Use formatter, without symbol, then add prefix
                    amt_item = QTableWidgetItem(f"- {self._format_number_as_currency(amount, include_symbol=False)}")
                    amt_item.setForeground(QColor("#ff3333"))
                elif type_ == "Receipt": # Use formatter, without symbol, then add prefix
                    amt_item = QTableWidgetItem(f"+ {self._format_number_as_currency(amount, include_symbol=False)}")
                    amt_item.setForeground(QColor("#00ff00"))
                else: # Default case, use formatter with symbol
                    amt_item = QTableWidgetItem(self._format_number_as_currency(amount))
                
                amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 4, amt_item)

                # Actions Container
                actions_widget = QWidget()
                actions_widget.setStyleSheet("background-color: transparent; border: none;")
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                actions_layout.setSpacing(5)

                btn_style = """
                    QPushButton {
                        background-color: #444444; color: #ffffff; border: 1px solid #666666;
                        border-radius: 4px; font-size: 12px; padding: 4px 8px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #555555; border-color: #999999; color: white; }
                """

                view_btn = QPushButton("View")
                view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                view_btn.setStyleSheet(btn_style)
                current_tx_id = row_data[0]
                view_btn.clicked.connect(lambda checked, tx_id=current_tx_id: self._open_transaction_detail_by_id(tx_id, "view"))
                actions_layout.addWidget(view_btn)

                edit_btn = QPushButton("Edit")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.setStyleSheet(btn_style)
                edit_btn.clicked.connect(lambda checked, tx_id=current_tx_id: self._open_transaction_detail_by_id(tx_id, "edit"))
                actions_layout.addWidget(edit_btn)

                table.setCellWidget(row, 5, actions_widget)

        if page_type == "Payment" and hasattr(self, 'payments_page_num'):
            self.payments_prev_btn.setEnabled(self.payments_page_num > 1)
            self.payments_next_btn.setEnabled(len(transactions) == 50)
        elif page_type == "Receipt" and hasattr(self, 'receipts_page_num'):
            self.receipts_prev_btn.setEnabled(self.receipts_page_num > 1)
            self.receipts_next_btn.setEnabled(len(transactions) == 50)
        elif page_type == "Transfer" and hasattr(self, 'transfers_page_num'):
            self.transfers_prev_btn.setEnabled(self.transfers_page_num > 1)
            self.transfers_next_btn.setEnabled(len(transactions) == 50)

    def _create_transaction_list_view(self, layout, page_name):
        """Creates a generic list view for transactions."""
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title = QLabel(f"All {page_name}")
        title.setStyleSheet(f"font-size: {self.s(20)}px; font-weight: bold; color: white; margin-bottom: {self.s(10)}px;")
        layout.addWidget(title)

        # Top Controls Row
        top_controls_layout = QHBoxLayout()
        top_controls_layout.setContentsMargins(0, 0, 0, 10)
        
        # Search Bar
        search_input = QLineEdit()
        search_input.setPlaceholderText(f"Search {page_name}...")
        search_input.setFixedWidth(self.s(300))
        search_input.setStyleSheet(f"padding: {self.s(8)}px; background-color: #333; color: white; border: 1px solid #555; border-radius: {self.s(4)}px;")
        top_controls_layout.addWidget(search_input)
        
        # Pagination UI setup
        page_num = 1
        prev_btn = QPushButton("<<")
        next_btn = QPushButton(">>")
        page_lbl = QLabel("Page 1")
        
        for btn in [prev_btn, next_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: #333; color: white; border: 1px solid #555; border-radius: {self.s(4)}px; padding: {self.s(5)}px {self.s(10)}px; }}
                QPushButton:hover {{ background-color: #444; }}
                QPushButton:disabled {{ background-color: #222; color: #555; border-color: #333; }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        prev_btn.setEnabled(False)
        
        top_controls_layout.addSpacing(self.s(20))
        top_controls_layout.addWidget(prev_btn)
        top_controls_layout.addWidget(page_lbl)
        top_controls_layout.addWidget(next_btn)
        top_controls_layout.addStretch()
        layout.addLayout(top_controls_layout)

        if page_name == "Receipts":
            self.receipts_search_input = search_input
            self.receipts_page_num = page_num
            self.receipts_prev_btn = prev_btn
            self.receipts_next_btn = next_btn
            self.receipts_page_lbl = page_lbl
            
            def on_receipts_search():
                if hasattr(self, 'receipts_page_num'):
                    self.receipts_page_num = 1
                    self.receipts_page_lbl.setText("Page 1")
                self._load_all_transactions("Receipt")
            search_input.textChanged.connect(on_receipts_search)
            prev_btn.clicked.connect(self._receipts_prev_page)
            next_btn.clicked.connect(self._receipts_next_page)
            
        elif page_name == "Payments":
            self.payments_search_input = search_input
            self.payments_page_num = page_num
            self.payments_prev_btn = prev_btn
            self.payments_next_btn = next_btn
            self.payments_page_lbl = page_lbl
            
            def on_payments_search():
                if hasattr(self, 'payments_page_num'):
                    self.payments_page_num = 1
                    self.payments_page_lbl.setText("Page 1")
                self._load_all_transactions("Payment")
            search_input.textChanged.connect(on_payments_search)
            prev_btn.clicked.connect(self._payments_prev_page)
            next_btn.clicked.connect(self._payments_next_page)
            
        elif page_name == "Transfers":
            self.transfers_search_input = search_input
            self.transfers_page_num = page_num
            self.transfers_prev_btn = prev_btn
            self.transfers_next_btn = next_btn
            self.transfers_page_lbl = page_lbl
            
            def on_transfers_search():
                if hasattr(self, 'transfers_page_num'):
                    self.transfers_page_num = 1
                    self.transfers_page_lbl.setText("Page 1")
                self._load_all_transactions("Transfer")
            search_input.textChanged.connect(on_transfers_search)
            prev_btn.clicked.connect(self._transfers_prev_page)
            next_btn.clicked.connect(self._transfers_next_page)

        table = QTableWidget()
        table.setColumnCount(6)
        
        if page_name == "Transfers":
            table.setHorizontalHeaderLabels(["Date", "Type", "Account (From/To)", "Description", "Amount", "Actions"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(0, self.s(140))
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(1, self.s(100))
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(4, self.s(160))
            table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(5, self.s(160))
        else:
            table.setHorizontalHeaderLabels(["Date", "Type", "Account", "Description", "Amount", "Actions"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(0, self.s(140))
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(1, self.s(100))
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(4, self.s(160))
            table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(5, self.s(160))
        
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(self.s(40))
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setShowGrid(False)
        
        table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: #2b2b2b; 
                alternate-background-color: #383838; 
                border: none; 
                color: white;
                font-size: {self.s(16)}px;
                font-weight: bold;
            }}
            QHeaderView::section {{ 
                background-color: #444; 
                color: white; 
                padding: {self.s(5)}px; 
                border: 1px solid #555;
                font-size: {self.s(16)}px;
                font-weight: bold;
            }}
            QTableWidget::item {{ padding: {self.s(5)}px; }}
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
        
        frame = QFrame()
        frame.setStyleSheet(".QFrame { border: 1px solid #ff9800; border-radius: 4px; }")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.addWidget(table)
        layout.addWidget(frame)

        return table

    def _payments_prev_page(self):
        if hasattr(self, 'payments_page_num') and self.payments_page_num > 1:
            self.payments_page_num -= 1
            self.payments_page_lbl.setText(f"Page {self.payments_page_num}")
            self._load_all_transactions("Payment")

    def _payments_next_page(self):
        if hasattr(self, 'payments_page_num'):
            self.payments_page_num += 1
            self.payments_page_lbl.setText(f"Page {self.payments_page_num}")
            self._load_all_transactions("Payment")

    def _receipts_prev_page(self):
        if hasattr(self, 'receipts_page_num') and self.receipts_page_num > 1:
            self.receipts_page_num -= 1
            self.receipts_page_lbl.setText(f"Page {self.receipts_page_num}")
            self._load_all_transactions("Receipt")

    def _receipts_next_page(self):
        if hasattr(self, 'receipts_page_num'):
            self.receipts_page_num += 1
            self.receipts_page_lbl.setText(f"Page {self.receipts_page_num}")
            self._load_all_transactions("Receipt")

    def _transfers_prev_page(self):
        if hasattr(self, 'transfers_page_num') and self.transfers_page_num > 1:
            self.transfers_page_num -= 1
            self.transfers_page_lbl.setText(f"Page {self.transfers_page_num}")
            self._load_all_transactions("Transfer")

    def _transfers_next_page(self):
        if hasattr(self, 'transfers_page_num'):
            self.transfers_page_num += 1
            self.transfers_page_lbl.setText(f"Page {self.transfers_page_num}")
            self._load_all_transactions("Transfer")

    def _account_ledger_prev_page(self):
        if hasattr(self, 'account_ledger_page_num') and self.account_ledger_page_num > 1:
            self.account_ledger_page_num -= 1
            self.account_ledger_page_lbl.setText(f"Page {self.account_ledger_page_num}")
            self._load_account_ledger(self.current_view_account_id)

    def _account_ledger_next_page(self):
        if hasattr(self, 'account_ledger_page_num'):
            self.account_ledger_page_num += 1
            self.account_ledger_page_lbl.setText(f"Page {self.account_ledger_page_num}")
            self._load_account_ledger(self.current_view_account_id)

    def _show_account_form(self):
        """Shows the account creation form and hides the create button."""
        self.create_account_btn.setVisible(False)
        self.account_form_container.setVisible(True)
        self.account_input.setFocus()

    def _hide_account_form(self):
        """Hides the account creation form and shows the create button."""
        self.account_form_container.setVisible(False)
        self.create_account_btn.setVisible(True)
        self.account_input.clear()

    def _add_account(self):
        """Adds a new account to the database and table."""
        name = self.account_input.text().strip()
        if name:
            # Save to DB
            self.db.create_account(name, 0)
            
            # Reload table to include new account and update total row
            self._load_accounts()
            
            self.account_input.clear()
            self._hide_account_form()


    def _setup_account_detail_page(self, page):
        """Sets up the layout for the account editing page."""
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Back Button
        back_btn = QPushButton("← Back to Account")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(f"background-color: transparent; color: #aaaaaa; border: none; text-align: left; font-size: {self.s(14)}px; margin-bottom: {self.s(20)}px;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.account_view_page))
        layout.addWidget(back_btn)

        # Title
        title = QLabel("Edit Account")
        title.setStyleSheet(f"font-size: {self.s(24)}px; font-weight: bold; color: white; margin-bottom: {self.s(20)}px;")
        layout.addWidget(title)

        # Rename Input
        lbl_name = QLabel("Account Name")
        lbl_name.setStyleSheet(f"color: #cccccc; font-size: {self.s(14)}px;")
        layout.addWidget(lbl_name)

        self.edit_name_input = QLineEdit()
        self.edit_name_input.setFixedWidth(self.s(400))
        self.edit_name_input.setStyleSheet("padding: 10px; border: 1px solid #555; border-radius: 4px; background-color: #333; color: white; margin-bottom: 20px;")
        layout.addWidget(self.edit_name_input, alignment=Qt.AlignmentFlag.AlignLeft)

        # Save & Delete Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(self.s(15))
        
        # Save Button
        save_btn = QPushButton("Save Changes")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                background-color: transparent;
                color: #009688;
                border: 1px solid #009688;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #009688;
                color: white;
            }
        """)
        save_btn.clicked.connect(self._save_account_details)
        btn_row.addWidget(save_btn)

        # Delete Button
        delete_btn = QPushButton("Delete Account")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                background-color: #444;
                color: #ff5252;
                border: 1px solid #666;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #888;
                color: white;
            }
        """)
        delete_btn.clicked.connect(self._delete_account_from_detail)
        btn_row.addWidget(delete_btn)
        
        btn_row.addStretch()
        
        layout.addLayout(btn_row)

    def _setup_account_view_page(self, page):
        """Sets up the layout for the account view page."""
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Back Button
        back_btn = QPushButton("← Back to Accounts")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(f"background-color: transparent; color: #aaaaaa; border: none; text-align: left; font-size: {self.s(14)}px; margin-bottom: {self.s(20)}px;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)

        # Title
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        self.account_view_title = QLabel("Account Name")
        self.account_view_title.setStyleSheet(f"font-size: {self.s(24)}px; font-weight: bold; color: white;")
        header_layout.addWidget(self.account_view_title)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        # Top Controls Row
        top_controls_layout = QHBoxLayout()
        top_controls_layout.setContentsMargins(0, 0, 0, 10)

        # Search Bar
        self.account_view_search_input = QLineEdit()
        self.account_view_search_input.setPlaceholderText("Search transactions in this account...")
        self.account_view_search_input.setFixedWidth(self.s(300))
        self.account_view_search_input.setStyleSheet(f"padding: {self.s(8)}px; background-color: #333; color: white; border: 1px solid #555; border-radius: {self.s(4)}px;")
        
        def on_ledger_search():
            if hasattr(self, 'account_ledger_page_num'):
                self.account_ledger_page_num = 1
                self.account_ledger_page_lbl.setText("Page 1")
            self._load_account_ledger(self.current_view_account_id)
            
        self.account_view_search_input.textChanged.connect(on_ledger_search)
        top_controls_layout.addWidget(self.account_view_search_input)

        # Pagination for Ledger
        self.account_ledger_page_num = 1
        self.account_ledger_prev_btn = QPushButton("<<")
        self.account_ledger_next_btn = QPushButton(">>")
        self.account_ledger_page_lbl = QLabel("Page 1")
        
        for btn in [self.account_ledger_prev_btn, self.account_ledger_next_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: #333; color: white; border: 1px solid #555; border-radius: {self.s(4)}px; padding: {self.s(5)}px {self.s(10)}px; }}
                QPushButton:hover {{ background-color: #444; }}
                QPushButton:disabled {{ background-color: #222; color: #555; border-color: #333; }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.account_ledger_prev_btn.clicked.connect(self._account_ledger_prev_page)
        self.account_ledger_next_btn.clicked.connect(self._account_ledger_next_page)
        self.account_ledger_prev_btn.setEnabled(False)
        
        top_controls_layout.addSpacing(self.s(20))
        top_controls_layout.addWidget(self.account_ledger_prev_btn)
        top_controls_layout.addWidget(self.account_ledger_page_lbl)
        top_controls_layout.addWidget(self.account_ledger_next_btn)

        top_controls_layout.addSpacing(self.s(12))

        settings_btn = QPushButton("⚙")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setToolTip("Account Settings")
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #aaaaaa;
                border: none;
                font-size: {self.s(26)}px;
            }}
            QPushButton:hover {{
                color: #ffffff;
            }}
        """)
        settings_btn.clicked.connect(self._open_account_settings_from_view)
        top_controls_layout.addWidget(settings_btn)

        top_controls_layout.addStretch()

        layout.addLayout(top_controls_layout)

        # Ledger Table
        self.ledger_table = QTableWidget()
        self.ledger_table.setColumnCount(6)
        self.ledger_table.setHorizontalHeaderLabels(["Date", "Type", "Description", "Amount", "Balance", "Actions"])
        self.ledger_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.ledger_table.setColumnWidth(0, self.s(140))
        self.ledger_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.ledger_table.setColumnWidth(1, self.s(140))
        self.ledger_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.ledger_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.ledger_table.setColumnWidth(3, self.s(160))
        self.ledger_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.ledger_table.setColumnWidth(4, self.s(160))
        self.ledger_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.ledger_table.setColumnWidth(5, self.s(160))
        
        self.ledger_table.verticalHeader().setVisible(False)
        self.ledger_table.verticalHeader().setDefaultSectionSize(self.s(40))
        self.ledger_table.setAlternatingRowColors(True)
        self.ledger_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ledger_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.ledger_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ledger_table.setShowGrid(False)
        
        self.ledger_table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: #2b2b2b; 
                alternate-background-color: #383838; 
                border: none; 
                color: white;
                font-size: {self.s(16)}px;
                font-weight: bold;
            }}
            QHeaderView::section {{ 
                background-color: #444; 
                color: white; 
                padding: {self.s(5)}px; 
                border: 1px solid #555;
                font-size: {self.s(16)}px;
                font-weight: bold;
            }}
            QTableWidget::item {{ padding: {self.s(5)}px; }}
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

        # Frame for Table Border
        ledger_frame = QFrame()
        ledger_frame.setStyleSheet(".QFrame { border: 1px solid #ff9800; border-radius: 4px; }")
        frame_layout = QVBoxLayout(ledger_frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.addWidget(self.ledger_table)

        layout.addWidget(ledger_frame)

    def _open_account_view(self):
        """Opens the view page for the selected account."""
        button = self.sender()
        if button:
            index = self.accounts_table.indexAt(button.pos())
            if index.isValid():
                row = index.row()
                name_item = self.accounts_table.item(row, 1)
                account_id = name_item.data(Qt.UserRole)
                self.current_view_account_id = account_id
                self.account_view_title.setText(name_item.text())
                if hasattr(self, 'account_ledger_page_num'):
                    self.account_ledger_page_num = 1
                    self.account_ledger_page_lbl.setText("Page 1")
                self._load_account_ledger(account_id)
                self.stacked_widget.setCurrentWidget(self.account_view_page)

    def _open_account_settings_from_view(self):
        """Opens the account detail page for the currently viewed account."""
        if self.current_view_account_id is not None:
            self.current_edit_id = self.current_view_account_id
            # Fetch current name
            self.cursor.execute("SELECT name FROM accounts WHERE id = ?", (self.current_edit_id,))
            row = self.cursor.fetchone()
            if row:
                self.edit_name_input.setText(row[0])
                self.stacked_widget.setCurrentWidget(self.account_detail_page)

    def _load_account_ledger(self, account_id):
        """Loads transactions for the specified account into the ledger table."""
        if account_id is None:
            self.ledger_table.setRowCount(0)
            return

        self.ledger_table.setRowCount(0)
        import gc
        gc.collect()
        
        # Fetch current balance
        self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
        res = self.cursor.fetchone()
        current_balance = res[0] if res else 0
        
        # 1. Fetch ALL transactions for the account, without search filtering
        self.cursor.execute("""
            SELECT 
                MAX(id), 
                date, 
                type, 
                payment_description, 
                MAX(description), 
                SUM(amount),
                COUNT(id),
                GROUP_CONCAT(description, ', ')
            FROM transactions 
            WHERE account_id = ? 
            GROUP BY CASE WHEN type IN ('Payment', 'Receipt') THEN txid ELSE id END, type, date
            ORDER BY date DESC, MAX(id) DESC
        """, (account_id,))
        
        transactions = self.cursor.fetchall()
        
        # 2. Process all transactions to calculate running balances
        running_balance = current_balance
        all_tx_data = []
        
        for tx_id, date, type_, pay_desc, item_desc, amount, count, all_desc in transactions:
            # Format Description
            desc = pay_desc if pay_desc else ""
            if count == 1:
                if desc and item_desc:
                    desc = f"{desc} - {item_desc}"
                elif item_desc:
                    desc = item_desc
            else:
                if not desc:
                    desc = f"Transaction ({count} items)"
            
            # Store data with its calculated running balance
            tx_data = {
                'tx_id': tx_id,
                'date': date,
                'type': type_,
                'desc': desc,
                'amount': amount,
                'balance': running_balance,
                'raw_pay_desc': pay_desc if pay_desc else "",
                'raw_item_desc': item_desc if item_desc else "",
                'all_desc': all_desc if all_desc else ""
            }
            all_tx_data.append(tx_data)
            
            # Update running balance for the *next* (older) transaction
            if type_ in ["Payment", "Transfer Out"]:
                running_balance += amount
            elif type_ in ["Receipt", "Transfer In"]:
                running_balance -= amount

        # 3. Filter transactions based on search input
        search_text = ""
        if hasattr(self, 'account_view_search_input'):
            search_text = self.account_view_search_input.text().strip().lower()

        if search_text:
            filtered_tx_data = []
            for tx in all_tx_data:
                if "Transfer" in tx['type']:
                    if search_text in tx['raw_item_desc'].lower():
                        filtered_tx_data.append(tx)
                else:
                    match_pay = search_text in tx['raw_pay_desc'].lower()
                    match_items = search_text in tx['all_desc'].lower()
                    
                    if match_pay or match_items:
                        # If matched on items and the search text isn't already visible in the description
                        if match_items and search_text not in tx['desc'].lower():
                            all_items = tx['all_desc'].split(',')
                            matches = [i.strip() for i in all_items if search_text in i.lower()]
                            if matches:
                                matched_str = ", ".join(matches)
                                if tx['raw_pay_desc']:
                                    tx['desc'] = f"{tx['raw_pay_desc']} - {matched_str}"
                                else:
                                    tx['desc'] = matched_str
                        filtered_tx_data.append(tx)
        else:
            filtered_tx_data = all_tx_data

        # 4. Apply Pagination
        total_matches = len(filtered_tx_data)
        limit = 50
        if hasattr(self, 'account_ledger_page_num'):
            start_idx = (self.account_ledger_page_num - 1) * limit
            end_idx = start_idx + limit
            page_data = filtered_tx_data[start_idx:end_idx]
            
            # Update buttons
            self.account_ledger_prev_btn.setEnabled(self.account_ledger_page_num > 1)
            self.account_ledger_next_btn.setEnabled(end_idx < total_matches)
        else:
            page_data = filtered_tx_data

        # 5. Populate the table with the filtered data
        for tx_data in page_data:
            row = self.ledger_table.rowCount()
            self.ledger_table.insertRow(row)

            date_item = QTableWidgetItem(QDate.fromString(tx_data['date'], "yyyy-MM-dd").toString("MM/dd/yyyy"))
            date_item.setData(Qt.UserRole, tx_data['tx_id'])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ledger_table.setItem(row, 0, date_item)
            
            display_type = tx_data['type']
            if "Transfer" in display_type:
                display_type = "Transfer"
            
            type_item = QTableWidgetItem(display_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ledger_table.setItem(row, 1, type_item)
            
            self.ledger_table.setItem(row, 2, QTableWidgetItem(tx_data['desc']))
            
            amount_internal = tx_data['amount']
            balance_internal = tx_data['balance']
            amount = self._from_internal(amount_internal)
            balance = self._from_internal(balance_internal)

            type_ = tx_data['type']
            if type_ == "Payment":
                amt_item = QTableWidgetItem(f"- {self._format_number_as_currency(amount, include_symbol=False)}")
                amt_item.setForeground(QColor("#ff3333"))
            elif type_ == "Receipt":
                amt_item = QTableWidgetItem(f"+ {self._format_number_as_currency(amount, include_symbol=False)}")
                amt_item.setForeground(QColor("#00ff00"))
            elif type_ == "Transfer Out":
                amt_item = QTableWidgetItem(f"- {self._format_number_as_currency(amount, include_symbol=False)}")
                amt_item.setForeground(QColor("#ffff00"))
                font = self._get_bold_font()
                font.setItalic(True)
                amt_item.setFont(font)
            elif type_ == "Transfer In":
                amt_item = QTableWidgetItem(f"+ {self._format_number_as_currency(amount, include_symbol=False)}")
                amt_item.setForeground(QColor("#ffff00"))
                font = self._get_bold_font()
                font.setItalic(True)
                amt_item.setFont(font)
            else:
                amt_item = QTableWidgetItem(self._format_number_as_currency(amount))
            
            amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ledger_table.setItem(row, 3, amt_item)

            # Balance Column
            bal_item = QTableWidgetItem(self._format_number_as_currency(balance))
            bal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ledger_table.setItem(row, 4, bal_item)

            # Actions Container
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent; border: none;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(5)

            btn_style = """
                QPushButton {
                    background-color: #444444;
                    color: #ffffff;
                    border: 1px solid #666666;
                    border-radius: 4px;
                    font-size: {self.s(12)}px;
                    padding: 4px 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #555555;
                    border-color: #999999;
                    color: white;
                }
            """

            view_btn = QPushButton("View")
            view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            view_btn.setStyleSheet(btn_style)
            view_btn.setProperty("action_type", "view")
            view_btn.clicked.connect(self._open_transaction_detail)
            actions_layout.addWidget(view_btn)

            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet(btn_style)
            edit_btn.setProperty("action_type", "edit")
            edit_btn.clicked.connect(self._open_transaction_detail)
            actions_layout.addWidget(edit_btn)

            self.ledger_table.setCellWidget(row, 5, actions_widget)

    def _open_account_detail(self):
        """Opens the detail page for the selected account."""
        button = self.sender()
        if button:
            # Button is inside a container widget, so we use the parent widget's position
            index = self.accounts_table.indexAt(button.parentWidget().pos())
            if index.isValid():
                row = index.row()
                name_item = self.accounts_table.item(row, 1)
                self.current_edit_id = name_item.data(Qt.UserRole)
                self.edit_name_input.setText(name_item.text())
                self.stacked_widget.setCurrentWidget(self.account_detail_page)

    def _open_payment_page_from_table(self):
        """Opens the payment page, pre-filling the selected account."""
        button = self.sender()
        if not button:
            return

        index = self.accounts_table.indexAt(button.parentWidget().pos())
        if not index.isValid():
            return

        row = index.row()
        name_item = self.accounts_table.item(row, 1)
        account_id = name_item.data(Qt.UserRole)
        account_name = name_item.text()

        self.current_payment_account_id = account_id
        
        self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
        res = self.cursor.fetchone()
        balance_internal = res[0] if res else 0
        balance = self._from_internal(balance_internal)
        self.payment_account_name_label.setText(f"{account_name} Account")
        self.payment_account_balance_label.setText(f"Current Balance: {self._format_number_as_currency(balance)}")
        
        # Reset Form
        self.payment_date.setDate(QDate.currentDate())
        self.payment_desc.clear()
        self.payment_item_table.clear_table()
        
        self.stacked_widget.setCurrentWidget(self.create_payment_page)

    def _open_payment_page_from_view(self):
        """Opens the payment page from the account view page."""
        if self.current_view_account_id:
            account_id = self.current_view_account_id
            account_name = self.account_view_title.text()

            self.current_payment_account_id = account_id
            # Use the formatter here
            self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
            res = self.cursor.fetchone()
            balance = self._from_internal(res[0]) if res else 0.0
            self.payment_account_name_label.setText(f"{account_name} Account")
            self.payment_account_balance_label.setText(f"Current Balance: {self.currency_symbol} {balance:,.{self.currency_decimals}f}")
            
            # Reset Form
            self.payment_date.setDate(QDate.currentDate())
            self.payment_desc.clear()
            self.payment_item_table.clear_table()
            
            self.stacked_widget.setCurrentWidget(self.create_payment_page)

    def _generate_payment_txid(self):
        """Generates the next sequential Payment ID."""
        self.cursor.execute("SELECT MAX(CAST(txid AS INTEGER)) FROM transactions WHERE type = 'Payment'")
        res = self.cursor.fetchone()
        next_id = (res[0] if res and res[0] is not None else 0) + 1
        return str(next_id)

    def _perform_payment(self):
        """Executes the payment transaction from the payment page."""
        if self.current_payment_account_id is None:
            self._show_modern_message("No Account Selected", "Please select an account to make a payment.", QMessageBox.Icon.Warning)
            return

        total_amount = self.payment_item_table.get_total()
        if total_amount <= 0:
            self._show_modern_message("Invalid Amount", "Total payment amount must be greater than zero.", QMessageBox.Icon.Warning)
            return

        try:
            date_str = self.payment_date.date().toString("yyyy-MM-dd")
            txid = self._generate_payment_txid()
            payment_desc = self.payment_desc.text().strip()
            
            items = self.payment_item_table.get_items()
            internal_items = []
            for item in items:
                internal_items.append({
                    'description': item['description'],
                    'quantity': item['quantity'],
                    'total': self._to_internal(item['total'])
                })
            
            self.db.create_payment(self.current_payment_account_id, date_str, payment_desc, internal_items, txid)

            self._load_accounts()
            self.stacked_widget.setCurrentIndex(0) # Go back to accounts page
            
            # Reset Form
            self.current_payment_account_id = None # Clear selected account
            self.payment_account_name_label.setText("Select an account") # Reset label
            self.payment_account_balance_label.setText("")
            self.payment_item_table.clear_table()

        except ValueError as e:
            self._show_modern_message("Warning", str(e), QMessageBox.Icon.Warning)
        except Exception as e:
            self._show_modern_message("Error", f"An error occurred during payment: {e}", QMessageBox.Icon.Critical)

    def _open_transfer_dialog(self):
        """Opens a dialog to transfer funds from the selected account."""
        button = self.sender()
        if not button:
            return
            
        # Get the row index from the button's parent widget
        index = self.accounts_table.indexAt(button.parentWidget().pos())
        if not index.isValid():
            return
            
        row = index.row()
        name_item = self.accounts_table.item(row, 1)
        from_id = name_item.data(Qt.UserRole)
        from_name = name_item.text()
        
        # Fetch current balance for display
        self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (from_id,))
        res = self.cursor.fetchone()
        current_balance_internal = res[0] if res else 0
        current_balance = self._from_internal(current_balance_internal)
        
        # Create Dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Transfer Funds")
        dialog.setFixedSize(self.s(600), self.s(700))
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: #2b2b2b; border: 1px solid #ff9800; border-radius: {self.s(15)}px; }}
            QWidget {{ background-color: #2b2b2b; color: white; }}
            QLabel {{ color: white; border: none; background-color: transparent; }}
            QCheckBox {{ color: white; background-color: #2b2b2b; font-size: {self.s(16)}px; }}
            QComboBox {{ padding: {self.s(5)}px; background-color: #333333; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(16)}px; }}
            QComboBox:hover {{ background-color: #444444; border-color: #888; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{ image: none; }}
            QComboBox QAbstractItemView {{ background-color: #333333; color: white; outline: none; border: 1px solid #ff9800; font-size: {self.s(16)}px; }}
            QComboBox QAbstractItemView::item {{ padding: {self.s(5)}px; color: white; }}
            QComboBox QAbstractItemView::item:hover {{ background-color: #555; }}
            QComboBox QAbstractItemView::item:selected {{ background-color: #555; color: white; border: 1px solid white; }}
            QAbstractSpinBox {{ padding: {self.s(5)}px; background-color: #2b2b2b; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(16)}px; }}
            QScrollArea {{ border: none; background-color: #2b2b2b; }}
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
        
        layout = QVBoxLayout(dialog)
        
        # From Label
        lbl_from = QLabel(f"{from_name}\nCurrent Balance: {self.currency_symbol} {current_balance:,.{self.currency_decimals}f}")
        lbl_from.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: white;")
        layout.addWidget(lbl_from)

        # Description Input
        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Description (Optional)")
        desc_input.setStyleSheet(f"padding: {self.s(5)}px; background-color: #333333; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(16)}px;")
        layout.addWidget(desc_input)

        # Budget Transfer Checkbox
        budget_cb = QCheckBox("Budget Transfer (Multi-Account)")
        budget_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(budget_cb)

        # Stack for Single vs Multi
        stack = QStackedWidget()
        
        # --- Single Transfer Page ---
        single_widget = QWidget()
        single_layout = QFormLayout(single_widget)
        single_layout.setContentsMargins(0, 10, 0, 0)
        
        # To Combo
        combo_to = QComboBox()
        combo_to.setView(QListView())
        combo_to.setStyleSheet(f"""
            QComboBox {{ padding: {self.s(8)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px; }}
            QComboBox QAbstractItemView {{ background-color: #2b2b2b; color: white; outline: none; border: 1px solid #444; font-size: {self.s(18)}px; }}
            QComboBox QAbstractItemView::item {{ padding: {self.s(10)}px; color: white; }}
            QComboBox QAbstractItemView::item:hover {{ background-color: #333; }}
            QComboBox QAbstractItemView::item:selected {{ background-color: #ff9800; color: black; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{ image: none; }}
        """)
        
        # Populate To Combo (exclude current account)
        self.cursor.execute("SELECT id, name FROM accounts WHERE id != ?", (from_id,))
        accounts = self.cursor.fetchall()
        
        if not accounts:
            self._show_modern_message("No Accounts", "No other accounts available to transfer to.", QMessageBox.Icon.Warning)
            return

        for acc_id, acc_name in accounts:
            combo_to.addItem(acc_name, acc_id)
            
        to_acc_lbl = QLabel("To Account:")
        to_acc_lbl.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        single_layout.addRow(to_acc_lbl, combo_to)
        
        # Amount SpinBox
        amount_spin = QuantitySpinBox()
        amount_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        amount_spin.setRange(0.00, 1000000000000000.00)
        amount_spin.setSpecialValueText(" ")
        amount_spin.setDecimals(self.currency_decimals)
        amt_lbl = QLabel("Amount:")
        amt_lbl.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        single_layout.addRow(amt_lbl, amount_spin)
        
        stack.addWidget(single_widget)

        # --- Multi Transfer Page ---
        multi_widget = QWidget()
        multi_layout = QVBoxLayout(multi_widget)
        multi_layout.setContentsMargins(0, 10, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #2b2b2b;")
        scroll_form = QFormLayout(scroll_content)
        
        multi_inputs = {} # Map acc_id -> (spinbox, pct_label, acc_name)
        
        total_lbl = QLabel(f"Total: {self.currency_symbol} 0.00")
        total_lbl.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: white; margin-top: {self.s(10)}px; border-top: 1px solid #555; padding-top: {self.s(5)}px;")
        total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        remaining_lbl = QLabel(f"Remaining: {self.currency_symbol} {current_balance:,.{self.currency_decimals}f}")
        remaining_lbl.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: white;")
        remaining_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        def update_budget_totals():
            total = 0.0
            
            # Calculate total
            for _, (spin, _, _) in multi_inputs.items():
                total += spin.value()
            
            remaining = current_balance - total

            total_lbl.setText(f"Total: {self.currency_symbol} {total:,.{self.currency_decimals}f}")
            remaining_lbl.setText(f"Remaining: {self.currency_symbol} {remaining:,.{self.currency_decimals}f}")
            
            if remaining < 0:
                remaining_lbl.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: #ff5252;")
            else:
                remaining_lbl.setStyleSheet(f"font-size: {self.s(18)}px; font-weight: bold; color: white;")
            
            for _, (spin, lbl, _) in multi_inputs.items():
                val = spin.value()
                if total > 0:
                    pct = (val / total) * 100
                    lbl.setText(self._format_percentage(pct))
                else:
                    lbl.setText("0.00%")

        for acc_id, acc_name in accounts:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            m_spin = QuantitySpinBox()
            m_spin.setFixedWidth(self.s(240))
            m_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            m_spin.setRange(0.00, 1000000000000000.00)
            m_spin.setDecimals(self.currency_decimals)
            m_spin.setSpecialValueText(" ")
            m_spin.valueChanged.connect(update_budget_totals)
            
            pct_lbl = QLabel("0.00%")
            pct_lbl.setFixedWidth(self.s(85))
            pct_lbl.setStyleSheet(f"color: white; font-weight: bold; margin-left: {self.s(10)}px; font-size: {self.s(16)}px;")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            row_layout.addWidget(m_spin)
            row_layout.addSpacing(self.s(5))
            row_layout.addWidget(pct_lbl)
            
            name_label = QLabel(f"{acc_name}:")
            name_label.setStyleSheet(f"color: white; font-size: {self.s(18)}px;")
            scroll_form.addRow(name_label, row_widget)
            multi_inputs[acc_id] = (m_spin, pct_lbl, acc_name)
            
        scroll.setWidget(scroll_content)
        multi_layout.addWidget(scroll)
        
        def clear_budget_inputs():
            for _, (spin, _, _) in multi_inputs.items():
                spin.setValue(0.0)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"QPushButton {{ background-color: #444; color: white; border: 1px solid #666; padding: {self.s(4)}px {self.s(10)}px; border-radius: {self.s(4)}px; margin-top: {self.s(5)}px; font-size: {self.s(14)}px; }} QPushButton:hover {{ background-color: #555; }}")
        clear_btn.clicked.connect(clear_budget_inputs)
        multi_layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        multi_layout.addWidget(total_lbl)
        multi_layout.addWidget(remaining_lbl)
        
        stack.addWidget(multi_widget)
        layout.addWidget(stack)
        
        # Logic to switch views
        budget_cb.stateChanged.connect(lambda: stack.setCurrentIndex(1 if budget_cb.isChecked() else 0))
        
        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("Transfer")
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setObjectName("ok_btn")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("cancel_btn")
        
        for btn in btn_box.buttons():
            btn.setIcon(QIcon())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_box.setStyleSheet(f"""
            QPushButton#ok_btn {{ 
                background-color: #2d5a27; 
                color: white; 
                border: 1px solid #3d8c34; 
                padding: {self.s(8)}px {self.s(16)}px; 
                border-radius: {self.s(4)}px; 
                font-size: {self.s(16)}px; 
                font-weight: bold;
            }}
            QPushButton#ok_btn:hover {{ background-color: #3d8c34; }}
            
            QPushButton#cancel_btn {{ 
                background-color: #8a2b2b; 
                color: white; 
                border: 1px solid #b71c1c; 
                padding: {self.s(8)}px {self.s(16)}px; 
                border-radius: {self.s(4)}px; 
                font-size: {self.s(16)}px; 
                font-weight: bold;
            }}
            QPushButton#cancel_btn:hover {{ background-color: #b71c1c; }}
        """)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        if dialog.exec() == QDialog.Accepted:
            # Check Balance First
            self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (from_id,))
            res = self.cursor.fetchone()
            current_balance_internal = res[0] if res else 0
            current_balance = self._from_internal(current_balance_internal)
            user_desc = desc_input.text().strip()

            if budget_cb.isChecked():
                # Multi Transfer
                total_needed = 0.0
                transfers_to_make = []
                
                for acc_id, (spin, _, _) in multi_inputs.items():
                    val = spin.value()
                    if val > 0:
                        total_needed += val
                        transfers_to_make.append((acc_id, val))
                
                if total_needed == 0:
                    return # Nothing to do
                # Use a small epsilon for floating-point comparison to avoid precision issues
                epsilon = 1e-9
                if current_balance < total_needed - epsilon:
                    QMessageBox.warning(self, "Insufficient Funds", f"Total amount {self.currency_symbol} {total_needed:,.{self.currency_decimals}f} exceeds current balance {self.currency_symbol} {current_balance:,.{self.currency_decimals}f}.")
                    return
                
                # Perform Transfers
                for target_id, amt in transfers_to_make:
                    self._perform_transfer(from_id, target_id, amt, description=user_desc, silent=True)
                
                self._show_modern_message("Success", "Budget transfer completed successfully.")
            else:
                # Single Transfer
                to_id = combo_to.currentData()
                amount = amount_spin.value()
                
                if to_id is not None and amount > 0:
                    # Use a small epsilon for floating-point comparison to avoid precision issues
                    epsilon = 1e-9
                    if current_balance < amount - epsilon:
                        return
                    self._perform_transfer(from_id, to_id, amount, description=user_desc)
            # _load_accounts() is called by _perform_transfer if not silent, or after the loop for multi-transfers.
    def _perform_transfer(self, from_id, to_id, amount, description="", silent=False):
        """Executes the transfer transaction."""
        try:
            amount_internal = self._to_internal(amount)
            self.db.create_transfer(from_id, to_id, amount_internal, description)
            
            self._load_accounts()
            if not silent:
                self._show_modern_message("Success", "Transfer completed successfully.")
            
        except ValueError:
            return # Transfer catches value errs implicitly
        except Exception as e:
            self._show_modern_message("Error", f"An error occurred: {e}", QMessageBox.Icon.Critical)

    def _save_account_details(self):
        """Saves the renamed account and returns to the account view."""
        new_name = self.edit_name_input.text().strip()
        if new_name and self.current_edit_id is not None:
            self.db.update_account_name(self.current_edit_id, new_name)
            self._load_accounts()
            self.account_view_title.setText(new_name)
            self.stacked_widget.setCurrentWidget(self.account_view_page)

    def _delete_account_from_detail(self):
        """Deletes the current account and returns to the list."""
        if self.current_edit_id is not None:
            reply = self._show_modern_message(
                "Confirm Delete", 
                "Are you sure you want to delete this account?", 
                QMessageBox.Icon.Question, 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.Yes:
                self.db.delete_account(self.current_edit_id)
                self._load_accounts()
                self.stacked_widget.setCurrentIndex(0)


    def _create_status_bar(self):
        """Initializes the status bar at the bottom of the window."""
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { background-color: #1e1e1e; border: none; border-top: 1px solid #333333; } QStatusBar::item { border: none; }")
        self.setStatusBar(self.status_bar)
        
        # Container to hold version label and buttons together
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(self.s(10), 0, self.s(10), 0)
        bottom_layout.setSpacing(self.s(8))
        
        self.version_label = QLabel(APP_VERSION)
        self.version_label.setStyleSheet(f"color: #dddddd; font-size: {self.s(12)}px; font-weight: bold;")
        bottom_layout.addWidget(self.version_label)
        
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
        self.check_updates_btn.clicked.connect(lambda: self._safe_open_url("https://dockport.github.io/tallybook"))
        bottom_layout.addWidget(self.check_updates_btn)
        
        bottom_layout.addStretch()
        
        self.status_bar.addWidget(bottom_container)

    def _safe_open_url(self, url):
        """Opens a URL in the system browser while escaping the AppImage environment isolation."""
        try:
            # We must escape the AppImage's internal library path so that the browser
            # can use the host system's native libraries.
            env = os.environ.copy()
            if "LD_LIBRARY_PATH" in env:
                del env["LD_LIBRARY_PATH"]
            
            # Using subprocess.Popen instead of QDesktopServices to ensure the 
            # environment change is respected.
            subprocess.Popen(["xdg-open", url], env=env)
        except Exception:
            # Fallback to standard Qt method if xdg-open fails
            QDesktopServices.openUrl(QUrl(url))

    def _on_report_bug_clicked(self):
        """Action when clicking the Report a Bug button."""
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle("Report a Bug / Feedback")
        dialog.setFixedSize(self.s(640), self.s(280))
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #1e1e1e;
                border: 1px solid #ff9800;
                border-radius: {self.s(8)}px;
            }}
            QLabel {{
                color: #ffffff;
                font-family: 'Fira Code', monospace;
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.s(20), self.s(15), self.s(20), self.s(15))
        layout.setSpacing(self.s(10))
        
        # Message
        message = QLabel(
            "Report any bugs or share your feedback to help us improve TallyBook!\n\n"
            f"Please include your version number ({APP_VERSION})."
        )
        message.setWordWrap(True)
        message.setStyleSheet(f"font-size: {self.s(15)}px; line-height: 1.4; color: #ffffff;")
        layout.addWidget(message)
        
        # Details Container
        details_container = QWidget()
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(self.s(10))
        
        # GitHub link row
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(self.s(8))
        
        lbl = QLabel("GitHub:")
        lbl.setStyleSheet(f"font-size: {self.s(15)}px; font-weight: bold; color: #ff9800; min-width: {self.s(80)}px;")
        row_layout.addWidget(lbl)
        
        github_url = "https://github.com/DOCKPORT/TallyBook"
        link_label = QLabel(f'<a href="{github_url}" style="color: #58a6ff; text-decoration: none;">{github_url}</a>')
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet(f"font-size: {self.s(14)}px; background: transparent;")
        row_layout.addWidget(link_label, 1)
        
        details_layout.addWidget(row_widget)
        
        # Email row
        email_row = QWidget()
        email_layout = QHBoxLayout(email_row)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.setSpacing(self.s(8))
        
        email_lbl = QLabel("Email:")
        email_lbl.setStyleSheet(f"font-size: {self.s(15)}px; font-weight: bold; color: #ff9800; min-width: {self.s(80)}px;")
        email_layout.addWidget(email_lbl)
        
        email_address = "DOCKPORT_DEV@PROTONMAIL.COM"
        addr_field = QLineEdit(email_address)
        addr_field.setReadOnly(True)
        addr_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: {self.s(4)}px;
                padding: {self.s(6)}px;
                font-size: {self.s(14)}px;
                font-family: 'Fira Code', monospace;
            }}
        """)
        email_layout.addWidget(addr_field, 1)
        
        copy_btn = QPushButton("Copy")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setFixedWidth(self.s(75))
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: {self.s(4)}px;
                font-size: {self.s(12)}px;
                font-weight: bold;
                padding: {self.s(6)}px {self.s(12)}px;
            }}
            QPushButton:hover {{
                background-color: #4caf50;
                border-color: #4caf50;
            }}
        """)
        
        def on_copy():
            clipboard = QApplication.clipboard()
            clipboard.setText(email_address)
            
            copy_btn.setText("✅")
            copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2e7d32;
                    color: #ffffff;
                    border: 1px solid #1b5e20;
                    border-radius: {self.s(4)}px;
                    font-size: {self.s(12)}px;
                    font-weight: bold;
                    padding: {self.s(6)}px {self.s(12)}px;
                }}
            """)
            
            def reset_style():
                copy_btn.setText("Copy")
                copy_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #333333;
                        color: #ffffff;
                        border: 1px solid #555555;
                        border-radius: {self.s(4)}px;
                        font-size: {self.s(12)}px;
                        font-weight: bold;
                        padding: {self.s(6)}px {self.s(12)}px;
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

    def _on_donate_clicked(self):
        """Action when clicking the Donate button."""
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle("Support TallyBook")
        dialog.setFixedSize(self.s(850), self.s(410))
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #1e1e1e;
                border: 1px solid #ff9800;
                border-radius: {self.s(8)}px;
            }}
            QLabel {{
                color: #ffffff;
                font-family: 'Fira Code', monospace;
            }}
        """)
        
        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(self.s(20), self.s(20), self.s(20), self.s(20))
        main_layout.setSpacing(self.s(25))
        
        # Left Side (Message and Details)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(self.s(12))
        
        # Message
        message = QLabel(
            "If you find TallyBook useful, you can support it's development!\n\n"
            "Your contributions help us build new features and improve stability." 
        ) 
        message.setWordWrap(True)
        message.setStyleSheet(f"font-size: {self.s(15)}px; line-height: 1.4; color: #ffffff;")
        left_layout.addWidget(message)
        
        # Details Container
        details_container = QWidget()
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(self.s(10))
        
        def create_address_row(network, address):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(self.s(8))
            
            lbl = QLabel(f"{network}:")
            lbl.setStyleSheet(f"font-size: {self.s(15)}px; font-weight: bold; color: #ff9800; min-width: {self.s(80)}px;")
            row_layout.addWidget(lbl)
            
            addr_field = QLineEdit(address)
            addr_field.setReadOnly(True)
            addr_field.setStyleSheet(f"""
                QLineEdit {{
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: {self.s(4)}px;
                    padding: {self.s(6)}px;
                    font-size: {self.s(14)}px;
                    font-family: 'Fira Code', monospace;
                }}
            """)
            row_layout.addWidget(addr_field, 1)
            
            copy_btn = QPushButton("Copy")
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setFixedWidth(self.s(75))
            copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #333333;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: {self.s(4)}px;
                    font-size: {self.s(12)}px;
                    font-weight: bold;
                    padding: {self.s(6)}px {self.s(12)}px;
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
                        border-radius: {self.s(4)}px;
                        font-size: {self.s(12)}px;
                        font-weight: bold;
                        padding: {self.s(6)}px {self.s(12)}px;
                    }}
                """)
                
                def reset_style():
                    copy_btn.setText("Copy")
                    copy_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #333333;
                            color: #ffffff;
                            border: 1px solid #555555;
                            border-radius: {self.s(4)}px;
                            font-size: {self.s(12)}px;
                            font-weight: bold;
                            padding: {self.s(6)}px {self.s(12)}px;
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
            
        details_layout.addWidget(create_address_row("Bitcoin", "bc1qltty5ezggulw7nkl2dx3vmxvg6flyg5lajpjlp"))
        details_layout.addWidget(create_address_row("Solana", "2VQucWV3Qe99zKN8wZKfhrTH2YAfs3SCUk6oHr6eBYpF"))
        details_layout.addWidget(create_address_row("Contact", "DOCKPORT_DEV@PROTONMAIL.COM"))
        
        left_layout.addWidget(details_container)
        main_layout.addWidget(left_widget, 1)
        
        # Right Side (QR Codes)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(self.s(15))
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        def create_qr_box(network_name, pixmap_path):
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(0, 0, 0, 0)
            box_layout.setSpacing(self.s(4))
            box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            lbl = QLabel(f"{network_name} QR")
            lbl.setStyleSheet(f"font-size: {self.s(13)}px; font-weight: bold; color: #ff9800;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box_layout.addWidget(lbl)
            
            qr_label = QLabel()
            pixmap = QPixmap(paths.resource_path(pixmap_path))
            if not pixmap.isNull():
                qr_label.setPixmap(pixmap.scaled(self.s(130), self.s(130), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                qr_label.setText("QR not found")
            qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box_layout.addWidget(qr_label)
            return box
            
        right_layout.addWidget(create_qr_box("Bitcoin", "assets/QR/BTC_QR.png"))
        right_layout.addWidget(create_qr_box("Solana", "assets/QR/SOL_QR.png"))
        
        main_layout.addWidget(right_widget)
        
        dialog.exec()



    def _generate_receipt_txid(self):
        """Generates the next sequential Receipt ID."""
        self.cursor.execute("SELECT MAX(CAST(txid AS INTEGER)) FROM transactions WHERE type = 'Receipt'")
        res = self.cursor.fetchone()
        next_id = (res[0] if res and res[0] is not None else 0) + 1
        self.receipt_txid.setText(str(next_id))

    def _perform_receipt(self):
        account_id = self.receipt_account_combo.currentData()
        if account_id is None:
            self._show_modern_message("No Account Selected", "Please select an account to deposit the receipt.", QMessageBox.Icon.Warning)
            return

        total_amount = self.receipt_item_table.get_total()
        if total_amount <= 0:
            self._show_modern_message("Invalid Amount", "Total receipt amount must be greater than zero.", QMessageBox.Icon.Warning)
            return

        try:
            date_str = self.receipt_date.date().toString("yyyy-MM-dd")
            txid = self.receipt_txid.text().strip()
            receipt_desc = self.receipt_desc.text().strip()
            
            items = self.receipt_item_table.get_items()
            internal_items = []
            for item in items:
                internal_items.append({
                    'description': item['description'],
                    'quantity': item['quantity'],
                    'total': self._to_internal(item['total'])
                })
                
            self.db.create_receipt(account_id, date_str, receipt_desc, internal_items, txid)

            self._load_accounts()
            self._show_modern_message("Success", f"Receipt of {self.currency_symbol} {total_amount:,.{self.currency_decimals}f} recorded successfully.")
            self.stacked_widget.setCurrentIndex(0) # Go back to accounts page
            
            # Reset Form
            self.receipt_desc.clear()
            self.receipt_item_table.clear_table()
            self._generate_receipt_txid()

        except ValueError as e:
            self._show_modern_message("Warning", str(e), QMessageBox.Icon.Warning)
        except Exception as e:
            self._show_modern_message("Error", f"An error occurred during receipt: {e}", QMessageBox.Icon.Critical)

    def _setup_transaction_detail_page(self, page):
        """Sets up the layout for the transaction editing page."""
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Back Button
        back_btn = QPushButton("← Back to Account Ledger")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("background-color: transparent; color: #aaaaaa; border: none; text-align: left; font-size: 14px; margin-bottom: 20px;")
        back_btn.clicked.connect(self._return_from_transaction_detail)
        layout.addWidget(back_btn)

        # Title
        self.tx_detail_title = QLabel("Edit Transaction")
        self.tx_detail_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white; margin-bottom: 20px;")
        layout.addWidget(self.tx_detail_title)

        # Top Form (Date, Description)
        top_form = QFormLayout()
        
        self.tx_edit_account_combo = QComboBox()
        self.tx_edit_account_combo.setView(QListView())
        self.tx_edit_account_combo.setFixedWidth(self.s(300))
        self.tx_edit_account_combo.setStyleSheet(f"""
            QComboBox {{ padding: {self.s(8)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px; }}
            QComboBox QAbstractItemView {{ background-color: #2b2b2b; color: white; outline: none; border: 1px solid #444; font-size: {self.s(18)}px; }}
            QComboBox QAbstractItemView::item {{ padding: {self.s(10)}px; color: white; }}
            QComboBox QAbstractItemView::item:hover {{ background-color: #333; }}
            QComboBox QAbstractItemView::item:selected {{ background-color: #ff9800; color: black; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{ image: none; }}
        """)
        lbl_acc = QLabel("Account:")
        lbl_acc.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        top_form.addRow(lbl_acc, self.tx_edit_account_combo)
        
        self.tx_edit_date = ModernDateEdit(scale_factor=self.scale_factor)
        self.tx_edit_date.setFixedWidth(self.s(200))
        self.tx_edit_date.setDisplayFormat("MM/dd/yyyy")
        self.tx_edit_date.setStyleSheet(f"QDateEdit {{ padding: {self.s(5)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px; }}")
        lbl_date = QLabel("Date:")
        lbl_date.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        top_form.addRow(lbl_date, self.tx_edit_date)
        
        self.tx_edit_pay_desc = QLineEdit()
        self.tx_edit_pay_desc.setFixedWidth(self.s(300))
        self.tx_edit_pay_desc.setPlaceholderText("Group Description")
        self.tx_edit_pay_desc.setStyleSheet(f"padding: {self.s(5)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px;")
        lbl_desc = QLabel("Description:")
        lbl_desc.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        top_form.addRow(lbl_desc, self.tx_edit_pay_desc)

        layout.addLayout(top_form)

        # Item Table
        self.tx_item_table = TransactionItemTable(editable=False, currency_formatter=self._format_number_as_currency, scale_factor=self.scale_factor)
        self.tx_item_table.setMaximumWidth(650)
        split_layout = QHBoxLayout()
        split_layout.addWidget(self.tx_item_table, 1)
        split_layout.addStretch(1)
        layout.addLayout(split_layout)

        # Buttons Layout
        btns_layout = QHBoxLayout()

        # Save Button
        self.tx_save_btn = QPushButton("Save Changes")
        self.tx_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tx_save_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(12)}px {self.s(24)}px; background-color: #009688; color: white;
                border: none; border-radius: {self.s(4)}px; font-weight: bold; font-size: {self.s(16)}px;
            }}
            QPushButton:hover {{ background-color: #00796b; }}
        """)
        self.tx_save_btn.clicked.connect(self._save_transaction_details)
        btns_layout.addWidget(self.tx_save_btn)

        # Delete Button
        self.tx_delete_btn = QPushButton("Delete Transaction")
        self.tx_delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tx_delete_btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.s(12)}px {self.s(24)}px;
                background-color: transparent;
                color: #ff5252;
                border: {self.s(1)}px solid #ff5252;
                border-radius: {self.s(4)}px;
                font-weight: bold;
                font-size: {self.s(16)}px;
            }}
            QPushButton:hover {{
                background-color: #ff5252;
                color: white;
            }}
        """)
        self.tx_delete_btn.clicked.connect(self._delete_transaction_from_detail)
        btns_layout.addWidget(self.tx_delete_btn)
        
        btns_layout.addStretch()
        layout.addLayout(btns_layout)

    def _open_transaction_detail(self):
        """Opens the transaction detail page."""
        button = self.sender()
        if button:
            index = self.ledger_table.indexAt(button.parentWidget().pos())
            if index.isValid():
                row = index.row()
                date_item = self.ledger_table.item(row, 0)
                tx_id = date_item.data(Qt.UserRole)
                mode = button.property("action_type")
                self._open_transaction_detail_by_id(tx_id, mode)

    def _open_transaction_detail_by_id(self, tx_id, mode):
        """Opens the transaction detail page for a given transaction ID and mode."""
        self.current_edit_tx_id = tx_id
        self.return_to_widget = self.stacked_widget.currentWidget()
        is_editable = (mode == "edit")

        # Load Data
        self.cursor.execute("SELECT txid, type, account_id FROM transactions WHERE id = ?", (tx_id,))
        meta = self.cursor.fetchone()
        
        if meta:
            txid_str, type_, acc_id = meta
            
            # Populate and set account combo
            self.tx_edit_account_combo.clear()
            self.cursor.execute("SELECT id, name FROM accounts")
            all_accounts = self.cursor.fetchall()
            for account_id, account_name in all_accounts:
                self.tx_edit_account_combo.addItem(account_name, account_id)
            
            current_index = self.tx_edit_account_combo.findData(acc_id)
            if current_index != -1:
                self.tx_edit_account_combo.setCurrentIndex(current_index)
            
            self.tx_edit_account_combo.setEnabled(is_editable)

            # Handle Transfers with a Popup Dialog
            if type_ in ['Transfer In', 'Transfer Out']:
                self._edit_transfer_dialog(tx_id, mode=mode)
                return
            
            # Fetch all items for this group if it's a Payment/Receipt
            if type_ in ['Payment', 'Receipt']:
                self.cursor.execute("""
                    SELECT date, payment_description, description, quantity, amount 
                    FROM transactions 
                    WHERE txid = ? AND type = ? AND account_id = ?
                    ORDER BY id ASC
                """, (txid_str, type_, acc_id))
            else:
                self.cursor.execute("SELECT date, payment_description, description, quantity, amount FROM transactions WHERE id = ?", (tx_id,))
            
            rows = self.cursor.fetchall()
            if rows:
                # Set Header Info from first row
                self.tx_edit_date.setDate(QDate.fromString(rows[0][0], "yyyy-MM-dd"))
                self.tx_edit_pay_desc.setText(rows[0][1] if rows[0][1] else "")
                
                # Set UI State
                self.tx_edit_date.setReadOnly(not is_editable)
                self.tx_edit_pay_desc.setReadOnly(not is_editable)
                self.tx_save_btn.setVisible(is_editable)
                self.tx_delete_btn.setVisible(is_editable)
                action = "Edit" if is_editable else "View"
                self.tx_detail_title.setText(f"{action} {type_}")

                # Populate Table
                items = []
                has_custom_qty = False
                for _, _, desc, qty, amt_internal in rows:
                    amt = self._from_internal(amt_internal)
                    if qty != 1.0:
                        has_custom_qty = True
                    unit_price = round((amt / qty), 6) if qty else 0
                    items.append({'description': desc, 'quantity': qty, 'price': unit_price})
                
                self.tx_item_table.enable_qty_cb.setChecked(has_custom_qty)
                self.tx_item_table.set_rows(items, editable=is_editable)
            
            self.stacked_widget.setCurrentWidget(self.transaction_detail_page)

    def _return_from_transaction_detail(self):
        """Returns to the previously viewed page and reloads its data."""
        if hasattr(self, 'return_to_widget') and self.return_to_widget:
            # Reload data based on which page we are returning to
            if self.return_to_widget == self.account_view_page:
                if self.current_view_account_id:
                    self._load_account_ledger(self.current_view_account_id)
            elif self.return_to_widget == self.receipts_list_page:
                self._load_all_transactions("Receipt")
            elif self.return_to_widget == self.payments_list_page:
                self._load_all_transactions("Payment")
            elif self.return_to_widget == self.transfers_list_page:
                self._load_all_transactions("Transfer")
            
            self.stacked_widget.setCurrentWidget(self.return_to_widget)
            self.return_to_widget = None # Clear it
        else:
            # Fallback to main accounts page
            self.stacked_widget.setCurrentIndex(0)

    def _save_transaction_details(self):
        """Saves changes to the transaction."""
        if self.current_edit_tx_id is None:
            return
            
        new_date = self.tx_edit_date.date().toString("yyyy-MM-dd")
        new_pay_desc = self.tx_edit_pay_desc.text()
        new_total_amount_internal = self._to_internal(self.tx_item_table.get_total())
        new_acc_id = self.tx_edit_account_combo.currentData()
        
        # Get old values to update balance
        self.cursor.execute("SELECT amount, type, account_id, txid FROM transactions WHERE id = ?", (self.current_edit_tx_id,))
        row = self.cursor.fetchone()
        if not row:
            return
        _, type_, old_acc_id, txid = row
        
        # Calculate Old Total for the group (Already in Cents from DB)
        if type_ in ['Payment', 'Receipt']:
            self.cursor.execute("SELECT SUM(amount) FROM transactions WHERE txid = ? AND type = ? AND account_id = ?", (txid, type_, old_acc_id))
            old_total_internal = self.cursor.fetchone()[0]
        else:
            self.cursor.execute("SELECT amount FROM transactions WHERE id = ?", (self.current_edit_tx_id,))
            old_total_internal = self.cursor.fetchone()[0]
        
        old_total_internal = old_total_internal or 0

        # Update Balance
        if old_acc_id != new_acc_id:
            # Revert from old account
            if type_ in ["Payment", "Transfer Out"]:
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (old_total_internal, old_acc_id))
            elif type_ in ["Receipt", "Transfer In"]:
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (old_total_internal, old_acc_id))
            
            # Apply to new account
            if type_ in ["Payment", "Transfer Out"]:
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (new_total_amount_internal, new_acc_id))
            elif type_ in ["Receipt", "Transfer In"]:
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (new_total_amount_internal, new_acc_id))
        elif new_total_amount_internal != old_total_internal: # account is same, just update diff
            diff = new_total_amount_internal - old_total_internal
            if type_ in ["Payment", "Transfer Out"]:
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (diff, new_acc_id))
            elif type_ in ["Receipt", "Transfer In"]:
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (diff, new_acc_id))
        # Fetch old transaction IDs to keep sorting stable
        if type_ in ['Payment', 'Receipt']:
            self.cursor.execute("SELECT id FROM transactions WHERE txid = ? AND type = ? AND account_id = ? ORDER BY id ASC", (txid, type_, old_acc_id))
        else:
            self.cursor.execute("SELECT id FROM transactions WHERE id = ?", (self.current_edit_tx_id,))
        old_ids = [r[0] for r in self.cursor.fetchall()]

        # Delete old transactions for this group
        if type_ in ['Payment', 'Receipt']:
            self.cursor.execute("DELETE FROM transactions WHERE txid = ? AND type = ? AND account_id = ?", (txid, type_, old_acc_id))
        else:
            self.cursor.execute("DELETE FROM transactions WHERE id = ?", (self.current_edit_tx_id,))
            
        # Insert new transactions
        items = self.tx_item_table.get_items()
        for idx, item in enumerate(items):
            description = item['description']
            quantity = item['quantity']
            line_total_internal = self._to_internal(item['total'])
            
            if line_total_internal > 0 or (description and type_ in ['Payment', 'Receipt']):
                if idx < len(old_ids):
                    self.cursor.execute("""
                        INSERT INTO transactions (id, account_id, date, txid, payment_description, description, quantity, amount, type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (old_ids[idx], new_acc_id, new_date, txid, new_pay_desc, description, quantity, line_total_internal, type_))
                else:
                    self.cursor.execute("""
                        INSERT INTO transactions (account_id, date, txid, payment_description, description, quantity, amount, type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_acc_id, new_date, txid, new_pay_desc, description, quantity, line_total_internal, type_))
        
        self.conn.commit()
        self._load_accounts() # Update main table
        self._return_from_transaction_detail()

    def _delete_transaction_from_detail(self):
        """Deletes a transaction and updates the account balance."""
        reply = self._show_modern_message(
            "Confirm Delete", 
            "Are you sure you want to delete this transaction?", 
            QMessageBox.Icon.Question, 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.Yes:
            self.cursor.execute("SELECT account_id, txid, type FROM transactions WHERE id = ?", (self.current_edit_tx_id,))
            row = self.cursor.fetchone()
            if row:
                acc_id, txid, type_ = row
                
                # Handle Transfers (Linked Deletion)
                if type_ in ['Transfer In', 'Transfer Out'] and txid and txid != "TRF":
                    self.cursor.execute("SELECT id, account_id, amount, type FROM transactions WHERE txid = ?", (txid,))
                    rows = self.cursor.fetchall()
                    
                    for r_id, r_acc_id, r_amt, r_type in rows:
                        if r_type == "Transfer Out":
                            self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (r_amt, r_acc_id))
                        elif r_type == "Transfer In":
                            self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (r_amt, r_acc_id))
                    
                    self.cursor.execute("DELETE FROM transactions WHERE txid = ?", (txid,))

                elif type_ in ['Payment', 'Receipt']:
                    # Calculate total amount for the group to revert balance
                    self.cursor.execute("SELECT SUM(amount) FROM transactions WHERE txid = ? AND type = ? AND account_id = ?", (txid, type_, acc_id))
                    total_amount = self.cursor.fetchone()[0]
                    
                    # Revert Balance
                    if type_ == "Payment":
                        self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (total_amount, acc_id))
                    elif type_ == "Receipt":
                        self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (total_amount, acc_id))
                    
                    self.cursor.execute("DELETE FROM transactions WHERE txid = ? AND type = ? AND account_id = ?", (txid, type_, acc_id))

                else:
                    # Single Item or Legacy Transfer
                    self.cursor.execute("SELECT amount FROM transactions WHERE id = ?", (self.current_edit_tx_id,))
                    total_amount = self.cursor.fetchone()[0]
                    
                    if type_ in ["Payment", "Transfer Out"]:
                        self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (total_amount, acc_id))
                    elif type_ in ["Receipt", "Transfer In"]:
                        self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (total_amount, acc_id))
                        
                    self.cursor.execute("DELETE FROM transactions WHERE id = ?", (self.current_edit_tx_id,))
                
                self.conn.commit()
                
                self._load_accounts() # Update sidebar/main table
                self._return_from_transaction_detail()

    def _edit_transfer_dialog(self, tx_id, mode="edit"):
        """Opens a popup dialog to edit a transfer transaction."""
        self.cursor.execute("SELECT date, description, amount, account_id, type, txid FROM transactions WHERE id = ?", (tx_id,))
        row = self.cursor.fetchone()
        if not row:
            return
        date_str, desc, amount_internal, acc_id, type_, txid = row
        amount = self._from_internal(amount_internal)

        # Find both sides of the transfer to get account names and IDs
        from_id, to_id = None, None
        if txid and txid.startswith("TRF-"):
            self.cursor.execute("""
                SELECT a.id, a.name, t.type
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.txid = ? AND t.type IN ('Transfer In', 'Transfer Out')
            """, (txid,))
            transfer_parts = self.cursor.fetchall()
            for acc_id_part, name, tx_type in transfer_parts:
                if tx_type == 'Transfer Out':
                    from_id = acc_id_part
                elif tx_type == 'Transfer In':
                    to_id = acc_id_part
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Transfer" if mode == "edit" else "View Transfer")
        dialog.setFixedSize(self.s(450), self.s(450))
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: #2b2b2b; border: 1px solid #ff9800; border-radius: {self.s(15)}px; }}
            QWidget {{ background-color: #2b2b2b; color: white; }}
            QLabel {{ color: white; border: none; background-color: transparent; }}
            QLineEdit {{ padding: {self.s(5)}px; background-color: #333333; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(16)}px; }}
            QComboBox {{ padding: {self.s(5)}px; background-color: #333333; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(16)}px; }}
            QComboBox:hover {{ background-color: #444444; border-color: #888; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{ image: none; }}
            QComboBox QAbstractItemView {{ background-color: #333333; color: white; outline: none; border: 1px solid #ff9800; font-size: {self.s(16)}px; }}
            QComboBox QAbstractItemView::item {{ padding: {self.s(5)}px; color: white; }}
            QComboBox QAbstractItemView::item:hover {{ background-color: #555; }}
            QComboBox QAbstractItemView::item:selected {{ background-color: #555; color: white; border: 1px solid white; }}
            QAbstractSpinBox {{ padding: {self.s(5)}px; background-color: #333333; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(16)}px; }}
        """)
        
        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        combo_from = QComboBox()
        combo_from.setView(QListView())
        combo_to = QComboBox()
        combo_to.setView(QListView())

        unified_combo_style = f"""
            QComboBox {{ padding: {self.s(8)}px; background-color: #444; color: white; border: 1px solid #666; border-radius: {self.s(4)}px; font-size: {self.s(18)}px; }}
            QComboBox QAbstractItemView {{ background-color: #2b2b2b; color: white; outline: none; border: 1px solid #444; font-size: {self.s(18)}px; }}
            QComboBox QAbstractItemView::item {{ padding: {self.s(10)}px; color: white; }}
            QComboBox QAbstractItemView::item:hover {{ background-color: #333; }}
            QComboBox QAbstractItemView::item:selected {{ background-color: #ff9800; color: black; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{ image: none; }}
        """
        combo_from.setStyleSheet(unified_combo_style)
        combo_to.setStyleSheet(unified_combo_style)

        self.cursor.execute("SELECT id, name FROM accounts")
        all_accounts = self.cursor.fetchall()
        for account_id, account_name in all_accounts:
            combo_from.addItem(account_name, account_id)
            combo_to.addItem(account_name, account_id)

        if from_id:
            combo_from.setCurrentIndex(combo_from.findData(from_id))
        if to_id:
            combo_to.setCurrentIndex(combo_to.findData(to_id))

        combo_from.setEnabled(mode == "edit")
        combo_to.setEnabled(mode == "edit")

        lbl_from = QLabel("From:")
        lbl_from.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        form.addRow(lbl_from, combo_from)
        
        lbl_to = QLabel("To:")
        lbl_to.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        form.addRow(lbl_to, combo_to)

        # Date
        date_edit = ModernDateEdit(scale_factor=self.scale_factor)
        date_edit.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        date_edit.setDisplayFormat("MM/dd/yyyy")
        date_edit.setReadOnly(mode == "view")
        lbl_date = QLabel("Date:")
        lbl_date.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        form.addRow(lbl_date, date_edit)
        
        # Description
        desc_edit = QLineEdit()
        desc_edit.setText(desc)
        desc_edit.setPlaceholderText("Description")
        desc_edit.setStyleSheet("padding: 5px; background-color: #333333; color: white; border: 1px solid #666; border-radius: 4px;")
        desc_edit.setReadOnly(mode == "view")
        lbl_desc = QLabel("Description:")
        lbl_desc.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        form.addRow(lbl_desc, desc_edit)

        # Amount
        amount_spin = QuantitySpinBox()
        amount_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        amount_spin.setRange(0.00, 1000000000000000.00)
        amount_spin.setDecimals(self.currency_decimals) # Use app-wide decimal setting
        amount_spin.setValue(amount)
        amount_spin.setReadOnly(mode == "view")
        lbl_amt = QLabel("Amount:")
        lbl_amt.setStyleSheet(f"font-size: {self.s(18)}px; color: white;")
        form.addRow(lbl_amt, amount_spin)
        
        layout.addLayout(form)
        
        # Buttons
        if mode == "edit":
            btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            btn_box.button(QDialogButtonBox.StandardButton.Ok).setObjectName("ok_btn")
            btn_box.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("cancel_btn")
        else:
            btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            btn_box.button(QDialogButtonBox.StandardButton.Close).setObjectName("cancel_btn") # Close behaves like Cancel visually
            
        btn_box.setStyleSheet(f"""
            QPushButton#ok_btn {{ 
                background-color: #2d5a27; 
                color: white; 
                border: 1px solid #3d8c34; 
                padding: {self.s(8)}px {self.s(16)}px; 
                border-radius: {self.s(4)}px; 
                font-size: {self.s(16)}px; 
                font-weight: bold;
            }}
            QPushButton#ok_btn:hover {{ background-color: #3d8c34; }}
            
            QPushButton#cancel_btn {{ 
                background-color: #8a2b2b; 
                color: white; 
                border: 1px solid #b71c1c; 
                padding: {self.s(8)}px {self.s(16)}px; 
                border-radius: {self.s(4)}px; 
                font-size: {self.s(16)}px; 
                font-weight: bold;
            }}
            QPushButton#cancel_btn:hover {{ background-color: #b71c1c; }}
        """)
        for btn in btn_box.buttons():
            btn.setIcon(QIcon())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        if mode == "edit":
            # Delete Button (Optional, for convenience)
            del_btn = QPushButton("Delete Transfer")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet(f"color: #ff5252; background: transparent; border: none; font-weight: bold; margin-top: {self.s(10)}px; font-size: {self.s(14)}px;")
            # Note: Reusing _delete_transaction_from_detail requires setting current_edit_tx_id. 
            # A simpler approach for the dialog:
            def delete_transfer():
                self.current_edit_tx_id = tx_id
                self._delete_transaction_from_detail()
                dialog.reject()
            del_btn.clicked.connect(delete_transfer)
            layout.addWidget(del_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        if dialog.exec() == QDialog.Accepted and mode == "edit":
            new_date = date_edit.date().toString("yyyy-MM-dd")
            new_amount_internal = self._to_internal(amount_spin.value())
            new_desc = desc_edit.text().strip()
            new_from_id = combo_from.currentData()
            new_to_id = combo_to.currentData()

            if new_from_id == new_to_id:
                self._show_modern_message("Invalid Accounts", "From and To accounts cannot be the same.", QMessageBox.Icon.Warning)
                return
            
            # 1. Revert old transaction balances (amount_internal is from DB/cents)
            if from_id and to_id:
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount_internal, from_id))
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount_internal, to_id))

            # 2. Apply new transaction balances
            self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (new_amount_internal, new_from_id))
            self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (new_amount_internal, new_to_id))

            # 3. Update transaction records
            new_from_name = combo_from.currentText()
            new_to_name = combo_to.currentText()

            # Update 'Transfer Out' record
            self.cursor.execute("""
                UPDATE transactions
                SET account_id = ?, date = ?, amount = ?, payment_description = ?, description = ?
                WHERE txid = ? AND type = 'Transfer Out'
            """, (new_from_id, new_date, new_amount_internal, f"Transfer to {new_to_name}", new_desc, txid))

            # Update 'Transfer In' record
            self.cursor.execute("""
                UPDATE transactions
                SET account_id = ?, date = ?, amount = ?, payment_description = ?, description = ?
                WHERE txid = ? AND type = 'Transfer In'
            """, (new_to_id, new_date, new_amount_internal, f"Transfer from {new_from_name}", new_desc, txid))
            
            self.conn.commit()
            self._load_accounts()
            self._return_from_transaction_detail()




