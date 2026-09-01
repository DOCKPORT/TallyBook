#!/usr/bin/env python3
# noqa: EXE001
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from scaling import scaled


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

