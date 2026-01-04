import sys
import json
import csv
import datetime
import random
import math
from pathlib import Path

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import *

# ======================
# 1. CẤU HÌNH & THEME
# ======================
BASE_DIR = Path(__file__).parent
# Đường dẫn đến các file data của 4 module trước
FILE_TRANS = BASE_DIR / "transactions.csv"
FILE_DEBTS = BASE_DIR / "debts.json"  # Hoặc multi_fund.json tùy file bạn export
FILE_GOALS = BASE_DIR / "budget.json" # File của Budget Multi-Goal
FILE_TODOS = BASE_DIR / "todos.json"
FILE_NOTES = BASE_DIR / "notes.json"

THEMES = {
    "spring": {"name": "Xuân", "bg": "#FFF8E1", "sec": "#b30000", "acc": "#FFD700", "txt": "#5D4037", "btn": "#d91e18"},
    "summer": {"name": "Hạ", "bg": "#E1F5FE", "sec": "#0277BD", "acc": "#4FC3F7", "txt": "#01579B", "btn": "#0288d1"},
    "autumn": {"name": "Thu", "bg": "#FFF3E0", "sec": "#E65100", "acc": "#FFB74D", "txt": "#3E2723", "btn": "#f57c00"},
    "winter": {"name": "Đông", "bg": "#ECEFF1", "sec": "#263238", "acc": "#90A4AE", "txt": "#37474F", "btn": "#455A64"}
}


class DataService:
    """Class này chịu trách nhiệm đọc data từ các file rời rạc"""
    @staticmethod
    def get_transaction_summary():
        income, expense = 0, 0
        recent = []
        if FILE_TRANS.exists():
            try:
                with open(FILE_TRANS, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
                    for row in data:
                        amt = float(row.get('amount', 0))
                        if row['type'] == 'income': income += amt
                        else: expense += amt
                    # Lấy 5 giao dịch gần nhất
                    recent = data[-5:][::-1] 
            except: pass
        return income, expense, income - expense, recent

    @staticmethod
    def get_debt_summary():
        owe, receive = 0, 0
        if FILE_DEBTS.exists():
            try:
                data = json.loads(FILE_DEBTS.read_text(encoding='utf-8'))
                # Xử lý tùy theo cấu trúc file debts.json của bạn (List object hoặc Dict)
                # Giả sử cấu trúc List từ bài Debt Manager
                debts = data if isinstance(data, list) else data.get('debts', [])
                for d in debts:
                    amt = d.get('amount', 0) - d.get('paid_back', 0)
                    if d.get('side') == 'IOWE': owe += amt
                    else: receive += amt
            except: pass
        return owe, receive, receive - owe

    @staticmethod
    def get_goal_summary():
        total_target, total_saved = 0, 0
        goals = []
        if FILE_GOALS.exists():
            try:
                data = json.loads(FILE_GOALS.read_text(encoding='utf-8'))
                goals = data.get('goals', [])
                for g in goals:
                    target = g.get('target', 0)
                    saved = sum(m.get('contribution', 0) for m in g.get('members', []))
                    total_target += target
                    total_saved += saved
            except: pass
        return total_target, total_saved, goals

    @staticmethod
    def get_today_tasks():
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        tasks = []
        if FILE_TODOS.exists():
            try:
                data = json.loads(FILE_TODOS.read_text(encoding='utf-8'))
                tasks = data.get(today_str, [])
            except: pass
        return tasks

# ======================
# 3. VISUAL EFFECTS
# ======================
class Particle:
    def __init__(self, w, h, mode="spring"):
        self.mode = mode; self.reset(w, h, True)
    def reset(self, w, h, first=False):
        self.x = random.uniform(0, w); self.size = random.uniform(5, 15)
        self.rotation = random.uniform(0, 360); self.speed_rot = random.uniform(-2, 2)
        if self.mode == "spring":
            self.y = random.uniform(-h, 0) if not first else random.uniform(0, h)
            self.speed_y = random.uniform(1, 3); self.drift = random.uniform(-0.5, 0.5)
            self.color = QColor("#FFD700") if random.choice([True, False]) else QColor("#FFB7C5"); self.shape = "flower"
        elif self.mode == "winter":
            self.y = random.uniform(-h, 0) if not first else random.uniform(0, h)
            self.speed_y = random.uniform(2, 5); self.drift = 0; self.color = QColor("#FFFFFF"); self.shape = "snow"
        else: self.y = random.uniform(-h, 0); self.speed_y = 2; self.drift = 0; self.color = QColor("gray"); self.shape = "circle"
        self.path = QPainterPath()
        if self.shape == "flower": self.create_flower_path()
    def create_flower_path(self):
        c = QPointF(0, 0); r = self.size / 2
        for i in range(5):
            a = math.radians(i * 72); t = QPointF(c.x() + r * math.cos(a), c.y() + r * math.sin(a))
            c1 = QPointF(c.x() + r*0.6 * math.cos(a-0.3), c.y() + r*0.6 * math.sin(a-0.3))
            c2 = QPointF(c.x() + r*0.6 * math.cos(a+0.3), c.y() + r*0.6 * math.sin(a+0.3))
            if i == 0: self.path.moveTo(c); 
            self.path.cubicTo(c1, t, c2)
        self.path.closeSubpath()
    def update(self, w, h):
        self.y += self.speed_y; self.x += self.drift + math.sin(self.y / 50) * 0.5
        self.rotation += self.speed_rot
        if self.y > h + 20: self.reset(w, h)

class SeasonalOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint); self.particles = []; self.current_season = "spring"
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_animation); self.initialized = False
    def set_season(self, s): self.current_season = s; self.init_particles()
    def init_particles(self):
        if self.width() > 0:
            self.particles = [Particle(self.width(), self.height(), self.current_season) for _ in range(50)]
            if not self.timer.isActive(): self.timer.start(20)
            self.initialized = True
    def update_animation(self):
        w, h = self.width(), self.height(); [p.update(w, h) for p in self.particles]; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for pt in self.particles:
            p.save(); p.translate(pt.x, pt.y); p.rotate(pt.rotation); p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(pt.color))
            if pt.shape == "flower": p.drawPath(pt.path)
            else: p.drawEllipse(QPointF(0,0), pt.size/2, pt.size/2)
            p.restore()

# ======================
# 4. CUSTOM WIDGETS
# ======================
class DashboardCard(QFrame):
    def __init__(self, title, value, icon, color, sub_text=""):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.9);
                border-left: 5px solid {color};
                border-radius: 10px;
            }}
            QLabel#Value {{ font-size: 20px; font-weight: bold; color: #2c3e50; }}
            QLabel#Title {{ color: gray; font-size: 12px; }}
            QLabel#Icon {{ font-size: 30px; }}
        """)
        
        layout = QHBoxLayout(self)
        
        # Text Info
        vbox = QVBoxLayout()
        lbl_title = QLabel(title); lbl_title.setObjectName("Title")
        lbl_val = QLabel(value); lbl_val.setObjectName("Value")
        lbl_sub = QLabel(sub_text); lbl_sub.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        vbox.addWidget(lbl_sub)
        
        # Icon
        lbl_icon = QLabel(icon); lbl_icon.setObjectName("Icon")
        
        layout.addLayout(vbox)
        layout.addStretch()
        layout.addWidget(lbl_icon)

class NavButton(QPushButton):
    def __init__(self, text, icon):
        super().__init__(f"  {icon}   {text}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 20px; border: none; color: white; font-size: 14px; }
            QPushButton:hover { background-color: rgba(255,255,255,0.1); }
            QPushButton:checked { background-color: rgba(255,255,255,0.2); font-weight: bold; border-left: 4px solid white; }
        """)


class MainDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Finance Master - Tổng Hợp")
        self.resize(1000, 650)
        self.current_theme = "spring"
        
        self.init_ui()
        self.overlay = SeasonalOverlay(self.centralWidget())
        self.overlay.show(); self.overlay.raise_()
        self.apply_theme("spring")
        
        # Refresh Data Timer (Real-time feel)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000) # Reload every 5s

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0); main_layout.setSpacing(0)
        
        # === SIDEBAR ===
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(250)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(0, 20, 0, 20)
        
        # Profile
        lbl_avatar = QLabel("🐉"); lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_avatar.setStyleSheet("font-size: 50px; background: rgba(255,255,255,0.2); border-radius: 40px; min-height: 80px;")
        lbl_name = QLabel("Võ Tiến Thiện"); lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setStyleSheet("color: white; font-weight: bold; font-size: 16px; margin-top: 10px;")
        
        sb_layout.addWidget(lbl_avatar)
        sb_layout.addWidget(lbl_name)
        sb_layout.addSpacing(30)
        
        # Nav Buttons
        self.btn_dash = NavButton("Dashboard", "🏠"); self.btn_dash.setChecked(True)
        self.btn_trans = NavButton("Thu Chi", "💸")
        self.btn_debt = NavButton("Sổ Nợ", "📝")
        self.btn_goal = NavButton("Quỹ Chung", "💰")
        self.btn_cal = NavButton("Lịch Trình", "📅")
        
        sb_layout.addWidget(self.btn_dash)
        sb_layout.addWidget(self.btn_trans)
        sb_layout.addWidget(self.btn_debt)
        sb_layout.addWidget(self.btn_goal)
        sb_layout.addWidget(self.btn_cal)
        sb_layout.addStretch()
        
        # Theme Selector
        self.combo_theme = QComboBox(); self.combo_theme.addItems(["spring", "summer", "autumn", "winter"])
        self.combo_theme.currentTextChanged.connect(self.apply_theme)
        sb_layout.addWidget(QLabel("  Giao diện:", styleSheet="color: white;"))
        sb_layout.addWidget(self.combo_theme)
        
        # main_layout.addWidget(self.sidebar)
        
        # === CONTENT AREA ===
        content_area = QWidget()
        self.content_layout = QVBoxLayout(content_area)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        self.lbl_title = QLabel("TỔNG QUAN TÀI CHÍNH"); self.lbl_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.lbl_date = QLabel(datetime.date.today().strftime("Hôm nay: %d/%m/%Y")); self.lbl_date.setStyleSheet("color: gray;")
        header.addWidget(self.lbl_title); header.addStretch(); header.addWidget(self.lbl_date)
        self.content_layout.addLayout(header)
        
        # 1. Cards Row
        self.cards_layout = QHBoxLayout()
        self.content_layout.addLayout(self.cards_layout)
        
        # 2. Charts Row
        charts_layout = QHBoxLayout()
        
        # Pie Chart (Cơ cấu tài sản)
        self.pie_view = QChartView(); self.pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.pie_view.setMinimumHeight(300)
        
        # Bar Chart (Thu vs Chi)
        self.bar_view = QChartView(); self.bar_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.bar_view.setMinimumHeight(300)
        
        charts_layout.addWidget(self.pie_view, 1)
        charts_layout.addWidget(self.bar_view, 2)
        self.content_layout.addLayout(charts_layout)
        
        # 3. Bottom Row (Table + Todos)
        bottom_layout = QHBoxLayout()
        
        # Recent Trans Table
        grp_trans = QGroupBox("Giao dịch gần đây")
        grp_trans.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid gray; border-radius: 5px; margin-top: 10px; }")
        v_trans = QVBoxLayout(grp_trans)
        self.table_recent = QTableWidget()
        self.table_recent.setColumnCount(3); self.table_recent.setHorizontalHeaderLabels(["Ngày", "Nội dung", "Số tiền"])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_recent.verticalHeader().setVisible(False)
        self.table_recent.setStyleSheet("background: rgba(255,255,255,0.8); border: none;")
        v_trans.addWidget(self.table_recent)
        bottom_layout.addWidget(grp_trans, 2)
        
        # Today Tasks
        grp_task = QGroupBox("Việc hôm nay")
        grp_task.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid gray; border-radius: 5px; margin-top: 10px; }")
        v_task = QVBoxLayout(grp_task)
        self.list_tasks = QListWidget()
        self.list_tasks.setStyleSheet("background: rgba(255,255,255,0.8); border: none;")
        v_task.addWidget(self.list_tasks)
        bottom_layout.addWidget(grp_task, 1)
        
        self.content_layout.addLayout(bottom_layout)
        
        main_layout.addWidget(content_area)
        self.refresh_data()

    def apply_theme(self, key):
        t = THEMES[key]
        self.current_theme = key
        self.overlay.set_season(key)
        self.sidebar.setStyleSheet(f"background-color: {t['sec']}; border-right: 1px solid {t['acc']};")
        self.centralWidget().setStyleSheet(f"background-color: {t['bg']};")
        
        # Update Chart Theme
        # Note: QtCharts themes are limited, we set transparent bg
        self.pie_view.setStyleSheet("background: transparent;")
        self.bar_view.setStyleSheet("background: transparent;")
        
        self.refresh_data() # Redraw UI elements with new colors

    def refresh_data(self):
        t = THEMES[self.current_theme]
        
        # 1. Get Data
        inc, exp, bal, recent = DataService.get_transaction_summary()
        owe, recv, net_debt = DataService.get_debt_summary()
        g_tgt, g_saved, goals = DataService.get_goal_summary()
        tasks = DataService.get_today_tasks()
        
        # 2. Update Cards
        # Clear old cards
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        c1 = DashboardCard("SỐ DƯ HIỆN TẠI", f"{inc-exp:,.0f} đ", "💵", "#2ecc71", f"Thu: {inc:,.0f} | Chi: {exp:,.0f}")
        c2 = DashboardCard("TÀI SẢN RÒNG", f"{bal + net_debt + g_saved:,.0f} đ", "💎", "#3498db", "Bao gồm cả nợ & quỹ")
        c3 = DashboardCard("NỢ PHẢI THU", f"{recv:,.0f} đ", "📝", "#f1c40f", f"Nợ phải trả: {owe:,.0f}")
        c4 = DashboardCard("TIẾT KIỆM", f"{g_saved:,.0f} đ", "🐷", "#e74c3c", f"Mục tiêu: {g_tgt:,.0f}")
        
        self.cards_layout.addWidget(c1)
        self.cards_layout.addWidget(c2)
        self.cards_layout.addWidget(c3)
        self.cards_layout.addWidget(c4)
        
        # 3. Update Charts
        # --- Pie Chart ---
        pie_series = QPieSeries()
        pie_series.append("Tiền mặt", max(0, bal))
        pie_series.append("Cho vay", max(0, recv))
        pie_series.append("Quỹ tiết kiệm", max(0, g_saved))
        
        chart_pie = QChart()
        chart_pie.addSeries(pie_series)
        chart_pie.setTitle("Cơ Cấu Tài Sản")
        chart_pie.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart_pie.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        chart_pie.setBackgroundBrush(QBrush(QColor(255,255,255,100))) # Semi-transparent
        self.pie_view.setChart(chart_pie)
        
        # --- Bar Chart ---
        set0 = QBarSet("Thu nhập"); set0.append([inc])
        set0.setColor(QColor("#2ecc71"))
        set1 = QBarSet("Chi tiêu"); set1.append([exp])
        set1.setColor(QColor("#e74c3c"))
        
        bar_series = QBarSeries()
        bar_series.append(set0)
        bar_series.append(set1)
        
        chart_bar = QChart()
        chart_bar.addSeries(bar_series)
        chart_bar.setTitle("Tổng quan Thu/Chi")
        chart_bar.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart_bar.setBackgroundBrush(QBrush(QColor(255,255,255,100)))
        self.bar_view.setChart(chart_bar)
        
        # 4. Update Recent Table
        self.table_recent.setRowCount(0)
        for r in recent:
            row = self.table_recent.rowCount()
            self.table_recent.insertRow(row)
            self.table_recent.setItem(row, 0, QTableWidgetItem(r['date']))
            self.table_recent.setItem(row, 1, QTableWidgetItem(r['description'] or r['category']))
            
            amt_item = QTableWidgetItem(f"{float(r['amount']):,.0f}")
            if r['type'] == 'expense': amt_item.setForeground(QColor("red"))
            else: amt_item.setForeground(QColor("green"))
            self.table_recent.setItem(row, 2, amt_item)
            
        # 5. Update Tasks
        self.list_tasks.clear()
        if not tasks:
            self.list_tasks.addItem("Không có việc cần làm hôm nay.")
        else:
            for t in tasks:
                icon = "✅" if t.get('done') else "🔲"
                name = t.get('name', t.get('text', 'Unknown')) # Fallback for old data
                price = t.get('price', 0)
                item = QListWidgetItem(f"{icon} {name} ({price:,.0f} đ)")
                self.list_tasks.addItem(item)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay'):
            self.overlay.setGeometry(self.centralWidget().rect())
            if not self.overlay.initialized:
                self.overlay.init_particles()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainDashboard()
    window.show()
    sys.exit(app.exec())