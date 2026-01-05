import sys, math, random
import csv, json, pathlib

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import *

from datetime import date, datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict
from core._const import DEBT_DATA, PAYMENT_LOG, SCHEDULE_FILE

from . import DebtEngine
from models import Transaction # Import để tạo transaction trả nợ
from models import Debt
from core.data_manager import DataManager

from agent import BotChatAgentAPI, LLMWorker
from style import THEMES, SeasonalOverlay


class DebtAIAdvisorPane(QWidget):
    """Pane AI RAG – chỉ xử lý nợ – dễ gắn vào bất kỳ dialog nào"""
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.agent = BotChatAgentAPI()
        self._init_ui()

    def _init_ui(self):
        lo = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("🤖 AI Tư vấn nợ"))
        header.addStretch()
        self.btn_ask = QPushButton("Hỏi AI")
        self.btn_ask.clicked.connect(self.ask_advice)
        header.addWidget(self.btn_ask)
        lo.addLayout(header)

        # Output
        self.output = QTextEdit(readOnly=True)
        self.output.setPlaceholderText("Nhấn “Hỏi AI” để nhận tư vấn, cảnh báo, gợi ý dựa trên dữ liệu nợ của bạn...")
        lo.addWidget(self.output)

    # ---------- API chính ----------
    def ask_advice(self):
        self.output.clear()
        self.btn_ask.setEnabled(False)

        # 1. Thu thập dữ liệu thật
        debts = self.engine.get_debts()
        if not debts:
            self.output.setHtml("<i>Không có dữ liệu nợ để phân tích.</i>")
            self.btn_ask.setEnabled(True)
            return

        total_borrow = sum(d.outstanding() for d in debts if d.side == "IOWE")
        total_lent   = sum(d.outstanding() for d in debts if d.side == "THEY_OWE")
        total_interest = sum(self._total_interest(d) for d in debts)
        overdue_count  = len([d for d in debts if d.is_overdue()])

        # 2. Build prompt RAG – ngắn gọn, tiếng Việt
        prompt = f"""
Bạn là chuyên gia tài chính cá nhân AI. Dựa trên dữ liệu nợ thật dưới đây, hãy:
- Phân tích rủi ro (≤150 từ).
- Đưa 3 gợi ý thiết thực để giảm nợ hoặc tối ưu lãi.
- Cảnh báo nếu có khoản quá hạn.

Dữ liệu:
- Tổng tôi đang nợ: {total_borrow:,.0f} đ
- Tổng người khác nợ tôi: {total_lent:,.0f} đ
- Lãi tích lũy: {total_interest:,.0f} đ
- Số khoản quá hạn: {overdue_count}

Lưu ý: Trả lời bằng tiếng Việt, ngắn gọn, thân thiện, không dài dòng.
"""
        # 3. Stream từ AI
        self.worker = LLMWorker(prompt, self.agent)
        self.worker.newToken.connect(self._append_token)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    # ---------- slot nội bộ ----------
    def _append_token(self, token: str):
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertPlainText(token)

    def _on_done(self):
        self.btn_ask.setEnabled(True)

    # ---------- tính lãi (giữ nguyên) ----------
    def _total_interest(self, d):
        from datetime import date, datetime
        if d.outstanding() <= 0 or d.interest_rate <= 0:
            return 0
        days = (date.today() - datetime.fromisoformat(d.start_date).date()).days
        if days <= 0:
            return 0
        yearly_rate = d.interest_rate / 100
        if d.compound:
            return d.amount * ((1 + yearly_rate) ** (days / 365) - 1)
        else:
            return d.amount * yearly_rate * (days / 365)








class DebtForm(QDialog):
    def __init__(self, debt: Debt = None, parent=None, theme_key="spring"):
        super().__init__(parent)
        self.theme = THEMES[theme_key]
        self.setWindowTitle("Thông Tin Món Nợ")
        self.debt = debt
        self.resize(400, 500)
        self.init_ui()
        self.apply_style()

    def init_ui(self):
        lo = QFormLayout(self)
        self.counterparty = QLineEdit()
        self.side = QComboBox()
        self.side.addItem("Tôi vay", "IOWE")
        self.side.addItem("Tôi cho vay", "THEY_OWE")
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 1e9)
        self.amount.setSingleStep(100000)
        self.paid_back = QDoubleSpinBox()
        self.paid_back.setRange(0, 1e9)
        self.paid_back.setSingleStep(100000)
        self.interest_rate = QDoubleSpinBox()
        self.interest_rate.setRange(0, 100)
        self.term_months = QSpinBox()
        self.term_months.setRange(0, 120)
        self.start_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.due_date = QDateEdit(QDate.currentDate().addMonths(6))
        self.due_date.setCalendarPopup(True)
        self.due_date.setSpecialValueText("Không xác định")
        self.purpose = QLineEdit()
        self.compound = QComboBox()
        self.compound.addItem("Lãi đơn", False)
        self.compound.addItem("Lãi kép", True)

        lo.addRow("Đối tác:", self.counterparty)
        lo.addRow("Loại nợ:", self.side)
        lo.addRow("Số tiền gốc (₫):", self.amount)
        lo.addRow("Đã trả (₫):", self.paid_back)
        lo.addRow("Lãi suất (%/năm):", self.interest_rate)
        lo.addRow("Thời hạn (tháng):", self.term_months)
        lo.addRow("Ngày bắt đầu:", self.start_date)
        lo.addRow("Hạn trả:", self.due_date)
        lo.addRow("Mục đích:", self.purpose)
        lo.addRow("Cách tính lãi:", self.compound)

        if self.debt:
            self._load_debt(self.debt)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        lo.addRow(btn_box)

    def apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.theme['bg_primary']}; }}
            QLabel {{ color: {self.theme['text_main']}; font-weight: bold; }}
            QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit {{
                background-color: white; padding: 5px; border: 1px solid {self.theme['bg_secondary']}; border-radius: 4px;
            }}
        """)

    def _load_debt(self, d):
        self.counterparty.setText(d.counterparty)
        self.side.setCurrentIndex(0 if d.side == "IOWE" else 1)
        self.amount.setValue(d.amount)
        self.paid_back.setValue(d.paid_back)
        self.interest_rate.setValue(d.interest_rate)
        self.term_months.setValue(d.term_months)
        self.start_date.setDate(QDate.fromString(d.start_date, "yyyy-MM-dd"))
        if d.due_date:
            self.due_date.setDate(QDate.fromString(d.due_date, "yyyy-MM-dd"))
        self.purpose.setText(d.purpose)
        self.compound.setCurrentIndex(1 if d.compound else 0)

    def get_debt(self, debt_id):
        dd = self.due_date.date().toString("yyyy-MM-dd") if self.due_date.date().isValid() else None
        return Debt(
            debt_id, self.counterparty.text(), self.side.currentData(),
            self.amount.value(), self.paid_back.value(), self.interest_rate.value(),
            self.term_months.value(), self.start_date.date().toString("yyyy-MM-dd"),
            dd, self.purpose.text(), self.compound.currentData()
        )


import sys
from datetime import date, datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import *

# Import Data Manager (Singleton) & Model
from core.data_manager import DataManager
from models._debt import Debt

# Import AI (Giả sử bạn đã có các file này)
from agent import BotChatAgentAPI, LLMWorker 

class DebtStatsDialog(QDialog):
    def __init__(self, parent=None, theme_key="spring"):
        super().__init__(parent)
        
        # --- KẾT NỐI DATA MANAGER ---
        self.data_manager = DataManager.instance()
        self.data_manager.data_changed.connect(self.populate_data)
        
        # Theme mở rộng
        self.theme = {
            'bg_primary': "#f4f4f9",
            'card_bg': "#ffffff",
            'text_main': "#333333",
            'text_sub': "#666666",
            'danger': "#e74c3c",
            'success': "#2ecc71",
            'warning': "#f39c12",
            'accent': "#3498db"
        }
        self.setWindowTitle("📊 Dashboard Phân Tích Nợ")
        self.resize(1000, 700)
        
        self.init_ui()
        self.apply_theme()
        self.populate_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- 1. Header Toolbar ---
        header = QFrame()
        header.setStyleSheet(f"background-color: {self.theme['card_bg']}; border-bottom: 1px solid #ddd;")
        hl = QHBoxLayout(header)
        
        lbl_title = QLabel("TỔNG QUAN TÀI CHÍNH (NỢ)")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        self.btn_close = QPushButton("Đóng")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)

        hl.addWidget(lbl_title)
        hl.addStretch()
        hl.addWidget(self.btn_close)
        main_layout.addWidget(header)

        # --- 2. Nội dung – QTabWidget ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {self.theme['accent']}; }}
            QTabBar::tab {{ background: {self.theme['card_bg']}; color: {self.theme['text_main']}; padding: 8px 16px; border-radius: 6px; }}
            QTabBar::tab:selected {{ background: {self.theme['accent']}; color: white; }}
        """)
        main_layout.addWidget(self.tabs)

        # Tạo 3 tab
        self._build_tab_stats()
        self._build_tab_ai()
        self._build_tab_history()

    # ---------- Tab Builders ----------
    def _build_tab_stats(self):
        tab = QWidget()
        lo = QVBoxLayout(tab)
        # A. Cards Grid
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(15)
        lo.addLayout(self.stats_grid)
        # B. Charts Layout
        self.charts_layout = QGridLayout()
        lo.addLayout(self.charts_layout)
        self.tabs.addTab(tab, "📊 Thống kê")
        
    def _build_tab_history(self):
        tab = QWidget()
        lo = QVBoxLayout(tab)
        lo.addWidget(QLabel("📜 Lịch sử trả gần đây:"))
        self.tab_history = QTableWidget(0, 3)
        self.tab_history.setHorizontalHeaderLabels(["Ngày", "Số tiền", "Còn lại"])
        self.tab_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab_history.setShowGrid(False)
        lo.addWidget(self.tab_history)
        self.tabs.addTab(tab, "📜 Lịch sử")

    def _build_tab_ai(self):
        tab = QWidget()
        lo = QVBoxLayout(tab)
        header = QHBoxLayout()
        header.addWidget(QLabel("🤖 AI Tư vấn nợ"))
        header.addStretch()
        self.btn_ask_ai = QPushButton("Hỏi AI")
        self.btn_ask_ai.clicked.connect(self.ask_ai_debt)
        header.addWidget(self.btn_ask_ai)
        lo.addLayout(header)
        
        self.ai_output = QTextEdit(readOnly=True)
        self.ai_output.setPlaceholderText("Nhấn “Hỏi AI” để nhận tư vấn, cảnh báo...")
        lo.addWidget(self.ai_output)
        self.tabs.addTab(tab, "💡 AI Tư vấn")

    def _clear_layout(self, layout):
            """Xóa sạch các widget trong layout để vẽ lại từ đầu"""
            if layout is None: return
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())

    # ---------- Data Logic ----------
    def populate_data(self):
            """Hàm này sẽ được gọi mỗi khi dữ liệu thay đổi"""
            
            # 1. Xóa dữ liệu cũ trên giao diện trước khi vẽ mới
            self._clear_layout(self.stats_grid)
            self._clear_layout(self.charts_layout)
            
            # 2. Lấy dữ liệu mới nhất
            debts = self.data_manager.debts 
            
            if not debts:
                # Nếu hết nợ, hiện thông báo vui
                lbl = QLabel("🎉 Tuyệt vời! Bạn không có khoản nợ nào.")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("font-size: 18px; color: green; margin-top: 50px;")
                self.stats_grid.addWidget(lbl, 0, 0, 1, 4)
                return

            # 3. Tính toán lại
            total_borrowed = sum(d.outstanding() for d in debts if d.side == "IOWE")
            total_lent = sum(d.outstanding() for d in debts if d.side == "THEY_OWE")
            total_interest = sum(self._total_interest(d) for d in debts)
            overdue_count = len([d for d in debts if d.is_overdue()])

            # 4. Vẽ lại Card
            c1 = self._create_card("Tôi đang nợ", f"{total_borrowed:,.0f} đ", 
                                "Cần thanh toán sớm" if total_borrowed > 0 else "Tuyệt vời!", 
                                self.theme['danger'], "💸")
            c2 = self._create_card("Cần thu hồi", f"{total_lent:,.0f} đ", 
                                "Tiền đang ở ngoài" if total_lent > 0 else "Không ai nợ bạn", 
                                self.theme['success'], "📥")
            c3 = self._create_card("Lãi tích lũy", f"{total_interest:,.0f} đ", 
                                "Số tiền mất đi do lãi", self.theme['warning'], "📈")
            c4 = self._create_card("Trạng thái", f"{overdue_count} khoản quá hạn", 
                                "Kiểm tra kỹ hạn trả", "#e67e22", "⚠️")

            self.stats_grid.addWidget(c1, 0, 0)
            self.stats_grid.addWidget(c2, 0, 1)
            self.stats_grid.addWidget(c3, 0, 2)
            self.stats_grid.addWidget(c4, 0, 3)

            # 5. Vẽ lại Biểu đồ
            self._build_radar_chart(debts)

    def _total_interest(self, d: Debt):
        if d.outstanding() <= 0 or d.interest_rate <= 0: return 0
        try:
            days = (date.today() - datetime.fromisoformat(d.start_date).date()).days
            if days <= 0: return 0
            yearly_rate = d.interest_rate / 100
            if d.compound:
                return d.amount * ((1 + yearly_rate) ** (days / 365) - 1)
            else:
                return d.amount * yearly_rate * (days / 365)
        except: return 0

    def ask_ai_debt(self):
        self.ai_output.clear()
        self.btn_ask_ai.setEnabled(False)

        # Lấy dữ liệu thật từ Singleton
        debts = self.data_manager.debts
        if not debts:
            self.ai_output.setHtml("<i>Không có dữ liệu nợ để phân tích.</i>")
            self.btn_ask_ai.setEnabled(True)
            return

        total_borrow = sum(d.outstanding() for d in debts if d.side == "IOWE")
        total_lent   = sum(d.outstanding() for d in debts if d.side == "THEY_OWE")
        total_interest = sum(self._total_interest(d) for d in debts)
        overdue_count  = len([d for d in debts if d.is_overdue()])

        prompt = f"""
        Bạn là chuyên gia tài chính AI. Dựa trên dữ liệu nợ:
        - Tổng nợ phải trả: {total_borrow:,.0f} đ
        - Tổng nợ cần thu: {total_lent:,.0f} đ
        - Lãi tích lũy: {total_interest:,.0f} đ
        - Số khoản quá hạn: {overdue_count}
        
        Hãy đưa ra lời khuyên ngắn gọn để tối ưu tài chính.
        """

        self.agent = BotChatAgentAPI()
        self.worker = LLMWorker(prompt, self.agent)
        self.worker.newToken.connect(self._append_ai_token)
        self.worker.finished.connect(self._on_ai_done)
        self.worker.start()

    def _append_ai_token(self, token):
        self.ai_output.moveCursor(QTextCursor.MoveOperation.End)
        self.ai_output.insertPlainText(token)

    def _on_ai_done(self):
        self.btn_ask_ai.setEnabled(True)

    # ---------- Helpers UI ----------
    def apply_theme(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.theme['bg_primary']}; }}
            QLabel {{ color: {self.theme['text_main']}; }}
            QPushButton {{ background-color: {self.theme['accent']}; color: white; border-radius: 6px; padding: 6px 15px; font-weight: bold; }}
            QPushButton:hover {{ background-color: #2980b9; }}
        """)

    def _create_card(self, title, value, subtext, color_code, icon):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background-color: {self.theme['card_bg']}; border-radius: 10px; border-left: 5px solid {color_code}; }}
        """)
        frame.setMinimumHeight(100)
        layout = QVBoxLayout(frame)
        
        lbl_title = QLabel(f"{icon} {title}")
        lbl_title.setStyleSheet(f"color: {self.theme['text_sub']}; font-size: 11px; text-transform: uppercase;")
        
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 22px; font-weight: bold;")
        
        lbl_sub = QLabel(subtext)
        lbl_sub.setStyleSheet(f"color: {color_code}; font-size: 11px; font-style: italic;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_sub)
        layout.addStretch()
        return frame

    def _build_radar_chart(self, debts):
        # Lấy khoản nợ lớn nhất làm mẫu vẽ
        target_debt = max(debts, key=lambda x: x.amount, default=None)
        if not target_debt: return

        radar = QPolarChart()
        radar.setTitle(f"Phân tích rủi ro: {target_debt.counterparty}")
        radar.legend().setVisible(False)

        # Logic vẽ (Giữ nguyên logic của bạn)
        categories = ["Gốc", "Lãi", "Đã trả", "Dư nợ", "Rủi ro"]
        risk = 100 if target_debt.is_overdue() else min(100, target_debt.interest_rate * 2)
        values = [100, min(100, target_debt.interest_rate * 5), 
                  (target_debt.paid_back/target_debt.amount*100) if target_debt.amount else 0,
                  (target_debt.outstanding()/target_debt.amount*100) if target_debt.amount else 0,
                  risk]
        
        series = QLineSeries()
        for i, val in enumerate(values): series.append(i, val)
        series.append(len(values), values[0])
        radar.addSeries(series)

        # Axis
        ang_axis = QCategoryAxis()
        for i, c in enumerate(categories): ang_axis.append(c, i)
        ang_axis.append("End", len(categories))
        ang_axis.setRange(0, len(categories))
        radar.addAxis(ang_axis, QPolarChart.PolarOrientation.PolarOrientationAngular)
        series.attachAxis(ang_axis)

        rad_axis = QValueAxis()
        rad_axis.setRange(0, 100)
        rad_axis.setVisible(False)
        radar.addAxis(rad_axis, QPolarChart.PolarOrientation.PolarOrientationRadial)
        series.attachAxis(rad_axis)

        chart_view = QChartView(radar)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(400)
        
        # Clear layout cũ trước khi add (để tránh chồng chéo khi refresh)
        while self.charts_layout.count():
            item = self.charts_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.charts_layout.addWidget(chart_view, 0, 0)

class DebtManager(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # --- 1. KẾT NỐI DATA MANAGER ---
        self.data_manager = DataManager.instance()
        # Lắng nghe thay đổi dữ liệu để tự refresh UI
        self.data_manager.data_changed.connect(self.refresh)

        self.current_theme = "spring"

        self.init_ui()

        # Overlay Effect
        self.overlay = SeasonalOverlay(self.centralWidget())
        self.overlay.show()
        self.overlay.raise_()
        self.apply_theme("spring")

        # Load lần đầu
        self.refresh()
        self.check_overdue()

    def init_ui(self):
        self.setWindowTitle("Quản Lý Nợ")
        self.resize(1100, 700)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # LEFT PANEL
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_lo = QVBoxLayout(left_panel)

        # Toolbar
        toolbar_lo = QHBoxLayout()
        self.btn_add      = self.create_btn("➕ Thêm", self.add_debt)
        self.btn_import   = self.create_btn("📤 Import", self.import_csv)
        self.btn_export   = self.create_btn("📥 Export", self.export_csv)
        self.btn_stats    = self.create_btn("📊 Thống Kê", self.open_stats)
        self.btn_schedule = self.create_btn("📅 Lịch trả", self.export_schedule)

        toolbar_lo.addWidget(self.btn_add)
        toolbar_lo.addWidget(self.btn_import)
        toolbar_lo.addWidget(self.btn_export)
        toolbar_lo.addWidget(self.btn_stats)
        toolbar_lo.addWidget(self.btn_schedule)
        toolbar_lo.addStretch()
        left_lo.addLayout(toolbar_lo)

        # Table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Đối tác", "Loại", "Gốc", "Còn lại", "Lãi %", "Hạn", "Trả", "Lãi đến nay"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self.edit_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        left_lo.addWidget(self.table)

        # Summary
        self.summary_frame = QFrame()
        self.summary_frame.setObjectName("summary")
        sum_lo = QHBoxLayout(self.summary_frame)
        self.lbl_owe = QLabel()
        self.lbl_receive = QLabel()
        self.lbl_net = QLabel()
        sum_lo.addWidget(self.lbl_owe)
        sum_lo.addWidget(self.lbl_receive)
        sum_lo.addWidget(self.lbl_net)
        left_lo.addWidget(self.summary_frame)

        # Lịch sử trả (Local Log)
        left_lo.addWidget(QLabel("Lịch sử trả gần đây:"))
        self.tab_history = QTableWidget(0, 3)
        self.tab_history.setHorizontalHeaderLabels(["Ngày", "Số tiền", "Còn lại"])
        self.tab_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab_history.setShowGrid(False)
        left_lo.addWidget(self.tab_history)

        # RIGHT PANEL – Charts
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_lo = QVBoxLayout(right_panel)
        self.pie_view = QChartView()
        self.pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.bar_view = QChartView()
        self.bar_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        right_lo.addWidget(self.pie_view)
        right_lo.addWidget(self.bar_view)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([650, 450])
        main_layout.addWidget(splitter)

    # ------------------- CORE FEATURES -------------------
    def refresh(self):
        # Lấy dữ liệu từ Singleton DataManager
        debts = self.data_manager.debts
        s = self.data_manager.debt_engine.summary() # Gọi engine con qua manager

        self.lbl_owe.setText(f"Cần trả: {s['i_owe']:,.0f} đ")
        self.lbl_owe.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 14px;")
        
        self.lbl_receive.setText(f"Cần thu: {s['they_owe']:,.0f} đ")
        self.lbl_receive.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 14px;")
        
        self.lbl_net.setText(f"Ròng: {s['net']:,.0f} đ")
        self.lbl_net.setStyleSheet("color: #3498db; font-weight: bold; font-size: 14px;")

        self.table.setRowCount(0)
        for d in debts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(d.counterparty))
            self.table.setItem(row, 1, QTableWidgetItem("Vay" if d.side == "IOWE" else "Cho vay"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{d.amount:,.0f}"))

            rem_item = QTableWidgetItem(f"{d.outstanding():,.0f}")
            rem_item.setForeground(QColor("red") if d.outstanding() > 0 else QColor("green"))
            self.table.setItem(row, 3, rem_item)

            self.table.setItem(row, 4, QTableWidgetItem(f"{d.interest_rate}%"))
            due_str = d.due_date if d.due_date else "-"
            self.table.setItem(row, 5, QTableWidgetItem(due_str))

            # Nút Trả Nhanh
            btn = QPushButton("Trả")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, id=d.id: self.quick_pay(id))
            self.table.setCellWidget(row, 6, btn)

            # Lãi tính đến nay (Tính trên giao diện)
            interest_today = self._calculate_interest(d)
            self.table.setItem(row, 7, QTableWidgetItem(f"{interest_today:,.0f}"))

            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, d.id)

        self.update_charts(s, debts)
        self._load_payment_log()

    def update_charts(self, s, debts):
        # Pie Chart
        series = QPieSeries()
        if s["i_owe"] > 0:
            slice_owe = series.append("Nợ", s["i_owe"])
            slice_owe.setBrush(QColor("#e74c3c"))
        if s["they_owe"] > 0:
            slice_they = series.append("Thu", s["they_owe"])
            slice_they.setBrush(QColor("#2ecc71"))
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Cơ Cấu Nợ")
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.setBackgroundBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.pie_view.setChart(chart)

        # Bar Chart (Chi tiết)
        bar_set = QBarSet("Còn lại")
        categories = []
        # Chỉ lấy top 5 active debts để vẽ cho đẹp
        active_debts = [d for d in debts if d.outstanding() > 0][:5]
        
        for d in active_debts:
            categories.append(d.counterparty)
            bar_set.append(d.outstanding())
            
        bar_series = QBarSeries()
        bar_series.append(bar_set)
        
        chart2 = QChart()
        chart2.addSeries(bar_series)
        chart2.setTitle("Top Khoản Nợ")
        chart2.setBackgroundBrush(QBrush(Qt.BrushStyle.NoBrush))
        
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart2.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)
        self.bar_view.setChart(chart2)

    # ------------------- ACTIONS -------------------
    def add_debt(self):
        # Truyền engine vào dialog nếu dialog cần check duplicate ID (optional)
        form = DebtForm(parent=self, theme_key=self.current_theme)
        if form.exec():
            # Lấy ID mới từ engine
            new_id = self.data_manager.debt_engine.next_id()
            debt = form.get_debt(new_id)
            
            # GỌI DATA MANAGER
            self.data_manager.add_debt(debt)

    def edit_selected(self):
        debt = self._selected_debt()
        if debt:
            form = DebtForm(debt, parent=self, theme_key=self.current_theme)
            if form.exec():
                updated_debt = form.get_debt(debt.id)
                self.data_manager.update_debt(updated_debt)

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0: return
        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ Xóa")
        action = menu.exec(self.table.mapToGlobal(pos))
        if action == delete_action:
            _id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            confirm = QMessageBox.question(self, "Xác nhận", "Xóa khoản nợ này?")
            if confirm == QMessageBox.StandardButton.Yes:
                self.data_manager.delete_debt(_id)

    def quick_pay(self, debt_id: int):
        # Tìm debt trong list của manager
        debt = next((d for d in self.data_manager.debts if d.id == debt_id), None)
        if not debt or debt.outstanding() <= 0: return

        amount, ok = QInputDialog.getDouble(
            self, "Trả nợ", f"Trả bao nhiêu? (còn {debt.outstanding():,.0f} đ)",
            value=min(1_000_000, debt.outstanding()), min=10_000, max=debt.outstanding()
        )
        if not ok or amount <= 0: return

        # 1. Cập nhật Debt
        debt.paid_back += amount
        self.data_manager.update_debt(debt)

        # 2. Tự động ghi log vào Transaction (GỌI QUA DATA MANAGER)
        self._create_repay_transaction(debt, amount)

        # 3. Ghi log trả nợ riêng (nếu cần)
        self._log_payment(debt_id, amount)
        
        QMessageBox.information(self, "OK", f"Đã trả {amount:,.0f} đ\nĐã ghi sổ chi tiêu!")

    def _create_repay_transaction(self, debt: Debt, amount: float):
        """
        Tự động tạo giao dịch Thu hoặc Chi dựa trên loại nợ
        """
        import uuid # Import thêm thư viện này ở đầu file nếu chưa có
        
        # 1. Xác định Loại giao dịch (Thu hay Chi)
        if debt.side == "IOWE":
            # Mình đi trả nợ -> Mất tiền -> CHI TIÊU
            trans_type = "expense"
            category = "Trả nợ"
            role = "Cá nhân" # Người chi là mình
            desc = f"Trả nợ cho {debt.counterparty} ({debt.purpose})"
        else:
            # Người ta trả nợ mình -> Nhận tiền -> THU NHẬP
            trans_type = "income"
            category = "Thu nợ"
            role = debt.counterparty # Người chi là đối tác
            desc = f"Thu nợ từ {debt.counterparty} ({debt.purpose})"

        # 2. Tạo ID ngẫu nhiên
        new_id = str(uuid.uuid4())
        
        # 3. Tạo Object Transaction
        trans = Transaction(
            id=new_id,
            date=date.today().isoformat(),
            category=category,      # "Trả nợ" hoặc "Thu nợ"
            amount=amount,
            type=trans_type,        # "expense" hoặc "income" <--- QUAN TRỌNG
            role=role,
            description=desc,
            expiry_date="",
            is_recurring=False,
            cycle="Tháng"
        )
        
        # 4. Gửi sang DataManager
        self.data_manager.add_transaction(trans)
        
        # Log ra console để kiểm tra (tùy chọn)
        print(f"✅ Auto Transaction: {trans_type.upper()} - {amount:,.0f} - {desc}")


    # ------------------- UTILS (Import/Export/Stats) -------------------
    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                # Gọi Engine thông qua Manager
                count = self.data_manager.debt_engine.import_csv(path)
                self.data_manager.notify_change()
                QMessageBox.information(self, "OK", f"Import thành công {count} khoản nợ!")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu file CSV", "", "CSV Files (*.csv)")
        if path:
            if self.data_manager.debt_engine.export_csv(path):
                QMessageBox.information(self, "OK", "Export thành công!")

    def open_stats(self):
        # Không cần truyền engine nữa
        dlg = DebtStatsDialog(parent=self, theme_key=self.current_theme) 
        dlg.exec()


    # ------------------- HELPER FUNCTIONS -------------------
    def _selected_debt(self) -> Debt | None:
        row = self.table.currentRow()
        if row < 0: return None
        _id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((d for d in self.data_manager.debts if d.id == _id), None)

    def _calculate_interest(self, d: Debt) -> float:
        # Helper tính lãi để hiển thị lên bảng
        if d.outstanding() <= 0 or d.interest_rate <= 0: return 0
        try:
            days = (date.today() - datetime.fromisoformat(d.start_date).date()).days
            if days <= 0: return 0
            yearly_rate = d.interest_rate / 100
            if d.compound:
                return d.amount * ((1 + yearly_rate) ** (days / 365) - 1)
            else:
                return d.amount * yearly_rate * (days / 365)
        except: return 0

    def check_overdue(self):
        overdue = [d for d in self.data_manager.debts if d.is_overdue()]
        if overdue:
            names = ", ".join(d.counterparty for d in overdue)
            QMessageBox.warning(self, "Nhắc hạn", f"Quá hạn: {names}")

    def create_btn(self, text, func):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(func)
        btn.setFixedHeight(35)
        return btn



    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.centralWidget().rect())
        if not self.overlay.initialized:
            self.overlay.init_particles()


    def apply_theme(self, key):...
        # self.current_theme = key
        # t = THEMES[key]
        # self.overlay.set_season(key)
        # self.centralWidget().setStyleSheet(f"background-color: {t['bg_primary']};")

        # panel_qss = f"QFrame#panel {{ background-color: rgba(255,255,255,0.7); border: 1px solid {t['accent']}; border-radius: 10px; }}"
        # self.findChild(QFrame, "panel").setStyleSheet(panel_qss)

        # btn_qss = f"""
        #     QPushButton {{ background-color: {t['bg_secondary']}; color: white; border-radius: 5px; padding: 5px 10px; font-weight: bold; border: none; }}
        #     QPushButton:hover {{ background-color: {t['btn_hover']}; }}
        # """
        # for btn in [self.btn_add, self.btn_import, self.btn_export, self.btn_stats, self.btn_schedule]:
        #     btn.setStyleSheet(btn_qss)

        # table_qss = f"""
        #     QTableWidget {{ background-color: rgba(255,255,255,0.8); border: none; gridline-color: transparent; color: {t['text_main']}; }}
        #     QHeaderView::section {{ background-color: {t['bg_secondary']}; color: white; padding: 8px; border: none; font-weight: bold; }}
        #     QTableWidget::item:selected {{ background-color: {t['accent']}; color: {t['text_main']}; }}
        # """
        # self.table.setStyleSheet(table_qss)
        # self.table.horizontalHeader().setStyleSheet(table_qss)
        # self.summary_frame.setStyleSheet(f"background-color: {t['bg_secondary']}; border-radius: 8px; color: white;")
        # self.refresh()


    def _log_payment(self, debt_id: int, amount: float):
        log = []
        # Kiểm tra file tồn tại và đọc (Thêm try-except để an toàn hơn)
        if PAYMENT_LOG.exists():
            try:
                log = json.loads(PAYMENT_LOG.read_text(encoding="utf8"))
            except: 
                log = [] # Nếu file lỗi thì reset thành list rỗng

        # --- SỬA LỖI TẠI ĐÂY ---
        # Thay self.engine.get_debts() bằng self.data_manager.debts
        # Thêm default=None để tránh crash nếu không tìm thấy ID
        debt = next((d for d in self.data_manager.debts if d.id == debt_id), None)
        
        if debt:
            log.append({
                "debt_id": debt_id,
                "counterparty": debt.counterparty,
                "date": date.today().isoformat(),
                "amount": amount,
                "remain": debt.outstanding()
            })
            log = log[-20:]  # Giữ 20 dòng gần nhất
            
            # Ghi file
            PAYMENT_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf8")
            
            # Load lại bảng hiển thị
            self._load_payment_log()

    def _load_payment_log(self):
        if not PAYMENT_LOG.exists():
            return
        
        try:
            log = json.loads(PAYMENT_LOG.read_text(encoding="utf8"))
        except:
            return # File lỗi thì bỏ qua

        self.tab_history.setRowCount(0)
        # Đảo ngược list để hiện cái mới nhất lên đầu (log[::-1])
        for entry in log[::-1]:  
            row = self.tab_history.rowCount()
            self.tab_history.insertRow(row)
            self.tab_history.setItem(row, 0, QTableWidgetItem(entry.get("date", "")))
            
            # Format tiền tệ
            amt = float(entry.get("amount", 0))
            rem = float(entry.get("remain", 0))
            
            self.tab_history.setItem(row, 1, QTableWidgetItem(f"{amt:,.0f}"))
            self.tab_history.setItem(row, 2, QTableWidgetItem(f"{rem:,.0f}"))



    def export_schedule(self):
        debt = self._selected_debt()
        if not debt:
            QMessageBox.warning(self, "Chọn nợ", "Vui lòng chọn 1 món nợ để export!")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu lịch trả", f"{debt.counterparty}_schedule.csv", "CSV (*.csv)")
        if not path:
            return
        schedule = debt.repayment_schedule()
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Kỳ", "Ngày", "Số tiền phải trả", "Trạng thái"])
            for idx, row in enumerate(schedule, 1):
                status = "Đã trả" if row["paid"] else "Chưa trả"
                writer.writerow([idx, row["date"], f"{row['amount']:,.0f}", status])
        QMessageBox.information(self, "OK", f"Đã xuất lịch trả:\n{path}")
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = DebtManager()
    win.show()
    sys.exit(app.exec())