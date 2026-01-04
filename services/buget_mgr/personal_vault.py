import sys
import json
import random
import math
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# --- CẤU HÌNH ---
DATA_FILE = Path("budget_data.json")

THEMES = {
    "spring": {"bg": "#FFF8E1", "card": "#ffffff", "prog_bg": "#ffecb3", "prog_fill": "#ff6f00", "text": "#5d4037", "btn": "#d32f2f"},
    "summer": {"bg": "#E1F5FE", "card": "#ffffff", "prog_bg": "#b3e5fc", "prog_fill": "#0288d1", "text": "#01579b", "btn": "#0277bd"},
    "autumn": {"bg": "#FFF3E0", "card": "#ffffff", "prog_bg": "#ffe0b2", "prog_fill": "#e65100", "text": "#3e2723", "btn": "#ef6c00"},
    "winter": {"bg": "#ECEFF1", "card": "#ffffff", "prog_bg": "#cfd8dc", "prog_fill": "#455a64", "text": "#37474f", "btn": "#37474f"}
}

# --- UTILS ---
def format_money(amount):
    return f"{int(amount):,}".replace(",", ".") + " đ"

class Fund:
    def __init__(self, id, name, type, target=0, current=0, icon="💰", history=None):
        self.id = id
        self.name = name
        self.type = type # 'goal', 'monthly', 'pool'
        self.target = target
        self.current = current
        self.icon = icon
        self.history = history if history else [] # List of {date, amount, note, type}

    def to_dict(self):
        return self.__dict__

# --- HIỆU ỨNG (PARTICLES) ---
class Particle:
    def __init__(self, w, h, color):
        self.reset(w, h, True)
        self.color = color
    def reset(self, w, h, first=False):
        self.x = random.uniform(0, w)
        self.y = random.uniform(-h, 0) if not first else random.uniform(0, h)
        self.speed_y = random.uniform(1, 3)
        self.size = random.uniform(2, 6)
    def update(self, w, h):
        self.y += self.speed_y
        if self.y > h: self.reset(w, h)

class Overlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.particles = []
        self.timer = QTimer(self); self.timer.timeout.connect(self.anim)
    def init_p(self, color):
        if self.width() > 0:
            self.particles = [Particle(self.width(), self.height(), QColor(color)) for _ in range(40)]
            self.timer.start(30)
    def anim(self):
        for p in self.particles: p.update(self.width(), self.height())
        self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self.particles:
            p.setBrush(QBrush(pt.color))
            p.drawEllipse(QPointF(pt.x, pt.y), pt.size, pt.size)

# --- UI COMPONENTS ---

class FundDetailDialog(QDialog):
    """Dialog để Nạp tiền / Rút tiền và xem lịch sử"""
    def __init__(self, fund: Fund, parent=None, theme=None):
        super().__init__(parent)
        self.fund = fund
        self.theme = theme
        self.setWindowTitle(f"Chi tiết: {fund.name}")
        self.resize(500, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header Info
        top_frame = QFrame()
        top_frame.setStyleSheet(f"background-color: {self.theme['prog_bg']}; border-radius: 10px;")
        top_lo = QVBoxLayout(top_frame)
        
        lbl_icon = QLabel(self.fund.icon)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 40px;")
        
        self.lbl_balance = QLabel(format_money(self.fund.current))
        self.lbl_balance.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_balance.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {self.theme['text']}")
        
        lbl_target = QLabel(f"Mục tiêu: {format_money(self.fund.target)}")
        lbl_target.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        top_lo.addWidget(lbl_icon)
        top_lo.addWidget(self.lbl_balance)
        if self.fund.type != 'pool':
            top_lo.addWidget(lbl_target)
            
        layout.addWidget(top_frame)

        # Action Buttons
        btn_lo = QHBoxLayout()
        btn_deposit = QPushButton("➕ Nạp Tiền")
        btn_deposit.setStyleSheet("background-color: #2e7d32; color: white; padding: 10px; font-weight: bold;")
        btn_deposit.clicked.connect(self.deposit)
        
        btn_withdraw = QPushButton("➖ Rút/Chi")
        btn_withdraw.setStyleSheet("background-color: #c62828; color: white; padding: 10px; font-weight: bold;")
        btn_withdraw.clicked.connect(self.withdraw)
        
        btn_lo.addWidget(btn_deposit)
        btn_lo.addWidget(btn_withdraw)
        layout.addLayout(btn_lo)

        # History Table
        layout.addWidget(QLabel("📜 Lịch sử giao dịch:"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Ngày", "Nội dung", "Số tiền"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.reload_table()

    def reload_table(self):
        self.table.setRowCount(0)
        # Sort history mới nhất lên đầu
        sorted_hist = sorted(self.fund.history, key=lambda x: x['date'], reverse=True)
        for h in sorted_hist:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(h['date']))
            self.table.setItem(row, 1, QTableWidgetItem(h['note']))
            
            amount_item = QTableWidgetItem(format_money(h['amount']))
            if h['type'] == 'in':
                amount_item.setForeground(QColor("green"))
                amount_item.setText(f"+{format_money(h['amount'])}")
            else:
                amount_item.setForeground(QColor("red"))
                amount_item.setText(f"-{format_money(h['amount'])}")
            
            self.table.setItem(row, 2, amount_item)

    def deposit(self):
        amt, ok = QInputDialog.getInt(self, "Nạp tiền", "Số tiền nạp vào hũ:", 500000, 0, 1000000000, 50000)
        if ok and amt > 0:
            note, ok2 = QInputDialog.getText(self, "Ghi chú", "Nội dung:", text="Nạp quỹ")
            if not ok2: return
            
            self.fund.current += amt
            self.fund.history.append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "amount": amt,
                "note": note,
                "type": "in"
            })
            self.lbl_balance.setText(format_money(self.fund.current))
            self.reload_table()

    def withdraw(self):
        amt, ok = QInputDialog.getInt(self, "Rút tiền", f"Số tiền rút ra (Max: {self.fund.current}):", 0, 0, int(self.fund.current), 50000)
        if ok and amt > 0:
            note, ok2 = QInputDialog.getText(self, "Ghi chú", "Nội dung (VD: Mua xe, Gửi mẹ):")
            if not ok2: return

            self.fund.current -= amt
            self.fund.history.append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "amount": amt,
                "note": note,
                "type": "out"
            })
            self.lbl_balance.setText(format_money(self.fund.current))
            self.reload_table()


class FundCard(QFrame):
    clicked = pyqtSignal(object) # Emit fund object

    def __init__(self, fund: Fund, theme = None):
        super().__init__()
        self.fund = fund
        self.theme = theme
        self.setFixedSize(300, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_ui()
        self.update_style()

    def init_ui(self):
        lay = QVBoxLayout(self)
        
        # Header
        h_lay = QHBoxLayout()
        icon = QLabel(self.fund.icon)
        icon.setStyleSheet("font-size: 30px; background: transparent;")
        name = QLabel(self.fund.name)
        name.setStyleSheet("font-size: 16px; font-weight: bold;")
        name.setWordWrap(True)
        h_lay.addWidget(icon)
        h_lay.addWidget(name)
        lay.addLayout(h_lay)

        # Money
        self.lbl_money = QLabel()
        self.lbl_money.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        self.lbl_money.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay.addWidget(self.lbl_money)

        # Progress
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(10)
        self.pbar.setTextVisible(False)
        lay.addWidget(self.pbar)

        # Status Text
        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet("font-size: 11px; font-style: italic;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay.addWidget(self.lbl_status)

        self.refresh_data()

    def refresh_data(self):
        self.lbl_money.setText(format_money(self.fund.current))
        
        if self.fund.type == 'pool':
            # Quỹ dự phòng: Không có đích, chỉ có số dư
            self.pbar.setVisible(False)
            self.lbl_status.setText("Quỹ mở (Tích lũy & Sử dụng)")
            self.lbl_money.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {self.theme['text']}")
        
        elif self.fund.type == 'monthly':
            # Hàng tháng: Target là số tiền cần đóng tháng này
            percent = min(100, int((self.fund.current / self.fund.target) * 100)) if self.fund.target else 0
            self.pbar.setValue(percent)
            self.pbar.setVisible(True)
            
            if self.fund.current >= self.fund.target:
                self.lbl_status.setText("✅ Tháng này đã hoàn thành!")
                self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
            else:
                rem = self.fund.target - self.fund.current
                self.lbl_status.setText(f"Còn thiếu: {format_money(rem)}")
                self.lbl_status.setStyleSheet("color: #d32f2f;")

        else: # goal
            # Mục tiêu: Tiết kiệm mua gì đó
            percent = min(100, int((self.fund.current / self.fund.target) * 100)) if self.fund.target else 0
            self.pbar.setValue(percent)
            self.pbar.setVisible(True)
            self.lbl_status.setText(f"Đạt {percent}% mục tiêu")
            
    def update_style(self):
        t = self.theme
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {t['card']};
                border-radius: 15px;
                border: 2px solid {t['prog_bg']};
            }}
            QFrame:hover {{
                border: 2px solid {t['prog_fill']};
                background-color: #fffde7;
            }}
            QLabel {{ border: none; background: transparent; color: {t['text']}; }}
        """)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{ border: none; background-color: {t['prog_bg']}; border-radius: 5px; }}
            QProgressBar::chunk {{ background-color: {t['prog_fill']}; border-radius: 5px; }}
        """)

    def mousePressEvent(self, event):
        self.clicked.emit(self.fund)


class BudgetApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quản Lý Ngân Sách & Quỹ (Standalone)")
        self.resize(1000, 650)
        self.funds = []
        self.current_theme = "spring"
        
        self.init_data()
        self.init_ui()
        self.overlay = Overlay(self.centralWidget())
        self.overlay.show()
        self.overlay.raise_()
        self.apply_theme("spring")

    def init_data(self):
        if DATA_FILE.exists():
            try:
                raw_data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
                self.funds = [Fund(**d) for d in raw_data]
            except: self.funds = []

        if not self.funds:
            # Dữ liệu mẫu
            self.funds = [
                Fund(1, "Quỹ Dự Phòng Khẩn Cấp", "pool", 0, 20000000, "🛡️"),
                Fund(2, "Mua Ô tô", "goal", 500000000, 150000000, "🚗"),
                Fund(3, "Báo hiếu Bố Mẹ", "monthly", 5000000, 0, "👴"),
                Fund(4, "Bảo hiểm Nhân thọ", "monthly", 2000000, 2000000, "🏥")
            ]
            self.save_data()

    def save_data(self):
        data = [f.to_dict() for f in self.funds]
        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        title = QLabel("KÉT SẮT CỦA TÔI")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(THEMES.keys())
        self.combo_theme.currentTextChanged.connect(self.apply_theme)

        btn_add = QPushButton("➕ Tạo Hũ Mới")
        btn_add.setFixedSize(120, 40)
        btn_add.clicked.connect(self.add_fund_dialog)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(QLabel("Giao diện:"))
        header.addWidget(self.combo_theme)
        header.addWidget(btn_add)
        self.main_layout.addLayout(header)

        # Scroll Area for Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        self.container = QWidget()
        self.flow_layout = QFlowLayout(self.container)
        scroll.setWidget(self.container)
        self.main_layout.addWidget(scroll)

        self.render_cards()

    def render_cards(self):
        # Xóa cũ
        while self.flow_layout.count():
            child = self.flow_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        theme = THEMES[self.current_theme]
        for fund in self.funds:
            card = FundCard(fund, theme)
            card.clicked.connect(self.open_detail)
            self.flow_layout.addWidget(card)

    def open_detail(self, fund):
        dlg = FundDetailDialog(fund, self, THEMES[self.current_theme])
        dlg.exec()
        self.save_data()
        self.render_cards() # Refresh UI

    def add_fund_dialog(self):
        # Dialog tạo mới
        name, ok = QInputDialog.getText(self, "Tạo Hũ Mới", "Tên hũ (VD: Mua nhà, Quỹ đen...):")
        if not ok or not name: return
        
        types = ["Tích lũy mục tiêu (Mua xe, Nhà)", "Hàng tháng (Báo hiếu, Bảo hiểm)", "Quỹ mở (Dự phòng, Khẩn cấp)"]
        t_str, ok2 = QInputDialog.getItem(self, "Loại quỹ", "Chọn loại:", types, 0, False)
        if not ok2: return
        
        f_type = 'goal'
        if "Hàng tháng" in t_str: f_type = 'monthly'
        elif "Quỹ mở" in t_str: f_type = 'pool'
        
        target = 0
        if f_type != 'pool':
            target, ok3 = QInputDialog.getInt(self, "Mục tiêu", "Số tiền mục tiêu (hoặc định mức tháng):", 1000000, 0, 2000000000)
        
        icon, ok4 = QInputDialog.getText(self, "Biểu tượng", "Emoji đại diện:", text="💰")
        
        new_id = len(self.funds) + 1
        new_fund = Fund(new_id, name, f_type, target, 0, icon)
        self.funds.append(new_fund)
        self.save_data()
        self.render_cards()

    def apply_theme(self, key):
        self.current_theme = key
        t = THEMES[key]
        self.centralWidget().setStyleSheet(f"background-color: {t['bg']};")
        self.findChild(QPushButton).setStyleSheet(f"background-color: {t['btn']}; color: white; font-weight: bold; border-radius: 5px;")
        
        self.overlay.init_p(t['prog_fill'])
        self.render_cards()
        
    def resizeEvent(self, event):
        self.overlay.resize(self.size())
        super().resizeEvent(event)

# --- CUSTOM LAYOUT (Flow Layout) ---
class QFlowLayout(QLayout):
    def __init__(self, parent=None, margin=10, hSpacing=15, vSpacing=15):
        super().__init__(parent)
        self.m_hSpace = hSpacing
        self.m_vSpace = vSpacing
        self.setContentsMargins(margin, margin, margin, margin)
        self.itemList = []
    def addItem(self, item): self.itemList.append(item)
    def horizontalSpacing(self): return self.m_hSpace
    def verticalSpacing(self): return self.m_vSpace
    def count(self): return len(self.itemList)
    def itemAt(self, index): return self.itemList[index] if 0 <= index < len(self.itemList) else None
    def takeAt(self, index): return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect): super().setGeometry(rect); self.doLayout(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.itemList: size = size.expandedTo(item.minimumSize())
        return size + QSize(2 * self.contentsMargins().left(), 2 * self.contentsMargins().top())
    def doLayout(self, rect, testOnly):
        x, y = rect.x(), rect.y()
        lineHeight = 0
        for item in self.itemList:
            wid = item.widget()
            spaceX = self.horizontalSpacing(); spaceY = self.verticalSpacing()
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x(); y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            if not testOnly: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = nextX; lineHeight = max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = BudgetApp()
    window.show()
    sys.exit(app.exec())