import sys
import json
import random
import math
import uuid
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from models._tran import Transaction  # hoặc đường dẫn đúng
from datetime import date
from core.data_manager import DataManager 
from core._const import DATA_BUDGET

# --- CẤU HÌNH ---


THEME_FUND = {
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
class IconSelectionDialog(QDialog):
    def __init__(self, current_icon, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn Biểu Tượng")
        self.selected_icon = current_icon
        self.setFixedSize(400, 350)
        
        # Danh sách icon mẫu (Presets)
        self.presets = [
            "💰", "💎", "🏦", "🐷", "💵",  # Tiền bạc
            "🏠", "🚗", "🏍️", "💻", "📱",  # Tài sản
            "✈️", "🌏", "🏖️", "🎒", "🎫",  # Du lịch
            "🎓", "📚", "💍", "👶", "🎁",  # Đời sống
            "💊", "🏥", "🛡️", "🚨", "🔧",  # Khẩn cấp/Sức khỏe
            "🍔", "☕", "🎉", "🐶", "🐱"   # Khác
        ]
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Label hướng dẫn
        layout.addWidget(QLabel("Chọn từ danh sách:"))

        # 2. Lưới các icon mẫu
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)
        
        row, col = 0, 0
        for icon in self.presets:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setFont(QFont("Segoe UI Emoji", 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Khi click vào nút -> Chọn icon và đóng dialog
            btn.clicked.connect(lambda checked, i=icon: self.select_preset(i))
            
            # Highlight icon đang dùng hiện tại
            if icon == self.selected_icon:
                btn.setStyleSheet("background-color: #ffd700; border: 2px solid orange;")
            
            grid.addWidget(btn, row, col)
            col += 1
            if col > 4: # 5 cột
                col = 0
                row += 1
        
        layout.addWidget(grid_widget)
        
        # 3. Phần nhập tùy chỉnh (Custom)
        layout.addWidget(QLabel("Hoặc tự nhập icon/emoji khác:"))
        
        input_lo = QHBoxLayout()
        self.txt_custom = QLineEdit(self.selected_icon)
        self.txt_custom.setFont(QFont("Segoe UI Emoji", 14))
        self.txt_custom.setPlaceholderText("Paste emoji vào đây...")
        
        btn_ok = QPushButton("Sử dụng")
        btn_ok.clicked.connect(self.select_custom)
        
        input_lo.addWidget(self.txt_custom)
        input_lo.addWidget(btn_ok)
        layout.addLayout(input_lo)

    def select_preset(self, icon):
        self.selected_icon = icon
        self.accept() # Đóng dialog trả về kết quả True

    def select_custom(self):
        txt = self.txt_custom.text().strip()
        if txt:
            self.selected_icon = txt[0:2] # Lấy tối đa 2 ký tự để tránh vỡ giao diện
            self.accept()

    def get_icon(self):
        return self.selected_icon


# ============================================================
# 2. CLASS CHÍNH: FUND DETAIL DIALOG (ĐÃ HOÀN THIỆN)
# ============================================================
class FundDetailDialog(QDialog):
    """Dialog để Nạp tiền / Rút tiền / Chỉnh sửa và xem lịch sử"""
    def __init__(self, fund: Fund, parent=None, theme=None):
        super().__init__(parent)
        self.fund = fund
        self.theme = theme
        self.data_mgr = DataManager.instance()

        self.setWindowTitle(f"Chi tiết: {self.fund.name}")
        self.resize(500, 650) # Tăng chiều cao để chứa nút Edit
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- 1. Header Info ---
        top_frame = QFrame()
        top_frame.setStyleSheet(f"background-color: {self.theme['prog_bg']}; border-radius: 10px;")
        top_lo = QVBoxLayout(top_frame)
        
        # Icon
        self.lbl_icon = QLabel(self.fund.icon)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("font-size: 40px;")
        
        # Tên Quỹ
        self.lbl_name = QLabel(self.fund.name)
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 5px;")

        # Số dư
        self.lbl_balance = QLabel(f"{self.fund.current:,.0f} đ")
        self.lbl_balance.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_balance.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {self.theme['text']}")
        
        # Mục tiêu (ẩn nếu là quỹ mở)
        self.lbl_target = QLabel(f"Mục tiêu: {self.fund.target:,.0f} đ")
        self.lbl_target.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        top_lo.addWidget(self.lbl_icon)
        top_lo.addWidget(self.lbl_name)
        top_lo.addWidget(self.lbl_balance)
        if self.fund.type != 'pool':
            top_lo.addWidget(self.lbl_target)
            
        layout.addWidget(top_frame)

        # --- 2. Action Buttons (Nạp / Rút) ---
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

        # --- 3. Management Buttons (Sửa / Xóa) ---
        mgmt_lo = QHBoxLayout()
        
        btn_edit = QPushButton("✏️ Chỉnh sửa & Đổi Icon")
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.clicked.connect(self.edit_fund) # <--- Hàm xử lý sửa
        
        btn_delete = QPushButton("🗑️ Xóa Hũ")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet("color: red;")
        btn_delete.clicked.connect(self.delete_fund) # <--- Hàm xử lý xóa

        mgmt_lo.addWidget(btn_edit)
        mgmt_lo.addWidget(btn_delete)
        layout.addLayout(mgmt_lo)

        # --- 4. History Table ---
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
            
            amount_item = QTableWidgetItem(f"{h['amount']:,.0f}")
            if h['type'] == 'in':
                amount_item.setForeground(QColor("green"))
                amount_item.setText(f"+{h['amount']:,.0f}")
            else:
                amount_item.setForeground(QColor("red"))
                amount_item.setText(f"-{h['amount']:,.0f}")
            
            self.table.setItem(row, 2, amount_item)

    # --- LOGIC NẠP / RÚT ---
    def deposit(self):
        amt, ok = QInputDialog.getInt(self, "Nạp tiền", "Số tiền nạp vào hũ:", 500000, 0, 1000000000, 50000)
        if ok and amt > 0:
            note, ok2 = QInputDialog.getText(self, "Ghi chú", "Nội dung:", text="Nạp quỹ")
            if not ok2: return

            # Gọi DataManager xử lý (KHÔNG tự cộng tiền ở đây để tránh lệch data)
            self.data_mgr.execute_fund_transaction(
                fund_id=self.fund.id, 
                amount=amt, 
                note=note, 
                is_deposit=True
            )
            
            # Cập nhật UI
            self.lbl_balance.setText(f"{self.fund.current:,.0f} đ")
            self.reload_table()
            if self.parent(): self.parent().render_cards()

    def withdraw(self):
        amt, ok = QInputDialog.getInt(self, "Rút tiền", f"Số tiền rút ra (Max: {self.fund.current}):", 0, 0, int(self.fund.current), 50000)
        if ok and amt > 0:
            note, ok2 = QInputDialog.getText(self, "Ghi chú", "Nội dung (VD: Mua xe, Gửi mẹ):")
            if not ok2: return

            self.data_mgr.execute_fund_transaction(
                fund_id=self.fund.id, 
                amount=amt, 
                note=note, 
                is_deposit=False
            )

            self.lbl_balance.setText(f"{self.fund.current:,.0f} đ")
            self.reload_table()
            if self.parent(): self.parent().render_cards()

    # --- LOGIC SỬA / XÓA (MỚI) ---
    def edit_fund(self):
        """Hàm chỉnh sửa: Tên, Mục tiêu và Icon"""
        
        # 1. Sửa Tên
        new_name, ok = QInputDialog.getText(self, "Sửa tên", "Tên hũ:", text=self.fund.name)
        if ok and new_name:
            self.fund.name = new_name

        # 2. Sửa Mục tiêu (nếu cần)
        if self.fund.type != 'pool':
            new_target, ok2 = QInputDialog.getInt(
                self, "Sửa mục tiêu", 
                "Số tiền mục tiêu mới:", 
                value=int(self.fund.target), 
                min=0, max=2000000000, step=100000
            )
            if ok2:
                self.fund.target = float(new_target)
        
        # 3. CHỌN ICON (SỬ DỤNG DIALOG MỚI)
        icon_dlg = IconSelectionDialog(self.fund.icon, self)
        if icon_dlg.exec():
            # Nếu user chọn icon và bấm OK/Sử dụng
            self.fund.icon = icon_dlg.get_icon()

        # 4. Lưu xuống DataManager
        self.data_mgr.update_fund(self.fund)

        # 5. Cập nhật UI ngay lập tức
        self.lbl_name.setText(self.fund.name)
        self.lbl_icon.setText(self.fund.icon)
        self.setWindowTitle(f"Chi tiết: {self.fund.name}")
        if self.fund.type != 'pool':
            self.lbl_target.setText(f"Mục tiêu: {self.fund.target:,.0f} đ")
        
        # Refresh màn hình cha
        if self.parent(): self.parent().render_cards()
        
        QMessageBox.information(self, "Đã lưu", "Cập nhật thông tin thành công!")

    def delete_fund(self):
        """Xóa hũ"""
        confirm = QMessageBox.question(
            self, "Xác nhận xóa", 
            f"Bạn có chắc muốn xóa vĩnh viễn hũ '{self.fund.name}'?\n(Tiền sử giao dịch sẽ không mất, nhưng hũ sẽ biến mất).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.data_mgr.delete_fund(self.fund.id)
            self.close()


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
        
        # self.init_data()
        self.data_mgr = DataManager.instance()
        self.data_mgr.data_changed.connect(self.on_data_changed)
        self.refresh_funds_list()
        self.init_ui()
        self.overlay = Overlay(self.centralWidget())
        self.overlay.show()
        self.overlay.raise_()
        self.apply_theme("spring")



    def refresh_funds_list(self):
            """Lấy danh sách quỹ mới nhất từ Engine"""
            # DataManager.funds trỏ tới BudgetEngine.funds
            self.funds = self.data_mgr.funds 
            
            # Nếu chưa có quỹ nào (lần đầu chạy), có thể gọi hàm tạo sample data CỦA ENGINE (nếu muốn)
            # Nhưng ở UI thì chỉ nên hiển thị danh sách rỗng nếu chưa có
            
    def on_data_changed(self):
        """Khi DataManager bắn tín hiệu thay đổi, UI tự load lại"""
        self.refresh_funds_list()
        self.render_cards()

    def init_data(self):
        if DATA_BUDGET.exists():
            try:
                raw_data = json.loads(DATA_BUDGET.read_text(encoding='utf-8'))
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

    # def save_data(self):
    #     data = [f.to_dict() for f in self.funds]
    #     DATA_BUDGET.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

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
        self.combo_theme.addItems(THEME_FUND.keys())
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
            
        theme = THEME_FUND[self.current_theme]
        for fund in self.funds:
            card = FundCard(fund, theme)
            card.clicked.connect(self.open_detail)
            self.flow_layout.addWidget(card)

    def open_detail(self, fund):
        dlg = FundDetailDialog(fund, self, THEME_FUND[self.current_theme])
        dlg.exec()
        self.render_cards() # Refresh UI

    def add_fund_dialog(self):
            """Hộp thoại tạo hũ mới - Đã kết nối với DataManager"""
            
            # 1. Nhập Tên
            name, ok = QInputDialog.getText(self, "Tạo Hũ Mới", "Tên hũ (VD: Mua nhà, Quỹ đen...):")
            if not ok or not name.strip(): return
            
            # 2. Chọn Loại
            types = [
                "Tích lũy mục tiêu (Mua xe, Nhà)", 
                "Hàng tháng (Báo hiếu, Bảo hiểm)", 
                "Quỹ mở (Dự phòng, Khẩn cấp)"
            ]
            t_str, ok2 = QInputDialog.getItem(self, "Loại quỹ", "Chọn loại:", types, 0, False)
            if not ok2: return
            
            # Mapping từ text sang code
            f_type = 'goal'
            if "Hàng tháng" in t_str: f_type = 'monthly'
            elif "Quỹ mở" in t_str: f_type = 'pool'
            
            # 3. Nhập Mục tiêu (Target)
            target = 0.0
            if f_type != 'pool':
                # Nếu không phải quỹ mở, bắt buộc nhập mục tiêu
                val, ok3 = QInputDialog.getInt(
                    self, "Mục tiêu", 
                    "Số tiền mục tiêu (hoặc định mức tháng):", 
                    1000000, 0, 2000000000, 100000
                )
                # Nếu user bấm Cancel ở bước này thì hủy luôn việc tạo
                if not ok3: return 
                target = float(val)
            
            # 4. Nhập Icon
            icon, ok4 = QInputDialog.getText(self, "Biểu tượng", "Emoji đại diện:", text="💰")
            if not ok4: icon = "💰" # Nếu cancel thì lấy mặc định
            
            # 5. Tạo Object Fund và Gửi sang DataManager
            # Lưu ý: Import uuid ở đầu file nếu chưa có
            import uuid 
            
            new_fund = Fund(
                id=str(uuid.uuid4()),      # Sinh ID ngẫu nhiên dạng chuỗi
                name=name, 
                type=f_type,               # Lưu ý: Model Fund của bạn cần có trường 'type' nếu muốn phân loại
                target=target, 
                current=0.0, 
                icon=icon
            )
            
            # --- THAY ĐỔI QUAN TRỌNG NHẤT ---
            # Không tự append vào list và không tự save file
            # Hãy để DataManager làm việc đó để đảm bảo đồng bộ
            self.data_mgr.add_fund(new_fund)
            
            # UI sẽ tự cập nhật nhờ signal data_changed, 
            # nhưng gọi thêm render_cards() để phản hồi tức thì cho mượt
            self.render_cards()

    def apply_theme(self, key):
        self.current_theme = key
        t = THEME_FUND[key]
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