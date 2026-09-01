"""Analytics page module for TallyBook.

Provides the AnalyticsPage widget: a scrollable set of monthly receipts and
per-account payment bar charts with hover tooltips. It also refreshes the
Sankey flow chart that lives on the Accounts page.
"""
from currency import from_internal
from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QValueAxis,
)
from PySide6.QtCore import QDate, QPointF, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from scaling import scaled
from widgets import ModernTooltip


class AnalyticsPage(QWidget):
    """Scrollable analytics view with monthly receipts/payment charts."""

    def __init__(self, parent=None, scale_factor=1.0):
        super().__init__(parent)
        self.scale_factor = scale_factor
        self.s = lambda val: scaled(self.scale_factor, val)
        self.currency_symbol = "$"
        self.currency_decimals = 2
        self._is_built = False
        self.modern_tooltip = None
        self._prev_acc_ids = None

    def set_currency_settings(self, symbol, decimals):
        """Updates currency formatting used by hover tooltips and the Sankey title."""
        self.currency_symbol = symbol
        self.currency_decimals = decimals
        if getattr(self, 'axis_y', None):
            self.axis_y.setTitleVisible(False)

    def build(self):
        """Builds the analytics page UI. Call once before update_data."""
        self.modern_tooltip = ModernTooltip(self)

        main_layout = QVBoxLayout(self)
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
        self.receipts_series.hovered.connect(self.on_bar_hovered)
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

        self.account_payment_charts = {}  # acc_id -> (series, axis_x, axis_y)

    def update_data(self, cursor, sankey_chart, sankey_title):
        """Queries the DB and updates the analytics charts (12-month rolling window).

        cursor: the DB cursor. sankey_chart/sankey_title: the Sankey widgets that
        live on the Accounts page (owned by the main window).
        """
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
            if sankey_chart is not None:
                cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Receipt'")
                raw_total = cursor.fetchone()[0] or 0
                total_receipts_all_time = from_internal(raw_total)

                cursor.execute("SELECT id, name FROM accounts")
                accounts = cursor.fetchall()

                sankey_data = []
                for acc_id, acc_name in accounts:
                    cursor.execute("""
                        SELECT SUM(amount) FROM transactions
                        WHERE type = 'Payment' AND account_id = ?
                    """, (acc_id,))
                    raw_vol = cursor.fetchone()[0] or 0
                    vol = from_internal(raw_vol)
                    sankey_data.append((acc_name, vol))

                sankey_chart.setData(total_receipts_all_time, sankey_data, self.currency_symbol, self.currency_decimals)
                if sankey_title is not None:
                    total_str = f"— {self.currency_symbol} {total_receipts_all_time:,.{self.currency_decimals}f}"
                    sankey_title.setText(f"Payment Flow of Net Receipts {total_str}")

            return

        self.receipts_series.clear()
        cursor.execute("""
            SELECT strftime('%Y-%m', date) as month, SUM(amount)
            FROM transactions
            WHERE type = 'Receipt' AND date >= ?
            GROUP BY month
        """, (start_date_str,))

        db_results = {row[0]: from_internal(row[1]) for row in cursor.fetchall()}

        bar_set_receipts = QBarSet("Receipts")
        bar_set_receipts.setColor(QColor("#ff9800"))
        bar_set_receipts.setPen(QPen(Qt.PenStyle.NoPen))

        max_val_receipts = 0
        for key in month_keys:
            total_amount = db_results.get(key, 0.0)
            bar_set_receipts.append(total_amount)
            max_val_receipts = max(max_val_receipts, total_amount)

        self.receipts_series.append(bar_set_receipts)
        self.axis_x.clear()
        self.axis_x.append(categories)
        self.axis_y.setRange(0, max_val_receipts * 1.1 if max_val_receipts > 0 else 100)

        # 3. Update Account Payments
        cursor.execute("SELECT id, name FROM accounts")
        accounts = cursor.fetchall()
        self.payments_header.setVisible(len(accounts) > 0)
        new_acc_ids = sorted([acc[0] for acc in accounts])

        # Determine if we need to rebuild the grid (only if accounts changed)
        if self._prev_acc_ids is None or self._prev_acc_ids != new_acc_ids:
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
            cursor.execute("""
                SELECT strftime('%Y-%m', date) as month, SUM(amount)
                FROM transactions
                WHERE type = 'Payment' AND account_id = ? AND date >= ?
                GROUP BY month
            """, (acc_id, start_date_str))

            p_results = {row[0]: from_internal(row[1]) for row in cursor.fetchall()}

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
                max_val_p = max(max_val_p, total_amount)

            series.append(bar_set_p)
            ax.clear()
            ax.append(categories)
            ay.setRange(0, max_val_p * 1.1 if max_val_p > 0 else 100)

        # 4. Update Sankey Chart (Flow from Total Receipts to Account Payments - All Time)
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Receipt'")
        raw_tr = cursor.fetchone()[0] or 0
        total_receipts_all_time = from_internal(raw_tr)

        sankey_data = []
        for acc_id, acc_name in accounts:
            cursor.execute("""
                SELECT SUM(amount)
                FROM transactions
                WHERE type = 'Payment'
                AND account_id = ?
            """, (acc_id,))
            raw_v = cursor.fetchone()[0] or 0
            vol = from_internal(raw_v)
            sankey_data.append((acc_name, vol))

        if sankey_chart is not None:
            sankey_chart.setData(total_receipts_all_time, sankey_data, self.currency_symbol, self.currency_decimals)
            if sankey_title is not None:
                total_str = f"— {self.currency_symbol} {total_receipts_all_time:,.{self.currency_decimals}f}"
                sankey_title.setText(f"Payment Flow of Net Receipts {total_str}")

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
        series.hovered.connect(self.on_bar_hovered)
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

    def on_bar_hovered(self, status, index, barset):
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
