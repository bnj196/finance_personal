import math
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *

# Import các phần phụ trợ GUI
from . import BudgetNode, StatisticsDialog
from models import Transaction, FamilyMember
from style import THEMES, SeasonalOverlay



from core.data_manager import DataManager

class TransactionDialog(QDialog):
    def __init__(self, parent=None, roles=None, transaction=None, theme_key="spring", cycle="Tháng"):
        super().__init__(parent)
        # Data
        self.roles = roles or ["Bố", "Mẹ", "Cá nhân"]
        self.cycle = cycle
        self.transaction = transaction
        
        # Style
        self.setWindowTitle("Chi Tiết Giao Dịch")
        self.resize(450, 550) # Resize to chút cho thoáng
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(15)
        
        # 1. Ngày tháng
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")

        # 2. Loại (Thu/Chi)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Thu nhập", "Chi tiêu"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)

        # 3. Danh mục (Có nút thêm nhanh)
        cat_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True) # Cho phép nhập tay tìm kiếm
        self.btn_add_cat = QPushButton("+")
        self.btn_add_cat.setFixedSize(30, 30)
        self.btn_add_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_cat.clicked.connect(self.add_new_category)
        
        cat_layout.addWidget(self.category_combo, stretch=1)
        cat_layout.addWidget(self.btn_add_cat)

        # 4. Số tiền
        self.amount_spin = QDoubleSpinBox() 
        self.amount_spin.setRange(0, 1_000_000_000)
        self.amount_spin.setSingleStep(50000)
        self.amount_spin.setSuffix(" đ") # Thêm đơn vị tiền tệ

        # 5. Thành viên (Role) - CÓ NÚT THÊM MỚI
        role_layout = QHBoxLayout()
        self.role_combo = QComboBox()
        self.role_combo.addItems(self.roles)
        
        self.btn_add_role = QPushButton("+")
        self.btn_add_role.setFixedSize(30, 30)
        self.btn_add_role.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_role.clicked.connect(self.add_new_role)
        
        role_layout.addWidget(self.role_combo, stretch=1)
        role_layout.addWidget(self.btn_add_role)

        # 6. Mô tả
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)
        self.desc_edit.setPlaceholderText("Ghi chú chi tiết...")

        # 7. Tùy chọn nâng cao (Định kỳ, Hạn)
        self.recurring_check = QCheckBox("Lặp lại định kỳ")
        self.cycle_combo = QComboBox()
        self.cycle_combo.addItems(["Tháng", "Tuần", "Năm"])
        self.cycle_combo.setEnabled(False)
        self.recurring_check.toggled.connect(self.cycle_combo.setEnabled)

        self.expiry_check = QCheckBox("Có hạn bảo hành/sử dụng")
        self.expiry_edit = QDateEdit(QDate.currentDate().addDays(30))
        self.expiry_edit.setCalendarPopup(True)
        self.expiry_edit.setEnabled(False)
        self.expiry_check.toggled.connect(self.expiry_edit.setEnabled)

        # Load Data nếu là Edit Mode
        if self.transaction: 
            self.load_data()
        else: 
            self.on_type_changed("Thu nhập")

        # Layout Add Rows
        layout.addRow("Ngày:", self.date_edit)
        layout.addRow("Loại:", self.type_combo)
        layout.addRow("Danh mục:", cat_layout)
        layout.addRow("Số tiền:", self.amount_spin)
        layout.addRow("Thành viên:", role_layout) # <--- Đã dùng layout mới
        layout.addRow("Mô tả:", self.desc_edit)
        layout.addRow("", QHBoxLayout()) # Spacer
        layout.addRow(self.recurring_check, self.cycle_combo)
        layout.addRow(self.expiry_check, self.expiry_edit)

        # Buttons OK/Cancel
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)
        
        self.setLayout(layout)

    def add_new_category(self):
        text, ok = QInputDialog.getText(self, "Thêm danh mục", "Tên danh mục mới:")
        if ok and text.strip():
            text = text.strip()
            if self.category_combo.findText(text) == -1:
                self.category_combo.addItem(text)
            self.category_combo.setCurrentText(text)

    def add_new_role(self):
        text, ok = QInputDialog.getText(self, "Thêm thành viên", "Tên thành viên mới (VD: Con trai):")
        if ok and text.strip():
            text = text.strip()
            if self.role_combo.findText(text) == -1:
                self.role_combo.addItem(text)
            self.role_combo.setCurrentText(text)

    def on_type_changed(self, text):
        self.category_combo.clear()
        items = (
            ["Lương", "Đầu tư", "Thưởng", "Kinh doanh", "Bán đồ cũ", "Khác"]
            if text == "Thu nhập"
            else ["Ăn uống", "Đi lại", "Nhà cửa", "Điện nước", "Giải trí", "Y tế", "Giáo dục", "Mua sắm", "Hiếu hỉ", "Khác"]
        )
        self.category_combo.addItems(items)

    def load_data(self):
        t = self.transaction
        self.date_edit.setDate(QDate.fromString(t.date, "yyyy-MM-dd"))
        self.type_combo.setCurrentText("Thu nhập" if t.type == "income" else "Chi tiêu")
        self.category_combo.setCurrentText(t.category)
        self.amount_spin.setValue(t.amount)
        self.role_combo.setCurrentText(t.role)
        self.desc_edit.setPlainText(t.description)
        
        self.recurring_check.setChecked(t.is_recurring)
        self.cycle_combo.setCurrentText(t.cycle if hasattr(t, 'cycle') else "Tháng")
        
        if t.expiry_date:
            self.expiry_check.setChecked(True)
            self.expiry_edit.setDate(QDate.fromString(t.expiry_date, "yyyy-MM-dd"))

    def get_data(self):
        return {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "category": self.category_combo.currentText(),
            "amount": self.amount_spin.value(),
            "type": "income" if self.type_combo.currentText() == "Thu nhập" else "expense",
            "role": self.role_combo.currentText(),
            "description": self.desc_edit.toPlainText(),
            "expiry_date": self.expiry_edit.date().toString("yyyy-MM-dd") if self.expiry_check.isChecked() else "",
            "is_recurring": self.recurring_check.isChecked(),
            "cycle": self.cycle_combo.currentText() if self.recurring_check.isChecked() else "Tháng"
        }


class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self.setMouseTracking(True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Neo zoom và kéo theo con trỏ chuột
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Chế độ kéo nền (drag canvas)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        # Bật theo dõi chuột để hover hoạt động ngay cả khi không nhấn
        self.setMouseTracking(True)

        # Tùy chỉnh thanh cuộn
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Tùy chỉnh kiểu con trỏ
        self.setCursor(Qt.CursorShape.ArrowCursor)

        # Giới hạn zoom (tùy chọn)
        self._zoom_step = 1.2
        self._min_scale = 0.2
        self._max_scale = 5.0

    def wheelEvent(self, event: QWheelEvent):
        """
        Zoom vào/vào vị trí con trỏ chuột.
        """
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Chỉ zoom khi giữ Ctrl (tùy chọn, có thể bỏ nếu muốn zoom không cần Ctrl)
            pass

        # Lấy hệ số zoom
        zoom_factor = self._zoom_step if event.angleDelta().y() > 0 else 1 / self._zoom_step

        # Lấy tỷ lệ hiện tại
        current_scale = self.transform().m11()  # m11 = scale X

        # Kiểm tra giới hạn zoom
        if current_scale * zoom_factor < self._min_scale:
            zoom_factor = self._min_scale / current_scale
        elif current_scale * zoom_factor > self._max_scale:
            zoom_factor = self._max_scale / current_scale

        # Áp dụng zoom
        self.scale(zoom_factor, zoom_factor)

        # Chấp nhận sự kiện
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """
        Xử lý nhấn chuột: cho phép kéo canvas bằng nút phải hoặc giữa.
        """
        if event.button() == Qt.MouseButton.RightButton:
            # Bắt đầu kéo canvas (ScrollHandDrag chỉ hoạt động với nút giữa mặc định)
            # Nên ta giả lập bằng cách chuyển chế độ tạm thời
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            fake_event = QMouseEvent(
                QEvent.Type.MouseButtonPress,
                event.position(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            super().mousePressEvent(fake_event)
            return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Khôi phục chế độ sau khi thả chuột phải.
        """
        if event.button() == Qt.MouseButton.RightButton:
            fake_event = QMouseEvent(
                QEvent.Type.MouseButtonRelease,
                event.position(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            super().mouseReleaseEvent(fake_event)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)  # hoặc ScrollHandDrag nếu bạn muốn giữ
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """
        (Tùy chọn) Hỗ trợ phím tắt: Ctrl + 0 để reset zoom.
        """
        if event.key() == Qt.Key.Key_0 and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.resetTransform()
            self.centerOn(self.scene().sceneRect().center())
        else:
            super().keyPressEvent(event)

class TransactionMgr(QMainWindow):
    def __init__(self, parent=None, theme_key="spring"):
        super().__init__(parent)
        self.setWindowTitle("Quản Lý Thu Chi")
        self.resize(1200, 750)
        self.current_theme_key = theme_key
        
        # --- KẾT NỐI DATA MANAGER (SINGLETON) ---
        self.data_manager = DataManager.instance()
        # Lắng nghe sự thay đổi dữ liệu để tự refresh
        self.data_manager.data_changed.connect(self.refresh_all)

        self.init_ui()

        # Overlay Effect
        self.overlay = SeasonalOverlay(self.centralWidget())
        self.overlay.show()
        self.overlay.raise_()
        self.apply_theme(self.current_theme_key)
        
        # Load dữ liệu lần đầu
        self.refresh_all()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # === LEFT PANEL (Data) ===
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.btn_add = self.create_btn("➕ Thêm", self.add_transaction)
        self.btn_edit = self.create_btn("✏️ Sửa", self.edit_transaction)
        self.btn_del = self.create_btn("🗑️ Xóa", self.delete_transaction)
        self.btn_stats = self.create_btn("📊 Thống kê", self.show_stats)
        
        self.btn_import = self.create_btn("📥 Import", self.import_csv)
        self.btn_export = self.create_btn("📤 Export", self.export_csv)

        toolbar_layout.addWidget(self.btn_add)
        toolbar_layout.addWidget(self.btn_edit)
        toolbar_layout.addWidget(self.btn_del)
        toolbar_layout.addWidget(self.btn_stats)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.btn_import)
        toolbar_layout.addWidget(self.btn_export)
        left_layout.addLayout(toolbar_layout)

        # Filter Bar
        filter_bar = QHBoxLayout()
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("Tìm kiếm...")
        self.keyword_edit.textChanged.connect(self.apply_filter)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["Tất cả", "Thu nhập", "Chi tiêu"])
        self.type_filter.currentTextChanged.connect(self.apply_filter)

        self.from_date = QDateEdit(QDate.currentDate().addMonths(-1)) # Mặc định xem 1 tháng
        self.from_date.setCalendarPopup(True)
        self.from_date.dateChanged.connect(self.apply_filter)

        self.to_date = QDateEdit(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.dateChanged.connect(self.apply_filter)

        filter_bar.addWidget(QLabel("🔍"))
        filter_bar.addWidget(self.keyword_edit, 1)
        filter_bar.addWidget(self.type_filter)
        filter_bar.addWidget(QLabel("Từ:"))
        filter_bar.addWidget(self.from_date)
        filter_bar.addWidget(QLabel("Đến:"))
        filter_bar.addWidget(self.to_date)
        left_layout.addLayout(filter_bar)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Ngày", "Loại", "Danh mục", "Số tiền", "Thành viên", "Mô tả", "Định kỳ"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.table)

        # Summary Bar
        summary_frame = QFrame()
        summary_frame.setObjectName("summary")
        summary_frame.setStyleSheet("background-color: rgba(255,255,255,0.5); border-radius: 10px; padding: 5px;")
        sum_layout = QHBoxLayout(summary_frame)
        self.income_label = QLabel("Thu: 0")
        self.expense_label = QLabel("Chi: 0")
        self.balance_label = QLabel("Dư: 0")
        sum_layout.addWidget(self.income_label)
        sum_layout.addWidget(self.expense_label)
        sum_layout.addWidget(self.balance_label)
        left_layout.addWidget(summary_frame)

        # === RIGHT PANEL (Visual Graph) ===
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        
        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setStyleSheet("background: transparent; border: none;")
        right_layout.addWidget(self.view)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([700, 500])
        main_layout.addWidget(splitter)

    # ==========================
    # CÁC HÀM LOGIC (DATA MANAGER INTEGRATION)
    # ==========================
    
    def refresh_all(self):
        # Lấy dữ liệu mới nhất từ Singleton (Proxy Property)
        transactions = self.data_manager.transactions 
        self.update_table(transactions)
        self.update_summary(transactions)
        self.update_graph(transactions)

    def update_summary(self, transactions):
        inc = sum(t.amount for t in transactions if t.type == "income")
        exp = sum(t.amount for t in transactions if t.type == "expense")
        self.income_label.setText(f"Thu: {inc:,.0f} đ")
        self.income_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 14px;")
        
        self.expense_label.setText(f"Chi: {exp:,.0f} đ")
        self.expense_label.setStyleSheet("color: #c0392b; font-weight: bold; font-size: 14px;")
        
        self.balance_label.setText(f"Dư: {inc - exp:,.0f} đ")
        self.balance_label.setStyleSheet("color: #2980b9; font-weight: bold; font-size: 16px;")

    # --- ADD ---
    def add_transaction(self):
        # Lấy danh sách roles hiện có để gợi ý
        current_data = self.data_manager.transactions
        roles = sorted(set(t.role for t in current_data)) or ["Bố", "Mẹ", "Cá nhân"]

        dlg = TransactionDialog(self, roles, theme_key=self.current_theme_key)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            # Tạo ID mới (dựa trên timestamp hoặc random để tránh trùng)
            import time
            new_id = str(int(time.time() * 1000)) 
            
            new_t = Transaction(id=new_id, **data)
            
            # GỌI DATA MANAGER
            self.data_manager.add_transaction(new_t)

    # --- EDIT ---
    def edit_transaction(self):
        row = self.table.currentRow()
        if row < 0: return
        tid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Tìm transaction trong list của Manager
        trans = next((t for t in self.data_manager.transactions if t.id == tid), None)
        
        if trans:
            roles = sorted(set(t.role for t in self.data_manager.transactions))
            dlg = TransactionDialog(self, roles, trans, theme_key=self.current_theme_key)
            if dlg.exec():
                new_data = dlg.get_data()
                # Cập nhật object hiện tại
                for k, v in new_data.items(): setattr(trans, k, v)
                
                # GỌI DATA MANAGER CẬP NHẬT
                self.data_manager.update_transaction(trans)

    # --- DELETE ---
    def delete_transaction(self):
        row = self.table.currentRow()
        if row < 0: return
        tid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        confirm = QMessageBox.question(self, "Xóa", "Bạn có chắc muốn xóa giao dịch này?")
        if confirm == QMessageBox.StandardButton.Yes:
            self.data_manager.delete_transaction(tid)

    # --- IMPORT / EXPORT (Giờ gọi qua Engine ẩn trong Manager) ---
    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                # Gọi Engine thông qua Manager
                count = self.data_manager.trans_engine.import_csv(path) 
                self.data_manager.notify_change() # Báo UI cập nhật
                QMessageBox.information(self, "Import", f"Đã import {count} dòng.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu file CSV", "", "CSV Files (*.csv)")
        if path:
            self.data_manager.trans_engine.export_csv(path)
            QMessageBox.information(self, "Export", "Xuất file thành công!")

    # --- HELPER GUI METHODS ---
    def create_btn(self, text, func):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(func)
        btn.setFixedHeight(35)
        return btn

    def apply_filter(self):
        keyword = self.keyword_edit.text().lower()
        type_text = self.type_filter.currentText()
        from_dt = self.from_date.date().toString("yyyy-MM-dd")
        to_dt = self.to_date.date().toString("yyyy-MM-dd")

        all_trans = self.data_manager.transactions
        filtered = [
            t for t in all_trans
            if (keyword in t.role.lower() or keyword in t.category.lower() or keyword in t.description.lower())
            and (type_text == "Tất cả" or (type_text == "Thu nhập" and t.type == "income") or (type_text == "Chi tiêu" and t.type == "expense"))
            and from_dt <= t.date <= to_dt
        ]
        self.update_table(filtered)
        self.update_graph(filtered)

    def update_table(self, data):
        self.table.setRowCount(len(data))
        for row, t in enumerate(data):
            date_item = QTableWidgetItem(t.date)
            date_item.setData(Qt.ItemDataRole.UserRole, t.id)
            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, QTableWidgetItem("Thu" if t.type == "income" else "Chi"))
            self.table.setItem(row, 2, QTableWidgetItem(t.category))

            amt_item = QTableWidgetItem(f"{t.amount:,.0f}")
            amt_color = QColor("#27ae60") if t.type == "income" else QColor("#c0392b")
            amt_item.setForeground(QBrush(amt_color))
            amt_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row, 3, amt_item)
            self.table.setItem(row, 4, QTableWidgetItem(t.role))
            self.table.setItem(row, 5, QTableWidgetItem(t.description))

            ck = QCheckBox()
            ck.setChecked(t.is_recurring)
            ck.setEnabled(False) # Chỉ hiển thị
            ck.setStyleSheet("margin-left:50%;")
            self.table.setCellWidget(row, 6, ck)

    def show_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("➕ Thêm", self.add_transaction)
        menu.addAction("✏️ Sửa", self.edit_transaction)
        menu.addAction("🗑️ Xóa", self.delete_transaction)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def show_stats(self):
        # Mở dialog thống kê (Code dialog này giả sử bạn đã có)
        dlg = StatisticsDialog(self, self.data_manager.transactions)
        dlg.exec()
    
    def update_graph(self, transactions):
        self.scene.clear()
        
        roles = sorted(set(t.role for t in transactions))
        if not roles:
            return

        # Tạo members
        colors = [QColor("#E74C3C"), QColor("#8E44AD"), QColor("#3498DB"), QColor("#16A085"), QColor("#F39C12")]
        members = [
            FamilyMember(r, colors[i % len(colors)]) for i, r in enumerate(roles)
        ]
        
        # ✅ TÍNH TOÁN TỔNG TIỀN CHO TỪNG MEMBER TRƯỚC
        for m in members:
            m.total_income = sum(t.amount for t in transactions if t.role == m.name and t.type == "income")
            m.total_expense = sum(t.amount for t in transactions if t.role == m.name and t.type == "expense")

        # ✅ SAU ĐÓ MỚI TẠO NODE
        cx, cy = 250, 250
        radius = 150
        n = len(members)
        for i, m in enumerate(members):
            angle = 2 * math.pi * i / n - math.pi / 2
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            node = BudgetNode(m, x, y)  # ← Giờ m đã có dữ liệu đầy đủ
            self.scene.addItem(node)

    def apply_theme(self, theme_key):
        self.current_theme_key = theme_key
        t = THEMES[theme_key]
        
        # 1. Update Overlay
        self.overlay.set_season(theme_key)
        if not self.overlay.initialized: self.overlay.init_particles()

        # 2. Main Window Background
        self.centralWidget().setStyleSheet(f"background-color: {t['bg_primary']};")

        # 3. Panels
        panel_style = f"""
            QFrame#panel {{
                background-color: rgba(255, 255, 255, 0.6); 
                border: 1px solid {t['accent']};
                border-radius: 15px;
            }}
        """
        self.findChild(QFrame, "panel").setStyleSheet(panel_style)

        # 4. Buttons
        btn_style = f"""
            QPushButton {{
                background-color: {t['bg_secondary']};
                color: {t['text_light']};
                border-radius: 8px;
                padding: 5px 15px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: {t['btn_hover']}; }}
        """
        for btn in [self.btn_add, self.btn_edit, self.btn_del, self.btn_stats]:
            btn.setStyleSheet(btn_style)

        # 5. Table Styling (The hard part)
        table_style = f"""
            QTableWidget {{
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid {t['accent']};
                border-radius: 10px;
                gridline-color: transparent;
                color: {t['text_main']};
            }}
            QHeaderView::section {{
                background-color: {t['bg_secondary']};
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item {{ padding: 5px; }}
            QTableWidget::item:selected {{
                background-color: {t['accent']};
                color: {t['text_main']};
            }}
        """
        self.table.setStyleSheet(table_style)
        self.table.horizontalHeader().setStyleSheet(table_style)

        # 6. Summary Labels
        self.income_label.setStyleSheet(f"color: #27ae60; font-weight: bold; font-size: 14px;")
        self.expense_label.setStyleSheet(f"color: #c0392b; font-weight: bold; font-size: 14px;")
        self.balance_label.setStyleSheet(f"color: {t['bg_secondary']}; font-weight: bold; font-size: 16px;")

        # Redraw Graphics to match theme
        self.update_graph(self.data_manager.transactions)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.centralWidget().rect())
        if not self.overlay.initialized: 
            self.overlay.init_particles()