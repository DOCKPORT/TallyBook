#!/usr/bin/env python3
"""A custom Sankey-style flow chart widget for TallyBook.

Renders a visual flow from total receipts to individual account
payment volumes, with interactive hover and selection support.
"""  # noqa: EXE001

from color_system import color_for_percentage
from currency import format_percentage
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget
from scaling import scaled


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
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if is_hovering else Qt.CursorShape.ArrowCursor
        )
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            clicked_account = None
            for rect, name, _ in self.account_zones:
                if rect.contains(pos):
                    clicked_account = name
                    break

            # Toggle selection if clicking the same one, otherwise select new,
            # or clear if clicking empty space
            if clicked_account:
                self.selected_account = (
                    None if self.selected_account == clicked_account else clicked_account
                )
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

        painter.drawText(
            self.source_label_rect, Qt.AlignmentFlag.AlignCenter, full_source_label
        )

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
                target_h = max(
                    2, (volume / total_payment_volume) * available_target_height
                )
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
                cp1_x,
                current_source_flow_y,
                cp1_x,
                current_target_y,
                target_x - arrow_w,
                current_target_y,
            )
            path.lineTo(target_x, current_target_y + target_h / 2)
            path.lineTo(target_x - arrow_w, current_target_y + target_h)
            path.cubicTo(
                cp1_x,
                current_target_y + target_h,
                cp1_x,
                current_source_flow_y + flow_h,
                source_x,
                current_source_flow_y + flow_h,
            )
            path.closeSubpath()

            # Determine color based on % (Centralized source of truth)
            pct = (
                (volume / self.total_receipts * 100) if self.total_receipts > 0 else 0.0
            )
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
                    alpha = 210  # Highlight selected
                else:
                    alpha = 30  # Dim others
            else:
                alpha = 90  # Default

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
                painter.setPen(QColor("#777777"))  # Muted grey for text
            font = QFont("Fira Code")
            font.setBold(True)
            font.setPointSize(self.s(10))
            painter.setFont(font)

            # pct already calculated above
            label_text = f"{name} {self._format_percentage(pct)}"
            label_vol = (
                f"{self.currency_symbol} {volume:,.{self.currency_decimals}f}"
            )

            # Measure label and elide if necessary to prevent going off-screen
            metrics = painter.fontMetrics()
            max_label_w = margin_right - 20  # Leave a small buffer at the very edge
            elided_label = metrics.elidedText(
                label_text, Qt.TextElideMode.ElideRight, max_label_w
            )

            # Draw name and %, centered vertically relative to the flow path
            label_y = int(current_target_y + target_h / 2 + 4)
            label_x = target_x + 10

            # Measure label for hit zone
            label_rect = QRect(
                label_x,
                label_y - metrics.height(),
                metrics.horizontalAdvance(elided_label),
                metrics.height() + 5,
            )
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

                bg_rect = QRectF(
                    mid_x - ov_w / 2 - 8,
                    mid_y - ov_h / 2 - 4,
                    ov_w + 16,
                    ov_h + 8,
                )
                painter.setBrush(QColor(0, 0, 0, 200))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bg_rect, 6, 6)

                painter.setPen(QColor("#ffffff"))
                painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, overlay_text)

            current_target_y += target_h + gap
            current_source_flow_y += flow_h