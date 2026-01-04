from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *



class BudgetNode(QGraphicsEllipseItem):
    def __init__(self, member, x, y, size=50, border_color=Qt.GlobalColor.black):
        super().__init__(x, y, size, size)
        self.member = member
        self.setBrush(QBrush(member.color))
        # Custom Border style
        pen = QPen(border_color, 3) 
        self.setPen(pen)
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{member.name}\nThu: {member.total_income:,.0f}\nChi: {member.total_expense:,.0f}")
        
        # Glow Effect
        if member.total_income > 0:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)
            shadow.setColor(member.color)
            shadow.setOffset(0, 0)
            self.setGraphicsEffect(shadow)

    def update_size(self):
        base = 50
        factor = min(self.member.total_expense / 500000, 5)
        size = int(base + factor * 20)
        self.setRect(self.rect().x(), self.rect().y(), size, size)




