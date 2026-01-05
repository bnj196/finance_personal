from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *

class BudgetNode(QGraphicsEllipseItem):
    def __init__(self, member, x, y):
        # Khởi tạo ellipse với tâm tại (0,0) → dễ di chuyển
        super().__init__(-30, -30, 60, 60)
        self.member = member
        self.setPos(x, y)
        self.setBrush(QBrush(member.color))
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        
        # Bật hover và kéo
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)  # tránh highlight

        # Hiệu ứng glow (tạo 1 lần)
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)

        self.tooltip = None
        self.update_visuals()

    def update_visuals(self):
        """Cập nhật kích thước và glow dựa trên tổng tiền."""
        total = self.member.total_income + self.member.total_expense
        base_size = 40
        max_size = 150
        size = base_size + min(total / 200_000, max_size - base_size)
        self.setRect(-size / 2, -size / 2, size, size)

        intensity = min(total / 1_000_000, 1.0)
        blur_radius = 20 + int(intensity * 80)
        opacity = 0.3 + intensity * 0.6
        glow_color = QColor(self.member.color)
        glow_color.setAlphaF(opacity)

        self.shadow.setBlurRadius(blur_radius)
        self.shadow.setColor(glow_color)

    def show_tooltip(self, pos):
        if self.tooltip:
            return
        if not self.scene():
            return

        text = (f"<b>{self.member.name}</b><br>"
                f"<span style='color:#27ae60'>💰 Thu: {self.member.total_income:,.0f} đ</span><br>"
                f"<span style='color:#e74c3c'>💸 Chi: {self.member.total_expense:,.0f} đ</span><br>"
                f"<span style='color:#3498db'>📊 Dư: {self.member.total_income - self.member.total_expense:,.0f} đ</span>")

        self.tooltip = QGraphicsTextItem()
        self.tooltip.setHtml(
            f"<div style='"
            f"background:rgba(30,30,40,220); "
            f"color:white; padding:8px; border-radius:6px; "
            f"font-family:Segoe UI; font-size:12px;'>"
            f"{text}</div>")
        self.tooltip.setPos(pos.x() + 15, pos.y() + 15)
        self.tooltip.setZValue(999)
        
        # 🔑 DÒNG QUAN TRỌNG: tooltip KHÔNG nhận sự kiện chuột
        self.tooltip.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        
        self.scene().addItem(self.tooltip)

    def hide_tooltip(self):
        if self.tooltip:
            if self.scene() and self.tooltip.scene():
                self.scene().removeItem(self.tooltip)
            self.tooltip = None

    # =============== HOVER EVENTS ===============
    def hoverEnterEvent(self, event):
        self.show_tooltip(event.scenePos())
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        if self.tooltip:
            self.tooltip.setPos(event.scenePos().x() + 15, event.scenePos().y() + 15)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.hide_tooltip()
        super().hoverLeaveEvent(event)

    # =============== MOUSE EVENTS (KÉO + ẨN TOOLTIP) ===============
    def mousePressEvent(self, event):
        # Ẩn tooltip ngay khi nhấn → tránh dính khi kéo
        self.hide_tooltip()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Không cần hiện lại tooltip — hoverEnter sẽ tự gọi nếu chuột còn trên node
        super().mouseReleaseEvent(event)