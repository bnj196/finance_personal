import math
import csv
import random

from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *

from . import BudgetNode, StatisticsDialog
from models import Transaction,FamilyMember
from style import  THEMES, SeasonalOverlay, Particle



import pathlib, shutil, os
DATA_FILE = pathlib.Path(__file__).parent / "transactions.csv"
BACKUP_FOLDER = pathlib.Path(__file__).parent / "backups"

class TransactionDialog(QDialog):

    def __init__(qtl, parent=None, roles=None, transaction=None, theme_key="spring",cycle="Tháng"):
        super().__init__(parent)
        #data
        qtl.roles = roles or ["Bố", "Mẹ", "Cá nhân"]
        qtl.cycle = cycle
        qtl.transaction = transaction

        #style
        # qtl.theme = THEMES[theme_key]
        qtl.setWindowTitle("Chi Tiết Giao Dịch")
        qtl.resize(400, 500)
        qtl.init_ui()


    def init_ui(qtl):
        layout = QFormLayout()
        layout.setSpacing(15)
        
        qtl.date_edit = QDateEdit(QDate.currentDate())
        qtl.date_edit.setCalendarPopup(True)
        qtl.date_edit.setDisplayFormat("dd/MM/yyyy")

        qtl.type_combo = QComboBox()
        qtl.type_combo.addItems(["Thu nhập", "Chi tiêu"])
        qtl.type_combo.currentTextChanged.connect(qtl.on_type_changed)

        qtl.category_combo = QComboBox()
        qtl.amount_spin = QDoubleSpinBox() 
        qtl.amount_spin.setRange(0, 1_000_000_000)
        qtl.amount_spin.setSingleStep(10000)
        
        qtl.role_combo = QComboBox()
        qtl.role_combo.setEditable(True)
        print("roles:",qtl.roles)
        qtl.role_combo.addItems(qtl.roles)

        qtl.desc_edit = QTextEdit()
        qtl.desc_edit.setMaximumHeight(60)

        qtl.recurring_check = QCheckBox("Lặp lại định kỳ")
        qtl.expiry_check = QCheckBox("Có hạn sử dụng")
        qtl.expiry_edit = QDateEdit(QDate.currentDate().addDays(30))
        qtl.expiry_edit.setCalendarPopup(True)
        qtl.expiry_edit.setEnabled(False)
        qtl.expiry_check.toggled.connect(qtl.expiry_edit.setEnabled)


        cat_layout = QHBoxLayout()
        qtl.category_combo = QComboBox()
        cat_layout.addWidget(qtl.category_combo, stretch=1)
        qtl.btn_add_cat = QPushButton("+")
        qtl.btn_add_cat.setFixedSize(30, 30)
        qtl.btn_add_cat.clicked.connect(qtl.add_new_category)
        cat_layout.addWidget(qtl.btn_add_cat)
        
        # combo chù kì theo tháng hoặc tuần
        qtl.cycle_combo = QComboBox()
        qtl.cycle_combo.addItems(["Tháng", "Tuần"])
        qtl.cycle_combo.setEnabled(False)
        qtl.recurring_check.toggled.connect(qtl.cycle_combo.setEnabled)

        if qtl.transaction: qtl.load_data()
        else: qtl.on_type_changed("Thu nhập")

        layout.addRow("Ngày:", qtl.date_edit)
        layout.addRow("Loại:", qtl.type_combo)
        layout.addRow("Danh mục:", cat_layout)
        layout.addRow("Số tiền (VNĐ):", qtl.amount_spin)
        layout.addRow("Thành viên:", qtl.role_combo)
        layout.addRow("Mô tả:", qtl.desc_edit)
        layout.addRow("", qtl.recurring_check)
        layout.addRow("", qtl.expiry_check)
        layout.addRow("Hết hạn:", qtl.expiry_edit)
        layout.addRow("Chu kỳ:", qtl.cycle_combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(qtl.accept)
        btn_box.rejected.connect(qtl.reject)
        layout.addRow(btn_box)
        qtl.setLayout(layout)

    def add_new_category(qtl):
        text, ok = QInputDialog.getText(qtl, "Thêm danh mục", "Tên danh mục mới:")
        if ok and text.strip():
            text = text.strip()
            if qtl.category_combo.findText(text) == -1:
                qtl.category_combo.addItem(text)
            qtl.category_combo.setCurrentText(text)


    def load_data(qtl):
        t = qtl.transaction
        qtl.date_edit.setDate(QDate.fromString(t.date, "yyyy-MM-dd"))
        qtl.type_combo.setCurrentText("Thu nhập" if t.type == "income" else "Chi tiêu")
        qtl.category_combo.setCurrentText(t.category)
        qtl.amount_spin.setValue(t.amount)
        qtl.role_combo.setCurrentText(t.role)
        qtl.desc_edit.setPlainText(t.description)
        qtl.recurring_check.setChecked(t.is_recurring)
        if t.expiry_date:
            qtl.expiry_check.setChecked(True)
            qtl.expiry_edit.setDate(QDate.fromString(t.expiry_date, "yyyy-MM-dd"))

    def get_data(qtl):
        return {
            "date": qtl.date_edit.date().toString("yyyy-MM-dd"),
            "category": qtl.category_combo.currentText(),
            "amount": qtl.amount_spin.value(),
            "type": "income" if qtl.type_combo.currentText() == "Thu nhập" else "expense",
            "role": qtl.role_combo.currentText(),
            "description": qtl.desc_edit.toPlainText(),
            "expiry_date": qtl.expiry_edit.date().toString("yyyy-MM-dd") if qtl.expiry_check.isChecked() else "",
            "is_recurring": qtl.recurring_check.isChecked()
        }


    def on_type_changed(qtl, text):
        qtl.category_combo.clear()
        items = (
            ["Lương", "Đầu tư", "Thưởng", "Kinh doanh", "Khác"]
            if text == "Thu nhập"
            else ["Ăn uống", "Đi lại", "Nhà cửa", "Giải trí", "Y tế", "Giáo dục", "Mua sắm", "Khác"]
        )
        qtl.category_combo.addItems(items)



class TransactionMgr(QMainWindow):
    def __init__(qtl, parent=None, theme_key="spring"):
        super().__init__(parent)
        qtl.setWindowTitle("Quản Lý Thu Chi ")
        qtl.resize(1200, 750)
        qtl.current_theme_key = theme_key # theme services
        qtl.transactions = []

        qtl.members = []
        qtl.budget_nodes = []

        qtl.init_ui()

        qtl.overlay = SeasonalOverlay(qtl.centralWidget())
        qtl.overlay.show()
        qtl.overlay.raise_()
        qtl.apply_theme(qtl.current_theme_key)

    def init_ui(qtl):
        qtl.setWindowTitle("Quản Lý Thu Chi - Module Độc Lập")
        qtl.resize(1200, 750)

        central = QWidget()
        qtl.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # === LEFT PANEL (Data) ===
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Custom Toolbar (Buttons Layout)
        toolbar_layout = QHBoxLayout()
        qtl.btn_add = qtl.create_btn("➕ Thêm", qtl.add_transaction)
        qtl.btn_edit = qtl.create_btn("✏️ Sửa", qtl.edit_transaction)
        qtl.btn_del = qtl.create_btn("🗑️ Xóa", qtl.delete_transaction)
        qtl.btn_stats = qtl.create_btn("📊 Thống kê", qtl.show_stats)

        qtl.btn_import = qtl.create_btn("📥 Import CSV", qtl.import_csv)
        toolbar_layout.addWidget(qtl.btn_import)
        qtl.btn_export = qtl.create_btn("📤 Export CSV", qtl.export_csv)
        toolbar_layout.addWidget(qtl.btn_export)

        # === FILTER BAR ===
        filter_bar = QHBoxLayout()
        qtl.keyword_edit = QLineEdit()
        qtl.keyword_edit.setPlaceholderText("Tìm theo tên, danh mục, mô tả...")
        qtl.keyword_edit.textChanged.connect(qtl.apply_filter)

        qtl.type_filter = QComboBox()
        qtl.type_filter.addItems(["Tất cả", "Thu nhập", "Chi tiêu"])
        qtl.type_filter.currentTextChanged.connect(qtl.apply_filter)

        qtl.from_date = QDateEdit()
        qtl.from_date.setCalendarPopup(True)
        qtl.from_date.setDate(QDate(2025, 1, 1))
        qtl.from_date.dateChanged.connect(qtl.apply_filter)

        qtl.to_date = QDateEdit()
        qtl.to_date.setCalendarPopup(True)
        qtl.to_date.setDate(QDate.currentDate())
        qtl.to_date.dateChanged.connect(qtl.apply_filter)

        filter_bar.addWidget(QLabel("Tìm:"))
        filter_bar.addWidget(qtl.keyword_edit)
        filter_bar.addWidget(QLabel("Loại:"))
        filter_bar.addWidget(qtl.type_filter)
        filter_bar.addWidget(QLabel("Từ:"))
        filter_bar.addWidget(qtl.from_date)
        filter_bar.addWidget(QLabel("Đến:"))
        filter_bar.addWidget(qtl.to_date)
        left_layout.addLayout(filter_bar)

        # Theme Switcher (Để test)
        qtl.combo_theme = QComboBox()
        qtl.combo_theme.addItems(["spring", "summer", "autumn", "winter"])
        qtl.combo_theme.currentTextChanged.connect(qtl.apply_theme)
        qtl.combo_theme.setFixedWidth(100)

        toolbar_layout.addWidget(qtl.btn_add)
        toolbar_layout.addWidget(qtl.btn_edit)
        toolbar_layout.addWidget(qtl.btn_del)
        toolbar_layout.addWidget(qtl.btn_stats)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(QLabel("Theme:"))
        toolbar_layout.addWidget(qtl.combo_theme)
        left_layout.addLayout(toolbar_layout)

        # Table
        qtl.table = QTableWidget(0, 7)
        qtl.table.setHorizontalHeaderLabels(["Ngày", "Loại", "Danh mục", "Số tiền", "Thành viên", "Mô tả", "Định kỳ"])
        qtl.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        qtl.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        qtl.table.setAlternatingRowColors(True)
        qtl.table.setShowGrid(False) # Modern look
        left_layout.addWidget(qtl.table)

        # Summary Bar
        summary_frame = QFrame()
        summary_frame.setObjectName("summary")
        summary_frame.setStyleSheet("background-color: rgba(255,255,255,0.5); border-radius: 10px; padding: 5px;")
        sum_layout = QHBoxLayout(summary_frame)
        qtl.income_label = QLabel("Thu: 0")
        qtl.expense_label = QLabel("Chi: 0")
        qtl.balance_label = QLabel("Dư: 0")
        sum_layout.addWidget(qtl.income_label)
        sum_layout.addWidget(qtl.expense_label)
        sum_layout.addWidget(qtl.balance_label)
        left_layout.addWidget(summary_frame)

        # === RIGHT PANEL (Visual) ===
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        
        qtl.scene = QGraphicsScene()
        qtl.view = QGraphicsView(qtl.scene)
        qtl.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        qtl.view.setStyleSheet("background: transparent; border: none;") # Transparent for theme bg
        right_layout.addWidget(qtl.view)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([700, 500])
        main_layout.addWidget(splitter)

        # Thêm context menu cho table
        qtl.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        qtl.table.customContextMenuRequested.connect(qtl.show_context_menu)


    def create_btn(qtl, text, func):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(func)
        btn.setFixedHeight(35)
        return btn

    def refresh_all(qtl):
        qtl.update_table()
        qtl.update_summary()
        qtl.update_graph()

    def update_summary(qtl): # update - thu chi dư
        inc = sum(t.amount for t in qtl.transactions if t.type == "income")
        exp = sum(t.amount for t in qtl.transactions if t.type == "expense")
        qtl.income_label.setText(f"Thu: {inc:,.0f} đ")
        qtl.expense_label.setText(f"Chi: {exp:,.0f} đ")
        qtl.balance_label.setText(f"Dư: {inc - exp:,.0f} đ")

    def resizeEvent(qtl, event):
        super().resizeEvent(event)
        qtl.overlay.setGeometry(qtl.centralWidget().rect())
        if not qtl.overlay.initialized: qtl.overlay.init_particles()


    def apply_theme(qtl, theme_key):
        qtl.current_theme_key = theme_key
        t = THEMES[theme_key]
        
        # 1. Update Overlay
        qtl.overlay.set_season(theme_key)
        if not qtl.overlay.initialized: qtl.overlay.init_particles()

        # 2. Main Window Background
        qtl.centralWidget().setStyleSheet(f"background-color: {t['bg_primary']};")

        # 3. Panels
        panel_style = f"""
            QFrame#panel {{
                background-color: rgba(255, 255, 255, 0.6); 
                border: 1px solid {t['accent']};
                border-radius: 15px;
            }}
        """
        qtl.findChild(QFrame, "panel").setStyleSheet(panel_style)

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
        for btn in [qtl.btn_add, qtl.btn_edit, qtl.btn_del, qtl.btn_stats]:
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
        qtl.table.setStyleSheet(table_style)
        qtl.table.horizontalHeader().setStyleSheet(table_style)

        # 6. Summary Labels
        qtl.income_label.setStyleSheet(f"color: #27ae60; font-weight: bold; font-size: 14px;")
        qtl.expense_label.setStyleSheet(f"color: #c0392b; font-weight: bold; font-size: 14px;")
        qtl.balance_label.setStyleSheet(f"color: {t['bg_secondary']}; font-weight: bold; font-size: 16px;")

        # Redraw Graphics to match theme
        qtl.update_graph()



    def update_graph(qtl):
        qtl.scene.clear()
        qtl.budget_nodes.clear()
        
        # Build data
        roles = sorted(set(t.role for t in qtl.transactions))
        # Màu sắc động cho các thành viên
        colors = [
            QColor("#E74C3C"), QColor("#8E44AD"), QColor("#3498DB"), 
            QColor("#16A085"), QColor("#F39C12"), QColor("#D35400")
        ]
        qtl.members = [FamilyMember(r, colors[i % len(colors)]) for i, r in enumerate(roles)]
        
        for m in qtl.members:
            m.total_income = sum(t.amount for t in qtl.transactions if t.role == m.name and t.type == "income")
            m.total_expense = sum(t.amount for t in qtl.transactions if t.role == m.name and t.type == "expense")

        # Draw
        if not qtl.members: return
        cx, cy, r = 250, 250, 150 # Điều chỉnh tọa độ
        theme_border = QColor(THEMES[qtl.current_theme_key]['accent'])
        
        for i, m in enumerate(qtl.members):
            angle = 2 * math.pi * i / len(qtl.members) - math.pi/2
            x = cx + r * math.cos(angle) - 25
            y = cy + r * math.sin(angle) - 25
            node = BudgetNode(m, int(x), int(y), border_color=theme_border)
            node.update_size()
            qtl.scene.addItem(node)
            qtl.budget_nodes.append(node)
            
            # Draw Text Label
            text = QGraphicsTextItem(m.name)
            text.setPos(x, y + node.rect().height())
            text.setDefaultTextColor(QColor(THEMES[qtl.current_theme_key]['text_main']))
            qtl.scene.addItem(text)



    def show_context_menu(qtl, pos):
        menu = QMenu()
        menu.addAction("➕ Thêm", qtl.add_transaction)
        menu.addAction("✏️ Sửa", qtl.edit_transaction)
        menu.addAction("🗑️ Xóa", qtl.delete_transaction)

        row = qtl.table.currentRow()
        if row >= 0:
            tid = qtl.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            t = next((tr for tr in qtl.transactions if tr.id == tid), None)
            if t and t.is_recurring:
                menu.addAction("⏸️ Dừng định kỳ", lambda: qtl.stop_recurring(tid))

        menu.exec(qtl.table.viewport().mapToGlobal(pos))


    def apply_filter(qtl):
        keyword = qtl.keyword_edit.text().lower()
        type_text = qtl.type_filter.currentText()
        from_dt = qtl.from_date.date().toString("yyyy-MM-dd")
        to_dt = qtl.to_date.date().toString("yyyy-MM-dd")

        filtered = [
            t for t in qtl.transactions
            if (keyword in t.role.lower() or keyword in t.category.lower() or keyword in t.description.lower())
            and (type_text == "Tất cả" or (type_text == "Thu nhập" and t.type == "income") or (type_text == "Chi tiêu" and t.type == "expense"))
            and from_dt <= t.date <= to_dt
        ]
        qtl.update_table(filtered)

    def update_table(qtl, data=None):
        if data is None:
            data = qtl.transactions

        qtl.table.setRowCount(len(data))
        for row, t in enumerate(data):
            date_item = QTableWidgetItem(t.date)
            date_item.setData(Qt.ItemDataRole.UserRole, t.id)
            qtl.table.setItem(row, 0, date_item)
            qtl.table.setItem(row, 1, QTableWidgetItem("Thu" if t.type == "income" else "Chi"))
            qtl.table.setItem(row, 2, QTableWidgetItem(t.category))

            amt_item = QTableWidgetItem(f"{t.amount:,.0f}")
            amt_color = QColor("#27ae60") if t.type == "income" else QColor("#c0392b")
            amt_item.setForeground(QBrush(amt_color))
            amt_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            qtl.table.setItem(row, 3, amt_item)
            qtl.table.setItem(row, 4, QTableWidgetItem(t.role))
            qtl.table.setItem(row, 5, QTableWidgetItem(t.description))

            # Cột 6 = Định kỳ (checkbox)
            ck = QCheckBox()
            ck.setChecked(t.is_recurring)
            ck.setStyleSheet("margin-left:50%;")
            ck.toggled.connect(lambda checked, id=t.id: qtl.toggle_recurring(id, checked))
            qtl.table.setCellWidget(row, 6, ck)


    def stop_recurring(qtl, tid: str):
        # 1. Xóa giao dịch gốc
        qtl.transactions = [tr for tr in qtl.transactions if tr.id != tid]
        # 2. Xóa dòng lịch sử sinh của nó
        rec_file = pathlib.Path(__file__).parent / "recurring_last.txt"
        if rec_file.exists():
            lines = []
            with open(rec_file, encoding="utf-8") as f:
                lines = [ln for ln in f if not ln.startswith(tid + ",")]
            with open(rec_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
        qtl.save_to_csv()
        qtl.refresh_all()
        QMessageBox.information(qtl, "Định kỳ", "Đã dừng & xóa lịch định kỳ này.")


    def toggle_recurring(qtl, tid: str, checked: bool):
        t = next((tr for tr in qtl.transactions if tr.id == tid), None)
        if not t:
            return
        t.is_recurring = checked
        qtl.save_to_csv()
        qtl.refresh_all()



    def load_sample_data(qtl):
        qtl.transactions = [
            Transaction(1, "2023-04-01", "Groceries", 150.0, "expense", "parent"),
            Transaction(2, "2023-04-02", "Salary", 3000.0, "income", "parent"),
            Transaction(3, "2023-04-03", "Utilities", 85.5, "expense", "child"),
        ]
    

    def add_transaction(qtl):
        roles = sorted(set(t.role for t in qtl.transactions)) or ["Bố", "Mẹ"]

        dlg = TransactionDialog(qtl, roles, theme_key=qtl.current_theme_key)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            new_id = str(len(qtl.transactions))
            print("this is new id:",new_id)
            qtl.transactions.append(Transaction(new_id, **data))
            qtl.refresh_all()

    def edit_transaction(qtl):
        row = qtl.table.currentRow()
        if row < 0: return
        tid = qtl.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        trans = next((t for t in qtl.transactions if t.id == tid), None)
        if trans:
            dlg = TransactionDialog(qtl, sorted(set(t.role for t in qtl.transactions)), trans, theme_key=qtl.current_theme_key)
            if dlg.exec():
                for k, v in dlg.get_data().items(): setattr(trans, k, v)
                qtl.refresh_all()

    def delete_transaction(qtl):
        row = qtl.table.currentRow()
        if row < 0: return
        tid = qtl.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        qtl.transactions = [t for t in qtl.transactions if t.id != tid]
        qtl.refresh_all()

    def show_stats(qtl):
        dlg = StatisticsDialog(qtl, qtl.transactions)
        dlg.exec()


    def next_occurrence(qtl, last: QDate, t: Transaction) -> QDate:
        # Sử dụng cycle từ transaction
        if getattr(t, 'cycle', 'Tháng') == "Tuần":
            return last.addDays(7)
        else:  # Mặc định là Tháng
            return last.addMonths(1)


    def save_to_csv(qtl):
        try:
            os.makedirs(DATA_FILE.parent, exist_ok=True)
            with open(DATA_FILE, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                # Thêm header "cycle" vào cuối
                writer.writerow(["id", "date", "category", "amount", "type", "role", "description", "expiry_date", "is_recurring", "cycle"])
                for t in qtl.transactions:
                    # Lấy cycle, nếu không có thì mặc định là Tháng
                    c = getattr(t, "cycle", "Tháng")
                    writer.writerow([t.id, t.date, t.category, t.amount, t.type, t.role, t.description, t.expiry_date, t.is_recurring, c])
        except Exception as e:
            QMessageBox.warning(qtl, "Lưu tự động", f"Lỗi lưu file: {e}")


    def load_from_csv(qtl):
        if not DATA_FILE.exists():
            return
        try:
            with open(DATA_FILE, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                qtl.transactions = []
                for row in reader:
                    qtl.transactions.append(
                        Transaction(
                            row["id"], row["date"], row["category"],
                            float(row["amount"]), row["type"], row["role"],
                            row["description"], row["expiry_date"],
                            row["is_recurring"].lower() == "true",
                            row.get("cycle", "Tháng") # <--- Đọc cycle, dùng .get để tránh lỗi với file cũ
                        )
                    )
            qtl.refresh_all()
        except Exception as e:
            QMessageBox.warning(qtl, "Tải dữ liệu", f"Lỗi tải file: {e}")

    def import_csv(qtl):
        path, _ = QFileDialog.getOpenFileName(qtl, "Chọn file CSV", "", "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                imported = []
                for row in reader:
                    imported.append(
                        Transaction(
                            row.get("id", str(random.randint(1000, 9999))),
                            row["date"], row["category"],
                            float(row["amount"]), 
                            row["type"], 
                            row["role"],
                            row.get("description", ""),
                            row.get("expiry_date", ""),
                            row.get("is_recurring", "false").lower() == "true",
                            row.get("cycle", "Tháng") # tháng default 
                        )
                    )
            qtl.transactions.extend(imported)
            qtl.refresh_all()
            qtl.save_to_csv() 
            QMessageBox.information(qtl, "Import", f"Đã thêm {len(imported)} giao dịch.")
        except Exception as e:
            QMessageBox.critical(qtl, "Import", f"Lỗi: {e}")


    def export_csv(qtl):
        path, _ = QFileDialog.getSaveFileName(qtl, "Lưu file CSV", "", "CSV Files (*.csv)")
        if not path: return
        if not path.endswith(".csv"): path += ".csv"
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f) # -init csv
                writer.writerow(["id", "date", "category", "amount", "type", "role", "description", "expiry_date", "is_recurring", "cycle"])
                for t in qtl.transactions:
                    c = getattr(t, "cycle", "Tháng")
                    writer.writerow([
                        t.id, t.date, t.category, t.amount, t.type, t.role,
                        t.description, t.expiry_date, t.is_recurring, c
                    ])
            QMessageBox.information(qtl, "Export", f"Đã xuất {len(qtl.transactions)} giao dịch.")
        except Exception as e:
            QMessageBox.critical(qtl, "Export", f"Lỗi: {e}")

    #---- handle database--- 
    def backup_csv(qtl):
        try:
            os.makedirs(BACKUP_FOLDER, exist_ok=True)
            timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
            backup_file = BACKUP_FOLDER / f"transactions_backup_{timestamp}.csv"
            shutil.copy(DATA_FILE, backup_file)
        except Exception as e:
            QMessageBox.warning(qtl, "Backup", f"Lỗi sao lưu: {e}")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = TransactionMgr()
    window.show()
    sys.exit(app.exec())