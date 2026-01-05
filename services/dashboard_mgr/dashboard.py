import sys
import json
import os
import random
import math
from datetime import datetime, date

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import *

# --- IMPORT CORE CỦA BẠN ---
# Đảm bảo bạn đã có file core/data_manager.py
from core.data_manager import DataManager 

# ======================
# 1. CẤU HÌNH & PATH
# ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_TODOS = os.path.join(BASE_DIR, "data", "todos.json") # File lưu việc cần làm

THEMES_DASH = {
    "spring": {"name": "Xuân", "bg": "#FFF8E1", "sec": "#b30000", "acc": "#FFD700", "txt": "#5D4037"},
    "summer": {"name": "Hạ", "bg": "#E1F5FE", "sec": "#0277BD", "acc": "#4FC3F7", "txt": "#01579B"},
    "autumn": {"name": "Thu", "bg": "#FFF3E0", "sec": "#E65100", "acc": "#FFB74D", "txt": "#3E2723"},
    "winter": {"name": "Đông", "bg": "#ECEFF1", "sec": "#263238", "acc": "#90A4AE", "txt": "#37474F"}
}

# Helper: Load JSON
def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def format_money(val):
    return f"{int(val):,}"

# ======================
# 2. VISUAL EFFECTS (Particle & Overlay)
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
        else:
            self.y = random.uniform(-h, 0); self.speed_y = 2; self.drift = 0; self.color = QColor("white"); self.shape = "circle"
        self.path = QPainterPath()
        if self.shape == "flower": self.create_flower_path()
    def create_flower_path(self):
        c = QPointF(0, 0); r = self.size / 2
        for i in range(5):
            a = math.radians(i * 72); t = QPointF(c.x() + r * math.cos(a), c.y() + r * math.sin(a))
            c1 = QPointF(c.x() + r*0.6 * math.cos(a-0.3), c.y() + r*0.6 * math.sin(a-0.3))
            c2 = QPointF(c.x() + r*0.6 * math.cos(a+0.3), c.y() + r*0.6 * math.sin(a+0.3))
            if i == 0: self.path.moveTo(c) 
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
# 3. CUSTOM WIDGETS
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
        vbox = QVBoxLayout()
        lbl_title = QLabel(title); lbl_title.setObjectName("Title")
        lbl_val = QLabel(value); lbl_val.setObjectName("Value")
        lbl_sub = QLabel(sub_text); lbl_sub.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        vbox.addWidget(lbl_title); vbox.addWidget(lbl_val); vbox.addWidget(lbl_sub)
        lbl_icon = QLabel(icon); lbl_icon.setObjectName("Icon")
        layout.addLayout(vbox); layout.addStretch(); layout.addWidget(lbl_icon)

# ======================
# 4. MAIN DASHBOARD CLASS
# ======================
class MainDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Finance Master - Tổng Hợp")
        self.resize(1100, 700)
        
        # --- KẾT NỐI DATA MANAGER (Của bạn) ---
        self.data_mgr = DataManager.instance()
        self.data_mgr.data_changed.connect(self.refresh_data)

        self.current_theme = "spring"
        self.init_ui()
        
        # Hiệu ứng nền
        self.overlay = SeasonalOverlay(self.centralWidget())
        self.overlay.show(); self.overlay.raise_()
        self.apply_theme("spring")
        
        self.refresh_data()

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20,20,20,20); main_layout.setSpacing(15)

        # --- HEADER ---
        header = QHBoxLayout()
        self.lbl_title = QLabel("TỔNG QUAN TÀI CHÍNH"); self.lbl_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.lbl_date = QLabel(date.today().strftime("Hôm nay: %d/%m/%Y")); self.lbl_date.setStyleSheet("color: #555; font-size: 14px;")
        
        # Combo chọn theme
        self.combo_theme = QComboBox(); self.combo_theme.addItems(list(THEMES_DASH.keys()))
        self.combo_theme.currentTextChanged.connect(self.apply_theme)
        
        header.addWidget(self.lbl_title); header.addStretch(); header.addWidget(QLabel("Theme:")); header.addWidget(self.combo_theme); header.addSpacing(10); header.addWidget(self.lbl_date)
        main_layout.addLayout(header)

        # --- 1. CARDS ROW ---
        self.cards_layout = QHBoxLayout()
        main_layout.addLayout(self.cards_layout)

        # --- 2. CHARTS ROW ---
        charts_layout = QHBoxLayout()
        self.pie_view = QChartView(); self.pie_view.setRenderHint(QPainter.RenderHint.Antialiasing); self.pie_view.setMinimumHeight(300)
        self.bar_view = QChartView(); self.bar_view.setRenderHint(QPainter.RenderHint.Antialiasing); self.bar_view.setMinimumHeight(300)
        charts_layout.addWidget(self.pie_view, 1); charts_layout.addWidget(self.bar_view, 2)
        main_layout.addLayout(charts_layout)

        # --- 3. BOTTOM ROW (Table + ToDo) ---
        bottom_layout = QHBoxLayout()
        
        # Left: Recent Transactions (Sử dụng dữ liệu từ App của bạn)
        grp_trans = QGroupBox("Giao dịch gần đây")
        grp_trans.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #ccc; border-radius: 8px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        v_trans = QVBoxLayout(grp_trans)
        self.table_recent = QTableWidget(); self.table_recent.setColumnCount(3)
        self.table_recent.setHorizontalHeaderLabels(["Ngày", "Nội dung", "Số tiền"])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_recent.verticalHeader().setVisible(False)
        self.table_recent.setAlternatingRowColors(True)
        self.table_recent.setStyleSheet("border: none; background: rgba(255,255,255,0.6);")
        v_trans.addWidget(self.table_recent)
        
        # Right: Todo List (Đọc từ file JSON)
        grp_todo = QGroupBox("Cần làm / Mua sắm")
        grp_todo.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #ccc; border-radius: 8px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        v_todo = QVBoxLayout(grp_todo)
        self.list_todo = QListWidget()
        self.list_todo.setStyleSheet("border: none; font-size: 13px; background: rgba(255,255,255,0.6);")
        v_todo.addWidget(self.list_todo)
        
        bottom_layout.addWidget(grp_trans, 2) # Table chiếm 2 phần
        bottom_layout.addWidget(grp_todo, 1)  # Todo chiếm 1 phần
        
        main_layout.addLayout(bottom_layout)

    def apply_theme(self, key):
        t = THEMES_DASH[key]
        self.current_theme = key
        self.overlay.set_season(key)
        self.centralWidget().setStyleSheet(f"background-color: {t['bg']};")
        self.pie_view.setStyleSheet("background: transparent;")
        self.bar_view.setStyleSheet("background: transparent;")
        self.refresh_data()

    def refresh_data(self):
        """Cập nhật toàn bộ dữ liệu Dashboard từ DataManager (Singleton)"""
        
        # --- LẤY DỮ LIỆU TỪ DATA MANAGER ---
        data = self.data_mgr.get_dashboard_summary()
        
        # Trích xuất các chỉ số tài chính
        inc = data.get("income", 0)
        exp = data.get("expense", 0)
        bal = data.get("balance", 0)
        owe = data.get("debt_owe", 0)
        recv = data.get("debt_recv", 0)
        saved = data.get("savings", 0)
        net_worth = data.get("net_worth", 0)
        recent = data.get("recent_transactions", [])
        todos_list = data.get("calendar_todos", [])   # ← ĐÃ ĐỔI TÊN
        notes_list = data.get("calendar_notes", [])   # ← MỚI THÊM

        # --- CẬP NHẬT TODO & NOTES (PHÂN TÁCH RÕ RÀNG) ---
        self.list_todo.clear()
        has_todos = len(todos_list) > 0
        has_notes = len(notes_list) > 0

        # --- PHẦN 1: CẦN LÀM / MUA SẮM ---
        if has_todos:
            title_item = QListWidgetItem("📋 CẦN LÀM / MUA SẮM")
            title_item.setForeground(QColor("#2c3e50"))
            title_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.list_todo.addItem(title_item)
            
            for item in todos_list:
                status = "✅" if item.get('done', False) else "🛒"
                name = item.get('name', 'Không tên')
                price = item.get('price', 0)
                price_str = f" - {price:,.0f}đ" if price > 0 else ""
                widget_item = QListWidgetItem(f"{status} {name}{price_str}")
                
                if item.get('done', False):
                    widget_item.setForeground(QColor("gray"))
                    f = widget_item.font()
                    f.setStrikeOut(True)
                    widget_item.setFont(f)
                self.list_todo.addItem(widget_item)

        # --- PHẦN 2: GHI CHÚ ---
        if has_notes:
            if has_todos:
                self.list_todo.addItem(QListWidgetItem(""))  # Dòng trống phân cách
            
            title_item = QListWidgetItem("📝 GHI CHÚ")
            title_item.setForeground(QColor("#2c3e50"))
            title_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.list_todo.addItem(title_item)
            
            for note in notes_list:
                if isinstance(note, dict):
                    content = str(note.get("content", "")).strip()
                elif isinstance(note, str):
                    content = note.strip()
                else:
                    content = ""
                if content:
                    widget_item = QListWidgetItem(f"• {content}")
                    widget_item.setForeground(QColor("#555"))
                    widget_item.setFont(QFont("Segoe UI", 10, italic=True))
                    self.list_todo.addItem(widget_item)

        # --- TRƯỜNG HỢP KHÔNG CÓ GÌ ---
        if not has_todos and not has_notes:
            self.list_todo.addItem(QListWidgetItem("Không có việc hay ghi chú hôm nay!"))

        # --- CẬP NHẬT CARDS ---
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        c1 = DashboardCard("SỐ DƯ KHẢ DỤNG", f"{bal:,.0f} đ", "💵", "#2ecc71", f"Thu: {inc:,.0f} | Chi: {exp:,.0f}")
        c2 = DashboardCard("TÀI SẢN RÒNG", f"{net_worth:,.0f} đ", "💎", "#3498db", "Bao gồm cả nợ & quỹ")
        c3 = DashboardCard("NỢ PHẢI THU", f"{recv:,.0f} đ", "📝", "#f1c40f", f"Nợ phải trả: {owe:,.0f}")
        c4 = DashboardCard("QUỸ TIẾT KIỆM", f"{saved:,.0f} đ", "🐷", "#e74c3c", "Tổng các ví/heo đất")
        
        self.cards_layout.addWidget(c1)
        self.cards_layout.addWidget(c2)
        self.cards_layout.addWidget(c3)
        self.cards_layout.addWidget(c4)

        # --- CẬP NHẬT BIỂU ĐỒ TRÒN ---
        pie_series = QPieSeries()
        if bal > 0: pie_series.append("Tiền mặt", bal)
        if recv > 0: pie_series.append("Cho vay", recv)
        if saved > 0: pie_series.append("Tiết kiệm", saved)

        chart_pie = QChart()
        chart_pie.addSeries(pie_series)
        chart_pie.setTitle("Cơ Cấu Tài Sản")
        chart_pie.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart_pie.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        chart_pie.setBackgroundBrush(QBrush(QColor(255, 255, 255, 0)))
        self.pie_view.setChart(chart_pie)

        # --- CẬP NHẬT BIỂU ĐỒ CỘT ---
        set0 = QBarSet("Thu nhập"); set0.append([inc]); set0.setColor(QColor("#2ecc71"))
        set1 = QBarSet("Chi tiêu"); set1.append([exp]); set1.setColor(QColor("#e74c3c"))
        bar_series = QBarSeries(); bar_series.append(set0); bar_series.append(set1)

        chart_bar = QChart()
        chart_bar.addSeries(bar_series)
        chart_bar.setTitle("Tổng quan Thu/Chi")
        chart_bar.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart_bar.setBackgroundBrush(QBrush(QColor(255, 255, 255, 0)))
        self.bar_view.setChart(chart_bar)

        # --- CẬP NHẬT BẢNG GIAO DỊCH GẦN ĐÂY ---
        self.table_recent.setRowCount(0)
        for r in recent:
            row = self.table_recent.rowCount()
            self.table_recent.insertRow(row)

            d_date = r.get("date", "") if isinstance(r, dict) else getattr(r, 'date', '')
            d_desc = (r.get("description") or r.get("category", "")) if isinstance(r, dict) else (getattr(r, 'description', '') or getattr(r, 'category', ''))
            d_amt = r.get("amount", 0) if isinstance(r, dict) else getattr(r, 'amount', 0)
            d_type = r.get("type", "expense") if isinstance(r, dict) else getattr(r, 'type', 'expense')

            self.table_recent.setItem(row, 0, QTableWidgetItem(str(d_date)))
            self.table_recent.setItem(row, 1, QTableWidgetItem(str(d_desc)))
            amt_item = QTableWidgetItem(f"{float(d_amt):,.0f}đ")
            amt_item.setForeground(QColor("red") if d_type == "expense" else QColor("green"))
            self.table_recent.setItem(row, 2, amt_item)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay'):
            self.overlay.setGeometry(self.centralWidget().rect())
            if not self.overlay.initialized: self.overlay.init_particles()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainDashboard()
    window.show()
    sys.exit(app.exec())
