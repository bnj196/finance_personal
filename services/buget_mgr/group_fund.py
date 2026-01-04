import sys
import json
import csv
import random
import math
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

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

# ======================
# 2. CUSTOM WIDGET: GOAL CARD (THẺ QUỸ)
# ======================
class GoalCard(QFrame):
    clicked = pyqtSignal(int) # Signal gửi ID của goal khi click

    def __init__(self, index, goal_data, theme):
        super().__init__()
        self.index = index
        self.goal = goal_data
        self.theme = theme
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(280, 160)
        
        # Style
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid {theme['acc']};
                border-radius: 15px;
            }}
            QFrame:hover {{
                background-color: white;
                border: 2px solid {theme['sec']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header: Icon + Name
        header = QHBoxLayout()
        icon = QLabel("💰")
        icon.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        lbl_name = QLabel(self.goal["name"])
        lbl_name.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme['txt']}; border: none; background: transparent;")
        header.addWidget(icon)
        header.addWidget(lbl_name)
        header.addStretch()
        layout.addLayout(header)
        
        # Stats
        target = self.goal.get("target", 1) or 1
        current = sum(m["contribution"] for m in self.goal.get("members", []))
        pct = min(100, int(current / target * 100))
        
        lbl_money = QLabel(f"{current:,}k / {target:,}k")
        lbl_money.setStyleSheet(f"color: {theme['sec']}; font-weight: bold; border: none; background: transparent;")
        lbl_money.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(lbl_money)
        
        # Progress Bar
        pbar = QProgressBar()
        pbar.setValue(pct)
        pbar.setFixedHeight(10)
        pbar.setTextVisible(False)
        pbar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #bdc3c7; border-radius: 5px; background: #ecf0f1; }}
            QProgressBar::chunk {{ background-color: {theme['sec']}; border-radius: 5px; }}
        """)
        layout.addWidget(pbar)
        
        # Footer: Member count
        mem_count = len(self.goal.get("members", []))
        lbl_mem = QLabel(f"👥 {mem_count} thành viên")
        lbl_mem.setStyleSheet("color: gray; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(lbl_mem)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)

# ======================
# 3. GRAPHICS ITEMS (Card Thành Viên)
# ======================
class MemberNode(QGraphicsItem):
    def __init__(self, name, income=0, expense=0, contribution=0):
        super().__init__()
        self.name = name; self.income = income; self.expense = expense; self.contribution = contribution
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
    def boundingRect(self): return QRectF(-70, -50, 140, 100)
    
    def paint(self, painter, option, widget):
        # Shadow
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawRoundedRect(self.boundingRect().translated(4, 4), 10, 10)
        # Card Body
        painter.setBrush(QColor("white")); painter.setPen(QPen(QColor("#FFD700"), 3) if self.isSelected() else QPen(QColor("#bdc3c7"), 1))
        painter.drawRoundedRect(self.boundingRect(), 10, 10)
        # Header
        painter.setBrush(QColor("#ecf0f1")); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(-70, -50, 140, 30), 10, 10); painter.drawRect(QRectF(-70, -30, 140, 10))
        # Text
        painter.setPen(QColor("#2c3e50")); painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(-70, -50, 140, 30), Qt.AlignmentFlag.AlignCenter, self.name)
        # Stats
        painter.setFont(QFont("Arial", 9))
        painter.drawText(QRectF(-65, -10, 130, 50), Qt.AlignmentFlag.AlignCenter, f"Thu: {self.income}k\nChi: {self.expense}k\nGóp: {self.contribution}k")

    def contextMenuEvent(self, event):
        menu = QMenu(); menu.setStyleSheet("QMenu { background: white; border: 1px solid gray; }")
        menu.addAction("✏️ Sửa", self.edit_info)
        menu.addAction("🗑️ Xóa", self.delete_node)
        menu.exec(event.screenPos())

    def edit_info(self):
        d = QDialog(); d.setWindowTitle("Sửa"); l = QFormLayout(d)
        n = QLineEdit(self.name); i = QLineEdit(str(self.income)); e = QLineEdit(str(self.expense)); c = QLineEdit(str(self.contribution))
        l.addRow("Tên:", n); l.addRow("Thu:", i); l.addRow("Chi:", e); l.addRow("Góp:", c)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(lambda: self._save(d, n, i, e, c)); bb.rejected.connect(d.reject); l.addRow(bb)
        d.exec()

    def _save(self, d, n, i, e, c):
        self.name = n.text(); self.income = int(i.text()); self.expense = int(e.text()); self.contribution = int(c.text())
        self.update(); self.scene().views()[0].main_window.update_detail_stats(); d.accept()

    def delete_node(self):
        self.scene().views()[0].main_window.remove_member(self); self.scene().removeItem(self)

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
        
        # Data
        self.goals = [] 
        self.current_goal_index = -1
        self.members_in_scene = [] 
        self.current_theme_key = "spring"

        # --- MAIN LAYOUT ---
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # 1. Dashboard View (Index 0)
        self.dashboard_widget = QWidget()
        self.setup_dashboard()
        self.stack.addWidget(self.dashboard_widget)

        # 2. Editor View (Index 1)
        self.editor_widget = QWidget()
        self.setup_editor()
        self.stack.addWidget(self.editor_widget)

        # Load Default Data
        if not self.goals:
            self.goals.append({"name": "Quỹ Du Lịch", "target": 20000, "members": []})
            self.goals.append({"name": "Quỹ Ăn Uống", "target": 5000, "members": []})
        
        self.apply_theme("spring")
        self.refresh_dashboard()

    # ==========================
    # DASHBOARD SETUP (ĐÃ SỬA LỖI QFLOWLAYOUT)
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
        
        # --- FIX: DÙNG GRID LAYOUT THAY VÌ QFLOWLAYOUT ---
        self.grid_layout = QGridLayout(self.cards_container)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

    def refresh_dashboard(self):
        # Clear old cards
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        # Add Cards
        t = THEMES[self.current_theme_key]
        total_money = 0
        
        row, col = 0, 0
        max_cols = 3 # Số cột tối đa trên 1 hàng

        for idx, goal in enumerate(self.goals):
            card = GoalCard(idx, goal, t)
            card.clicked.connect(self.open_editor)
            
            # Context Menu cho Card (để xóa)
            card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            card.customContextMenuRequested.connect(lambda pos, i=idx: self.card_context_menu(pos, i))
            
            self.grid_layout.addWidget(card, row, col)
            
            # Logic tính toán Grid (Giả lập Flow)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
            
            current_fund = sum(m["contribution"] for m in goal.get("members", []))
            total_money += current_fund

        # Update Stats
        self.lbl_total_funds.setText(f"Số lượng quỹ: {len(self.goals)}")
        self.lbl_total_money.setText(f"Tổng tài sản: {total_money:,}k")

    def card_context_menu(self, pos, index):
        menu = QMenu()
        delete = menu.addAction("🗑️ Xóa Quỹ Này")
        action = menu.exec(QCursor.pos())
        if action == delete:
            confirm = QMessageBox.question(self, "Xóa", f"Xóa quỹ '{self.goals[index]['name']}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                del self.goals[index]
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

        # Add Member
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
        self.view = EditorGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)

    def open_editor(self, index):
        self.current_goal_index = index
        goal = self.goals[index]
        
        # Load Data to UI
        self.ed_name.setText(goal["name"])
        self.ed_target.setText(str(goal["target"]))
        
        # Load Scene
        self.scene.clear()
        self.members_in_scene = []
        for m in goal.get("members", []):
            node = MemberNode(m["name"], m["income"], m["expense"], m["contribution"])
            # Set pos or random
            node.setPos(m.get("x", random.randint(100, 600)), m.get("y", random.randint(100, 500)))
            self.scene.addItem(node)
            self.members_in_scene.append(node)
        
        self.update_detail_stats()
        self.stack.setCurrentIndex(1) # Switch to Editor

    def back_to_dashboard(self):
        self.save_current_scene() # Save positions
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

    def add_new_goal(self):
        name, ok = QInputDialog.getText(self, "Tạo Quỹ", "Tên quỹ mới:")
        if ok and name:
            self.goals.append({"name": name, "target": 10000, "members": []})
            self.refresh_dashboard()

    def save_current_meta(self):
        if self.current_goal_index == -1: return
        self.goals[self.current_goal_index]["name"] = self.ed_name.text()
        try: self.goals[self.current_goal_index]["target"] = int(self.ed_target.text())
        except: pass
        self.update_detail_stats()
        QMessageBox.information(self, "OK", "Đã cập nhật thông tin quỹ!")

    def add_member_from_sidebar(self):
        self.add_member_dialog()

    def add_member_dialog(self, pos=None):
        name = self.inp_name.text() if not pos else "Thành viên mới"
        
        # Nếu click chuột phải add nhanh
        if pos:
            d = QDialog(); d.setWindowTitle("Thêm"); l = QFormLayout(d)
            n_inp = QLineEdit()
            l.addRow("Tên:", n_inp)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); l.addRow(bb)
            if d.exec(): name = n_inp.text()
            else: return

        if not name: return
        try: cont = int(self.inp_cont.text())
        except: cont = 0

        node = MemberNode(name, contribution=cont)
        if pos: node.setPos(pos)
        else: node.setPos(random.randint(100, 500), random.randint(100, 500))
        
        self.scene.addItem(node)
        self.members_in_scene.append(node)
        self.save_current_scene()
        self.update_detail_stats()
        self.inp_name.clear(); self.inp_cont.setText("0")

    def remove_member(self, node):
        if node in self.members_in_scene: self.members_in_scene.remove(node)
        self.save_current_scene()
        self.update_detail_stats()

    def save_current_scene(self):
        if self.current_goal_index == -1: return
        m_data = []
        for m in self.members_in_scene:
            m_data.append({
                "name": m.name, "income": m.income, "expense": m.expense, "contribution": m.contribution,
                "x": m.x(), "y": m.y()
            })
        self.goals[self.current_goal_index]["members"] = m_data

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
        self.save_current_scene()

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "JSON (*.json)")
        if path:
            with open(path, encoding='utf-8') as f:
                self.goals = json.load(f).get("goals", [])
                self.refresh_dashboard()

    def export_data(self):
        self.save_current_scene() # Save active state if any
        path, _ = QFileDialog.getSaveFileName(self, "Export", "multi_fund.json", "JSON (*.json)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"goals": self.goals}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = BudgetManager()
    window.show()
    sys.exit(app.exec())