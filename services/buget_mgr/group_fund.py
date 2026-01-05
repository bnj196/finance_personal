import sys
import json
import csv
import random
import math
import uuid
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


from models._tran import Transaction
from models._budget import Goal # Import model Goal
from core.data_manager import DataManager
# ======================
# 1. CẤU HÌNH THEME
# ======================
THEMES = {
    "spring": {
        "name": "Xuân", "bg": "#FFF8E1", "sec": "#b30000", "acc": "#FFD700", "txt": "#5D4037", "btn": "#d91e18"
    },
    "summer": {
        "name": "Hạ", "bg": "#E1F5FE", "sec": "#0277BD", "acc": "#4FC3F7", "txt": "#01579B", "btn": "#0288d1"
    },
    "autumn": {
        "name": "Thu", "bg": "#FFF3E0", "sec": "#E65100", "acc": "#FFB74D", "txt": "#3E2723", "btn": "#f57c00"
    },
    "winter": {
        "name": "Đông", "bg": "#ECEFF1", "sec": "#263238", "acc": "#90A4AE", "txt": "#37474F", "btn": "#455A64"
    }
}

class GoalCard(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, index, goal_data, theme): 
        super().__init__()
        self.index = index
        self.theme = theme
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(280, 160)
        
        # ---------------------------------------------------------
        # 1. XỬ LÝ DỮ LIỆU THÔNG MINH (DICT -> OBJECT)
        # ---------------------------------------------------------
        if isinstance(goal_data, dict):
            # Nếu truyền vào là Dict (do code cũ hoặc load json raw)
            # Tự động convert sang Object Goal để tránh lỗi .name
            try:
                # Lọc key để tránh lỗi nếu dict có trường lạ
                valid_keys = Goal.__init__.__code__.co_varnames
                clean_data = {k: v for k, v in goal_data.items() if k in valid_keys}
                self.goal = Goal(**clean_data)
                
                # Gán lại members (vì dataclass init có thể không xử lý sâu list dict)
                if "members" in goal_data:
                    self.goal.members = goal_data["members"]
            except Exception as e:
                print(f"⚠️ GoalCard Error: {e}")
                self.goal = Goal(name="Lỗi Dữ Liệu", target=1)
        else:
            # Nếu đã là Object chuẩn -> Dùng luôn
            self.goal = goal_data

        # ---------------------------------------------------------
        # 2. GIAO DIỆN (UI LAYOUT)
        # ---------------------------------------------------------
        
        # Style
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid {theme['acc']};
                border-radius: 15px;
            }}
            QFrame:hover {{
                background-color: white;
                border: 2px solid {theme['sec']};
                margin-top: -2px; /* Hiệu ứng nổi lên nhẹ */
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # --- Header: Icon + Name ---
        header = QHBoxLayout()
        icon = QLabel("💰") # Bạn có thể thay bằng self.goal.icon nếu model có
        icon.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        
        lbl_name = QLabel(self.goal.name) 
        lbl_name.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme['txt']}; border: none; background: transparent;")
        lbl_name.setWordWrap(True) # Cho phép xuống dòng nếu tên dài
        
        header.addWidget(icon)
        header.addWidget(lbl_name)
        header.addStretch()
        layout.addLayout(header)
        
        # --- Stats Calculation ---
        target = self.goal.target if self.goal.target else 1
        # Tính tổng contribution từ list members (list dict)
        current = sum(m.get("contribution", 0) for m in self.goal.members)
        
        # Tính % hiển thị
        real_pct = int(current / target * 100)
        display_pct = min(100, real_pct) # Bar chỉ chạy max 100
        
        # Logic màu sắc
        status_icon = ""
        if real_pct >= 100:
            bar_color = "#9b59b6" # Tím (Vượt chỉ tiêu)
            status_icon = "🔥"
            money_color = "#8e44ad"
        else:
            bar_color = theme['sec']
            money_color = theme['sec']

        # --- Label Tiền ---
        lbl_money = QLabel(f"{current:,.0f}k / {target:,.0f}k {status_icon}")
        lbl_money.setStyleSheet(f"color: {money_color}; font-weight: bold; border: none; background: transparent; font-size: 14px;")
        lbl_money.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(lbl_money)
        
        # --- Progress Bar ---
        pbar = QProgressBar()
        pbar.setValue(display_pct)
        pbar.setFixedHeight(12)
        pbar.setTextVisible(False)
        pbar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #bdc3c7; border-radius: 6px; background: #ecf0f1; }}
            QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 6px; }}
        """)
        layout.addWidget(pbar)
        
        # --- Footer ---
        mem_count = len(self.goal.members)
        lbl_mem = QLabel(f"👥 {mem_count} thành viên • {real_pct}%")
        lbl_mem.setStyleSheet("color: gray; font-size: 11px; border: none; background: transparent; font-style: italic;")
        layout.addWidget(lbl_mem)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)

# ======================
# 3. GRAPHICS ITEMS (Card Thành Viên)
# ======================
class MemberNode(QGraphicsItem):
    """
    Node đại diện cho một thành viên trong Quỹ Nhóm.
    - Có khả năng hiển thị Thu/Chi/Đóng góp.
    - Có menu ngữ cảnh để Sửa/Xóa/Chi tiêu.
    - Tự động đồng bộ với DataManager nếu role là 'owner'.
    """
    def __init__(self, name, income=0, expense=0, contribution=0, role="member"):
        super().__init__()
        self.name = name
        self.income = income
        self.expense = expense
        self.contribution = contribution # Số dư hiện tại của người này trong quỹ
        self.role = role # "owner" (Tôi) hoặc "member" (Người khác)
        
        # Kết nối tới DataManager
        self.data_mgr = DataManager.instance()

        # Cấu hình Graphics Item
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
        # Cache rect để tối ưu hiệu năng vẽ
        self._rect = QRectF(-70, -50, 140, 100)

    def boundingRect(self):
        return self._rect
    
    def paint(self, painter, option, widget):
        """Vẽ Node lên màn hình"""
        # 1. Xác định màu sắc dựa trên Role
        is_owner = (self.role == "owner")
        is_selected = self.isSelected()
        
        # Viền: Vàng đậm nếu là Owner, Xám nếu là Member. Xanh nếu đang chọn.
        if is_selected:
            border_color = QColor("#2980b9") # Xanh dương khi chọn
            border_width = 3
        elif is_owner:
            border_color = QColor("#f1c40f") # Vàng Gold nếu là Tôi
            border_width = 3
        else:
            border_color = QColor("#bdc3c7") # Xám mặc định
            border_width = 1
            
        # Nền Header: Vàng nhạt nếu Owner, Xám nhạt nếu Member
        header_bg = QColor("#fff9c4") if is_owner else QColor("#ecf0f1")

        # 2. Vẽ Bóng đổ (Shadow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawRoundedRect(self._rect.translated(4, 4), 10, 10)
        
        # 3. Vẽ Thân thẻ (Body)
        painter.setBrush(QColor("white"))
        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(self._rect, 10, 10)
        
        # 4. Vẽ Header (Chứa tên)
        painter.setBrush(header_bg)
        painter.setPen(Qt.PenStyle.NoPen)
        # Vẽ phần trên bo góc, phần dưới phẳng để nối với body
        path = QPainterPath()
        path.addRoundedRect(QRectF(-70, -50, 140, 30), 10, 10)
        painter.drawPath(path)
        # Che góc bo dưới của header để nó liền mạch
        painter.drawRect(QRectF(-70, -30, 140, 10)) 
        
        # 5. Vẽ Text (Tên & Số liệu)
        # Tên
        painter.setPen(QColor("#2c3e50"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(-70, -50, 140, 30), Qt.AlignmentFlag.AlignCenter, self.name)
        
        # Số liệu (Thu / Chi / Dư)
        painter.setFont(QFont("Segoe UI", 9))
        stats_text = (
            f"Thu: {self.income}k\n"
            f"Chi: {self.expense}k\n"
            f"Dư: {self.contribution}k"
        )
        painter.drawText(QRectF(-65, -10, 130, 50), Qt.AlignmentFlag.AlignCenter, stats_text)

        # Icon vương miện nếu là Owner
        if is_owner:
            painter.setFont(QFont("Segoe UI Emoji", 12))
            painter.drawText(QRectF(50, -60, 20, 20), Qt.AlignmentFlag.AlignCenter, "👑")

    def contextMenuEvent(self, event):
        """Menu chuột phải"""
        menu = QMenu()
        menu.setStyleSheet("QMenu { background: white; border: 1px solid gray; font-size: 12px; }")
        
        # Action: Chi tiêu
        action_spend = menu.addAction("💸 Chi tiêu / Rút quỹ")
        action_spend.triggered.connect(self.spend_money)
        
        # Action: Nạp thêm (Optional)
        action_income = menu.addAction("💰 Nạp thêm")
        action_income.triggered.connect(self.add_income)

        menu.addSeparator()
        
        # Action: Edit / Delete
        menu.addAction("✏️ Sửa thông tin", self.edit_info)
        menu.addAction("🗑️ Xóa thành viên", self.delete_node)
        
        menu.exec(event.screenPos())

    # ==================================================
    # LOGIC CHÍNH: CHI TIÊU
    # ==================================================
    def spend_money(self):
        """Xử lý khi thành viên chi tiền"""
        # 1. Kiểm tra số dư trước
        if self.contribution <= 0:
            QMessageBox.warning(None, "Không thể chi tiêu", f"{self.name} không còn tiền trong quỹ (Số dư: {self.contribution}k).")
            return

        # 2. Nhập số tiền
        amt_k, ok = QInputDialog.getInt(None, "Chi tiêu quỹ", 
                                      f"Nhập số tiền {self.name} chi (Tối đa {self.contribution}k):", 
                                      0, 0, self.contribution, 10) # Max set là self.contribution
        if not ok or amt_k <= 0: return
        
        # Kiểm tra lại lần nữa cho chắc
        if amt_k > self.contribution:
            QMessageBox.warning(None, "Lỗi", "Số tiền chi vượt quá số dư hiện tại!")
            return

        # 3. Nhập lý do
        note, ok2 = QInputDialog.getText(None, "Nội dung", "Lý do chi tiêu:")
        if not ok2: return
        if not note: note = "Chi tiêu quỹ chung"

        # 4. Cập nhật dữ liệu
        self.expense += amt_k           # Tăng tổng chi để theo dõi
        self.contribution -= amt_k      # Giảm số dư
        
        self.update() 
        self.scene().views()[0].main_window.update_detail_stats()

        # 5. Đồng bộ ví thật (Nếu là Owner)
        if self.role == "owner":
            self._sync_transaction_expense(amt_k, note)


    def _sync_transaction_expense(self, amt_k, note):
        """Hàm private: Tạo Transaction thật trong DataManager"""
        try:
            real_amount = amt_k * 1000 # Đổi từ k -> đồng
            
            new_trans = Transaction(
                id=str(uuid.uuid4()),
                date=date.today().isoformat(),
                category="Chi tiêu Quỹ Nhóm", # Danh mục riêng để dễ track
                amount=real_amount,
                type="expense",               # Dòng tiền ra
                role="CaNhan",                # Vai trò ví chính
                description=f"[Quỹ Nhóm] {note}",
                is_recurring=False
            )
            
            self.data_mgr.add_transaction(new_trans)
            
            QMessageBox.information(None, "Đồng bộ thành công", 
                                    f"Đã trừ {real_amount:,.0f}đ vào Ví cá nhân của bạn!")
        except Exception as e:
            QMessageBox.warning(None, "Lỗi đồng bộ", f"Không thể tạo giao dịch: {e}")

    # ==================================================
    # CÁC LOGIC KHÁC (Sửa, Xóa, Nạp)
    # ==================================================
    def add_income(self):
        """Nạp thêm tiền vào quỹ (Logic ngược lại với Spend)"""
        amt_k, ok = QInputDialog.getInt(None, "Nạp quỹ", "Số tiền nạp (k):", 0, 0, 1000000, 50)
        if ok and amt_k > 0:
            self.income += amt_k
            self.contribution += amt_k
            self.update()
            self.scene().views()[0].main_window.update_detail_stats()
            # Tương tự: Nếu là owner thì có thể tạo Transaction type="expense" (Nạp tiền đi)
            # Tùy bạn muốn triển khai hay không.

    def edit_info(self):
        """Hộp thoại sửa thông tin thủ công"""
        d = QDialog()
        d.setWindowTitle("Sửa thông tin")
        l = QFormLayout(d)
        
        n = QLineEdit(self.name)
        i = QLineEdit(str(self.income))
        e = QLineEdit(str(self.expense))
        c = QLineEdit(str(self.contribution))
        
        # Thêm combo box chọn Role
        cb_role = QComboBox()
        cb_role.addItems(["member", "owner"])
        cb_role.setCurrentText(self.role)

        l.addRow("Tên:", n)
        l.addRow("Tổng Thu (k):", i)
        l.addRow("Tổng Chi (k):", e)
        l.addRow("Số Dư (k):", c)
        l.addRow("Vai trò:", cb_role)
        
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        l.addRow(bb)
        
        if d.exec():
            # Cập nhật dữ liệu
            self.name = n.text()
            try:
                self.income = int(i.text())
                self.expense = int(e.text())
                self.contribution = int(c.text())
            except: pass
            
            self.role = cb_role.currentText()
            
            self.update() # Vẽ lại (nếu đổi role thì màu sẽ đổi)
            self.scene().views()[0].main_window.update_detail_stats()

    def delete_node(self):
        """Xóa node khỏi scene"""
        # Gọi về Main Window để xóa khỏi list quản lý
        self.scene().views()[0].main_window.remove_member(self)
        # Xóa khỏi màn hình
        self.scene().removeItem(self)
# ======================
# 4. CUSTOM VIEW
# ======================
class EditorGraphicsView(QGraphicsView):
    def __init__(self, scene, main_window):
        super().__init__(scene)
        self.main_window = main_window
        self.setStyleSheet("background: transparent; border: none;")
    
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if not item:
            menu = QMenu()
            menu.addAction("➕ Thêm thành viên", lambda: self.main_window.add_member_dialog(self.mapToScene(event.pos())))
            menu.exec(event.globalPos())
        else: super().contextMenuEvent(event)
class GroupFundMgr(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quản Lý Ngân Sách - Đa Quỹ")
        self.resize(1200, 800)
        
        # --- KẾT NỐI DATA MANAGER ---
        self.data_mgr = DataManager.instance()
        
        # [QUAN TRỌNG] TRỎ THẲNG VÀO LIST CỦA ENGINE (Tham chiếu)
        # Thay vì self.goals = [], ta lấy list từ engine
        self.goals = self.data_mgr.goals 
        
        self.current_goal_index = -1
        self.members_in_scene = [] 
        self.current_theme_key = "spring"

        # --- UI SETUP ---
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.dashboard_widget = QWidget()
        self.setup_dashboard()
        self.stack.addWidget(self.dashboard_widget)

        self.editor_widget = QWidget()
        self.setup_editor()
        self.stack.addWidget(self.editor_widget)

        # Nếu chưa có dữ liệu nào trong JSON, tạo mẫu (và lưu luôn)
        if not self.goals:
            self.create_sample_data()
        
        self.apply_theme("spring")
        self.refresh_dashboard()

    def create_sample_data(self):
        """Tạo dữ liệu mẫu và lưu xuống ổ cứng thông qua DataManager"""
        # Tạo Object Goal
        g1 = Goal(name="Quỹ Du Lịch", target=20000)
        g2 = Goal(name="Quỹ Ăn Uống", target=5000)
        
        # Gọi hàm save của DataManager
        self.data_mgr.add_goal(g1)
        self.data_mgr.add_goal(g2)



    # def load_initial_data(self):
    #     # Nếu bạn muốn load từ DataManager.budget_engine.goals thì viết ở đây
    #     # Hiện tại dùng sample data nếu list rỗng
    #     if not self.goals:
    #         self.goals.append({"name": "Quỹ Du Lịch", "target": 20000, "members": []})
    #         self.goals.append({"name": "Quỹ Ăn Uống", "target": 5000, "members": []})

    # ==========================
    # DASHBOARD SETUP
    # ==========================
    def setup_dashboard(self):
        layout = QVBoxLayout(self.dashboard_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        lbl_title = QLabel("QUẢN LÝ QUỸ CHUNG")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        
        # Theme Selector
        self.combo_theme = QComboBox(); self.combo_theme.addItems(["spring", "summer", "autumn", "winter"])
        self.combo_theme.currentTextChanged.connect(self.apply_theme)
        
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(QLabel("Giao diện:"))
        header.addWidget(self.combo_theme)
        layout.addLayout(header)

        # Global Stats
        self.global_stats_frame = QFrame()
        self.global_stats_frame.setObjectName("stats")
        stats_lo = QHBoxLayout(self.global_stats_frame)
        self.lbl_total_funds = QLabel("Tổng quỹ: 0")
        self.lbl_total_money = QLabel("Tổng tiền: 0k")
        stats_lo.addWidget(self.lbl_total_funds)
        stats_lo.addStretch()
        stats_lo.addWidget(self.lbl_total_money)
        layout.addWidget(self.global_stats_frame)

        # Toolbar
        toolbar = QHBoxLayout()
        btn_add = self.create_btn("➕ Tạo Quỹ Mới", self.add_new_goal)
        btn_import = self.create_btn("📥 Nhập Data", self.import_data)
        btn_export = self.create_btn("📤 Xuất Data", self.export_data)
        toolbar.addWidget(btn_add)
        toolbar.addStretch()
        toolbar.addWidget(btn_import)
        toolbar.addWidget(btn_export)
        layout.addLayout(toolbar)

        # Scroll Area for Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        self.cards_container = QWidget()
        
        # Dùng Grid Layout để hiển thị Card đẹp hơn
        self.grid_layout = QGridLayout(self.cards_container)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

    def refresh_dashboard(self):
            # Xóa card cũ
            for i in reversed(range(self.grid_layout.count())): 
                widget = self.grid_layout.itemAt(i).widget()
                if widget: widget.setParent(None)

            t = THEMES[self.current_theme_key]
            total_money = 0
            row, col = 0, 0
            max_cols = 3

            # Lặp qua các Goal OBJECT (chứ không phải dict)
            # print(self.goals)cls
            
            for idx, goal_obj in enumerate(self.goals):
                card = GoalCard(idx, goal_obj, t) # Truyền Object vào Card
                card.clicked.connect(self.open_editor)
                
                # Context Menu
                card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                card.customContextMenuRequested.connect(lambda pos, i=idx: self.card_context_menu(pos, i))
                
                self.grid_layout.addWidget(card, row, col)
                
                col += 1
                if col >= max_cols: col = 0; row += 1
                
                # Tính tổng tiền (members là list dict bên trong Object Goal)
                current_fund = sum(m["contribution"] for m in goal_obj.members)
                total_money += current_fund

            self.lbl_total_funds.setText(f"Số lượng quỹ: {len(self.goals)}")
            self.lbl_total_money.setText(f"Tổng tài sản: {total_money:,}k")

    def add_new_goal(self):
        name, ok = QInputDialog.getText(self, "Tạo Quỹ", "Tên quỹ mới:")
        if ok and name:
            # 1. Tạo Object Goal mới
            new_goal = Goal(name=name, target=10000) # ID tự sinh trong model
            
            # 2. Gọi DataManager để thêm và lưu file
            self.data_mgr.add_goal(new_goal)
            
            self.refresh_dashboard()

    def card_context_menu(self, pos, index):
        menu = QMenu()
        delete = menu.addAction("🗑️ Xóa Quỹ Này")
        action = menu.exec(QCursor.pos())
        if action == delete:
            goal_to_del = self.goals[index] # Lấy Object cần xóa
            confirm = QMessageBox.question(self, "Xóa", f"Xóa quỹ '{goal_to_del.name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                # Gọi DataManager để xóa và lưu file
                self.data_mgr.delete_goal(goal_to_del.id)
                self.refresh_dashboard()

    # ==========================
    # EDITOR SETUP (DETAIL VIEW)
    # ==========================
    def setup_editor(self):
        layout = QHBoxLayout(self.editor_widget)
        layout.setContentsMargins(0,0,0,0)

        # --- LEFT SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(300)
        self.sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(self.sidebar)

        # Back Button
        btn_back = QPushButton("⬅️ Về Trang Chủ")
        btn_back.setStyleSheet("background-color: #7f8c8d; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_back.clicked.connect(self.back_to_dashboard)
        sb_layout.addWidget(btn_back)

        # Goal Info
        self.ed_name = QLineEdit()
        self.ed_target = QLineEdit()
        form = QFormLayout()
        form.addRow("Tên:", self.ed_name)
        form.addRow("Mục tiêu:", self.ed_target)
        sb_layout.addLayout(form)
        
        btn_save_meta = self.create_btn("💾 Cập nhật thông tin", self.save_current_meta)
        sb_layout.addWidget(btn_save_meta)
        sb_layout.addWidget(QLabel("---"))

        # Add Member Quick Form
        grp_add = QGroupBox("Thêm thành viên")
        form_add = QFormLayout(grp_add)
        self.inp_name = QLineEdit()
        self.inp_cont = QLineEdit("0")
        form_add.addRow("Tên:", self.inp_name)
        form_add.addRow("Góp:", self.inp_cont)
        btn_add_mem = self.create_btn("➕ Thêm vào hình", self.add_member_from_sidebar)
        form_add.addRow(btn_add_mem)
        sb_layout.addWidget(grp_add)

        # Detail Stats
        self.lbl_detail_stats = QLabel()
        self.lbl_detail_stats.setStyleSheet("font-size: 13px; line-height: 150%;")
        sb_layout.addWidget(self.lbl_detail_stats)
        
        # Progress Bar in Editor
        self.ed_pbar = QProgressBar()
        self.ed_pbar.setTextVisible(True)
        sb_layout.addWidget(self.ed_pbar)

        sb_layout.addStretch()
        layout.addWidget(self.sidebar)

        # --- RIGHT SCENE ---
        self.scene = QGraphicsScene()
        # EditorGraphicsView phải được import hoặc định nghĩa
        self.view = EditorGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)

    def open_editor(self, index):
            self.current_goal_index = index
            goal = self.goals[index] # Đây là Object Goal
            
            # Load Data to UI (.name, .target)
            self.ed_name.setText(goal.name)
            self.ed_target.setText(str(goal.target))
            
            # Load Scene
            self.scene.clear()
            self.members_in_scene = []
            
            # goal.members là list dict (đã định nghĩa trong Model)
            for m in goal.members:
                role = m.get("role", "member")
                # Tạo node đồ họa
                node = MemberNode(
                    name=m["name"], 
                    income=m["income"], 
                    expense=m["expense"], 
                    contribution=m["contribution"],
                    role=role
                )
                node.setPos(m.get("x", 100), m.get("y", 100))
                self.scene.addItem(node)
                self.members_in_scene.append(node)
            
            self.update_detail_stats()
            self.stack.setCurrentIndex(1)

    def save_current_meta(self):
        """Lưu tên và mục tiêu xuống file"""
        if self.current_goal_index == -1: return
        
        # Lấy object hiện tại
        goal = self.goals[self.current_goal_index]
        
        # Cập nhật thuộc tính object
        goal.name = self.ed_name.text()
        try: goal.target = int(self.ed_target.text())
        except: pass
        
        # --- QUAN TRỌNG: GỌI UPDATE ĐỂ LƯU XUỐNG Ổ CỨNG ---
        self.data_mgr.update_goal(goal)
        # --------------------------------------------------
        
        self.update_detail_stats()
        QMessageBox.information(self, "OK", "Đã lưu thông tin!")

    def save_current_scene(self):
        """Lưu vị trí và thông tin các node xuống file"""
        if self.current_goal_index == -1: return
        
        # 1. Thu thập dữ liệu từ các Node đồ họa
        m_data = []
        for m in self.members_in_scene:
            m_data.append({
                "name": m.name, 
                "income": m.income, 
                "expense": m.expense, 
                "contribution": m.contribution,
                "role": m.role,
                "x": m.x(), "y": m.y()
            })
        
        # 2. Cập nhật vào Object Goal
        goal = self.goals[self.current_goal_index]
        goal.members = m_data
        
        # 3. GỌI DATA MANAGER ĐỂ LƯU JSON
        self.data_mgr.update_goal(goal)

    def back_to_dashboard(self):
        self.save_current_scene() # Save positions & data
        self.refresh_dashboard()
        self.stack.setCurrentIndex(0)

    # ==========================
    # LOGIC FUNCTIONS
    # ==========================
    def create_btn(self, text, func):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(func)
        return btn

    def apply_theme(self, key):
        self.current_theme_key = key
        t = THEMES[key]
        self.dashboard_widget.setStyleSheet(f"background-color: {t['bg']};")
        self.editor_widget.setStyleSheet(f"background-color: {t['bg']};")
        
        # Global Stats Style
        self.global_stats_frame.setStyleSheet(f"""
            QFrame#stats {{ background-color: {t['sec']}; border-radius: 10px; padding: 10px; }}
            QLabel {{ color: white; font-weight: bold; font-size: 16px; }}
        """)

        # Sidebar Style
        self.sidebar.setStyleSheet(f"""
            QFrame#sidebar {{ background-color: rgba(255,255,255,0.8); border-right: 1px solid {t['sec']}; }}
            QLabel {{ color: {t['txt']}; }}
            QGroupBox {{ border: 1px solid {t['sec']}; border-radius: 5px; margin-top: 10px; font-weight: bold; color: {t['sec']}; }}
        """)

        # Buttons
        btn_style = f"QPushButton {{ background-color: {t['btn']}; color: white; border-radius: 4px; padding: 6px; }}"
        for btn in self.findChildren(QPushButton): 
            if "Về Trang Chủ" not in btn.text(): btn.setStyleSheet(btn_style)

        self.refresh_dashboard()





    def add_member_from_sidebar(self):
        # Lấy tên từ sidebar input
        name = self.inp_name.text()
        if not name: return
        
        try: cont = int(self.inp_cont.text())
        except: cont = 0
        
        self.add_member_logic(name, cont)
        
        # Reset input
        self.inp_name.clear(); self.inp_cont.setText("0")

    def add_member_dialog(self, pos=None):
        """Hộp thoại thêm thành viên (Dùng cho click chuột phải)"""
        d = QDialog()
        d.setWindowTitle("Thêm thành viên")
        l = QFormLayout(d)
        
        n_inp = QLineEdit()
        l.addRow("Tên:", n_inp)
        
        # Thêm lựa chọn Role
        c_role = QComboBox()
        c_role.addItems(["member", "owner"])
        l.addRow("Vai trò:", c_role)

        # --- SỬA LỖI TẠI ĐÂY ---
        # PyQt6 yêu cầu gọi qua StandardButton
        btns = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        bb = QDialogButtonBox(btns)
        # -----------------------

        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject) # Thêm dòng này để nút Cancel hoạt động
        l.addRow(bb)
        
        if d.exec(): 
            name = n_inp.text()
            role = c_role.currentText()
            if not name: return
            
            # Tạo node
            # Import MemberNode nếu chưa có hoặc đảm bảo nó nằm cùng file
            node = MemberNode(name, contribution=0, role=role)
            if pos: node.setPos(pos)
            else: node.setPos(random.randint(100, 500), random.randint(100, 500))
            
            self.scene.addItem(node)
            self.members_in_scene.append(node)
            self.save_current_scene()
            self.update_detail_stats()


    def add_member_logic(self, name, cont):
        """Logic thêm thành viên chung"""
        # Tự động set role nếu tên là 'Tôi'
        role = "member"
        if name in ["Tôi", "Me", "Admin"]:
            role = "owner"
            
        node = MemberNode(name, contribution=cont, role=role)
        node.setPos(random.randint(100, 500), random.randint(100, 500))
        
        self.scene.addItem(node)
        self.members_in_scene.append(node)
        self.save_current_scene()
        self.update_detail_stats()

    def remove_member(self, node):
        if node in self.members_in_scene: self.members_in_scene.remove(node)
        self.save_current_scene()
        self.update_detail_stats()



    def update_detail_stats(self):
        target = 1
        try: target = int(self.ed_target.text())
        except: pass
        if target == 0: target = 1
        
        total_cont = sum(m.contribution for m in self.members_in_scene)
        pct = min(100, int(total_cont/target*100))
        
        self.lbl_detail_stats.setText(
            f"💰 Tổng góp: {total_cont:,}k\n"
            f"🎯 Mục tiêu: {target:,}k\n"
            f"📉 Còn thiếu: {max(0, target-total_cont):,}k"
        )
        self.ed_pbar.setValue(pct)
        color = "#2ecc71" if pct >= 100 else "#f1c40f"
        self.ed_pbar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
        
        # Save mỗi khi update stat
        self.save_current_scene()

    def import_data(self):
            """Nhập dữ liệu: Convert Dict -> Object và Gộp vào DataManager"""
            path, _ = QFileDialog.getOpenFileName(self, "Import", "", "JSON (*.json)")
            if not path: return

            try:
                with open(path, encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Lấy danh sách dict từ file (chấp nhận cả cấu trúc cũ và mới)
                imported_list_dicts = data.get("goals", []) if isinstance(data, dict) else data
                
                if not imported_list_dicts:
                    QMessageBox.warning(self, "Trống", "File không có dữ liệu hợp lệ.")
                    return

                # --- HỎI NGƯỜI DÙNG: GỘP HAY GHI ĐÈ? ---
                msg = QMessageBox()
                msg.setWindowTitle("Tùy chọn nhập")
                msg.setText(f"Tìm thấy {len(imported_list_dicts)} quỹ trong file.")
                msg.setInformativeText("Bạn muốn xử lý thế nào?")
                btn_append = msg.addButton("Gộp thêm (Giữ cũ)", QMessageBox.ButtonRole.ActionRole)
                btn_replace = msg.addButton("Ghi đè (Xóa cũ)", QMessageBox.ButtonRole.ActionRole)
                btn_cancel = msg.addButton("Hủy", QMessageBox.ButtonRole.RejectRole)
                msg.exec()

                if msg.clickedButton() == btn_cancel:
                    return

                # --- XỬ LÝ LOGIC ---
                
                # 1. Nếu chọn Ghi đè -> Xóa sạch dữ liệu cũ trong Engine
                if msg.clickedButton() == btn_replace:
                    # Copy list ID ra để xóa (tránh lỗi xóa khi đang duyệt)
                    ids_to_remove = [g.id for g in self.data_mgr.goals]
                    for gid in ids_to_remove:
                        self.data_mgr.delete_goal(gid)

                # 2. DUYỆT TỪNG ITEM VÀ THÊM VÀO (QUAN TRỌNG)
                count = 0
                for item_dict in imported_list_dicts:
                    try:
                        # FIX LỖI "AttributeError": Convert Dict -> Object Goal
                        # Lọc các trường hợp lệ để tránh lỗi key lạ
                        valid_keys = Goal.__init__.__code__.co_varnames
                        clean_data = {k: v for k, v in item_dict.items() if k in valid_keys}
                        
                        new_goal_obj = Goal(**clean_data)
                        
                        # Đảm bảo load members đúng (vì dataclass init nông)
                        if "members" in item_dict:
                            new_goal_obj.members = item_dict["members"]
                            
                        # Nếu file không có ID, tạo mới. Nếu có, giữ nguyên (hoặc tạo mới để tránh trùng)
                        # Ở đây ta tạo ID mới cho an toàn khi Gộp
                        import uuid
                        new_goal_obj.id = str(uuid.uuid4())

                        # GỌI DATA MANAGER ĐỂ LƯU VÀO DATABASE CHÍNH
                        self.data_mgr.add_goal(new_goal_obj)
                        count += 1
                        
                    except Exception as e:
                        print(f"⚠️ Bỏ qua 1 mục lỗi: {e}")

                # 3. Refresh UI
                self.refresh_dashboard()
                QMessageBox.information(self, "Thành công", f"Đã nhập {count} quỹ vào hệ thống!")

            except Exception as e:
                QMessageBox.critical(self, "Lỗi Import", f"Không đọc được file: {e}")

    def export_data(self):
        self.save_current_scene() # Save active state if any
        path, _ = QFileDialog.getSaveFileName(self, "Export", "multi_fund.json", "JSON (*.json)")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({"goals": self.goals}, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "OK", "Xuất file thành công!")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", f"Không ghi được file: {e}")
    def update_detail_stats(self):
        # 1. Lấy mục tiêu
        try: target = int(self.ed_target.text())
        except: target = 1
        if target == 0: target = 1
        
        # 2. Tính tổng số dư thực tế
        total_balance = sum(m.contribution for m in self.members_in_scene)
        
        # 3. Tính %
        # Nếu tổng âm (do nợ), % là 0 (hoặc số âm tùy bạn chọn hiển thị)
        pct = int(total_balance / target * 100)
        
        # 4. Tính số tiền cần
        # Nếu đang âm 100k, target 9tr -> Cần nạp 9.1tr là đúng toán học.
        # Nhưng để hiển thị dễ hiểu:
        missing = target - total_balance
        
        status_text = ""
        if total_balance < 0:
            status_text = f"⚠️ Đang âm quỹ: {abs(total_balance):,}k"
            bar_color = "#e74c3c" # Màu đỏ báo động
        elif missing <= 0:
            status_text = f"🎉 Vượt chỉ tiêu: {abs(missing):,}k"
            bar_color = "#9b59b6" # Màu tím
            pct = 100 # Full cây
        else:
            status_text = f"📉 Còn thiếu: {missing:,}k"
            bar_color = "#f1c40f" if pct < 50 else "#2ecc71"

        # 5. Cập nhật UI
        self.lbl_detail_stats.setText(
            f"💰 Số dư hiện tại: {total_balance:,}k\n"
            f"🎯 Mục tiêu: {target:,}k\n"
            f"{status_text}"
        )
        
        self.ed_pbar.setValue(min(100, max(0, pct))) # Giới hạn bar từ 0-100 để không lỗi
        self.ed_pbar.setFormat(f"{pct}%")
        self.ed_pbar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #bdc3c7; border-radius: 5px; background: #ecf0f1; text-align: center; font-weight: bold; color: #333; }}
            QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 5px; }}
        """)
        
        self.save_current_scene()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = BudgetManager()
    window.show()
    sys.exit(app.exec())