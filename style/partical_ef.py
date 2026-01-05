
import random
import math

from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *

class Particle:
    def __init__(self, w, h, mode="spring"):
        self.mode = mode
        self.reset(w, h, first_time=True)

    def reset(self, w, h, first_time=False):
        self.x = random.uniform(0, w)
        self.size = random.uniform(5, 15)
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-2, 2)
        
        if self.mode == "spring": 
            self.y = random.uniform(-h, 0) if not first_time else random.uniform(0, h)
            self.speed_y = random.uniform(1, 3)
            self.drift = random.uniform(-0.5, 0.5)
            self.color = QColor("#FFD700") if random.choice([True, False]) else QColor("#FFB7C5")
            self.shape = "flower"
        elif self.mode == "winter":
            self.y = random.uniform(-h, 0) if not first_time else random.uniform(0, h)
            self.speed_y = random.uniform(2, 5)
            self.drift = 0
            self.color = QColor("#FFFFFF")
            self.shape = "snow"
        else: # Default fallback
            self.y = random.uniform(-h, 0)
            self.speed_y = 2
            self.drift = 0
            self.color = QColor("gray")
            self.shape = "circle"

        self.path = QPainterPath()
        if self.shape == "flower": self.create_flower_path()

    def create_flower_path(self):
        center = QPointF(0, 0)
        petal_radius = self.size / 2
        for i in range(5):
            angle = math.radians(i * 72)
            tip = QPointF(center.x() + petal_radius * math.cos(angle), center.y() + petal_radius * math.sin(angle))
            ctrl1 = QPointF(center.x() + petal_radius*0.6 * math.cos(angle-0.3), center.y() + petal_radius*0.6 * math.sin(angle-0.3))
            ctrl2 = QPointF(center.x() + petal_radius*0.6 * math.cos(angle+0.3), center.y() + petal_radius*0.6 * math.sin(angle+0.3))
            if i == 0: self.path.moveTo(center)
            self.path.cubicTo(ctrl1, tip, ctrl2)
        self.path.closeSubpath()

    def update(self, w, h):
        self.y += self.speed_y
        self.x += self.drift + math.sin(self.y / 50) * 0.5
        self.rotation += self.rotation_speed
        if self.y > h + 20: self.reset(w, h)


class SeasonalOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.particles = []
        self.current_season = "spring"
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        
        # --- FIX: Thêm dòng này để định nghĩa biến ---
        self.initialized = False 

    def set_season(self, season):
        self.current_season = season
        self.particles = []
        # Reset lại để tạo hạt mới đúng theo mùa
        self.init_particles()

    def init_particles(self):
        if self.width() > 0:
            count = 50
            self.particles = [Particle(self.width(), self.height(), self.current_season) for _ in range(count)]
            if not self.timer.isActive(): self.timer.start(20)
            
            # --- FIX: Đánh dấu là đã khởi tạo ---
            self.initialized = True 

    def update_animation(self):
        w, h = self.width(), self.height()
        for p in self.particles: p.update(w, h)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for p in self.particles:
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rotation)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(p.color))
            if p.shape == "flower": painter.drawPath(p.path)
            else: painter.drawEllipse(QPointF(0,0), p.size/2, p.size/2)
            painter.restore()