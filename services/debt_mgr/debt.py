import sys, math, random
import csv, json, pathlib

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import *

from datetime import date, datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict
from core._const import DATA_FILE

from . import DebtEngine
from agent import BotChatAgentAPI, LLMWorker
from models import Debt
from style import THEMES, SeasonalOverlay

DATA_FILE = pathlib.Path("debts.json")
DATA_FILE      = pathlib.Path("debts.json")
PAYMENT_LOG    = pathlib.Path("payment_log.json")
SCHEDULE_FILE  = pathlib.Path("schedule_export.csv")







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
        self.worker = LLMWorkerDebt(prompt, self.agent)
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


class DebtStatsDialog(QDialog):
    def __init__(self, engine, parent=None, theme_key="spring"):
        super().__init__(parent)
        self.engine = engine
        # Theme mở rộng cho trực quan hơn
        self.theme = {
            'bg_primary': "#f4f4f9",      # Nền sáng nhẹ
            'card_bg': "#ffffff",         # Nền thẻ trắng
            'text_main': "#333333",
            'text_sub': "#666666",
            'danger': "#e74c3c",          # Đỏ (Nợ phải trả)
            'success': "#2ecc71",         # Xanh (Người khác nợ mình)
            'warning': "#f39c12",         # Vàng (Lãi/Sắp hạn)
            'accent': "#3498db"           # Xanh dương (Chính)
        }
        self.setWindowTitle("📊 Dashboard Phân Tích Nợ")
        self.resize(1000, 700)
        self.init_ui()
        self.apply_theme()
        self.populate_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) # Full viền

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

        # --- 2. Nội dung – QTabWidget (3 tab) ---
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

    # ---------- 3 tab ----------
    def _build_tab_stats(self):
        tab = QWidget()
        lo = QVBoxLayout(tab)

        # A. Cards
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(15)
        lo.addLayout(self.stats_grid)

        # B. Charts
        self.charts_layout = QGridLayout()
        lo.addLayout(self.charts_layout)

        self.tabs.addTab(tab, "📊 Thống kê")

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
        self.ai_output.setPlaceholderText("Nhấn “Hỏi AI” để nhận tư vấn, cảnh báo, gợi ý dựa trên dữ liệu nợ của bạn...")
        lo.addWidget(self.ai_output)

        self.tabs.addTab(tab, "💡 AI Tư vấn")

    def _build_tab_history(self):
        tab = QWidget()
        lo = QVBoxLayout(tab)

        lo.addWidget(QLabel("📜 Lịch sử trả gần đây:"))
        self.tab_history = QTableWidget(0, 3)
        self.tab_history.setHorizontalHeaderLabels(["Ngày", "Số tiền", "Còn lại"])
        self.tab_history.setShowGrid(False)
        lo.addWidget(self.tab_history)

        self.tabs.addTab(tab, "📜 Lịch sử")

    # ---------- AI Tư vấn ----------
    def ask_ai_debt(self):
        """Gửi dữ liệu nợ → AI → stream tư vấn"""
        self.ai_output.clear()
        self.btn_ask_ai.setEnabled(False)

        # 1. Thu thập dữ liệu thật
        debts = self.engine.get_debts()
        if not debts:
            self.ai_output.setHtml("<i>Không có dữ liệu nợ để phân tích.</i>")
            self.btn_ask_ai.setEnabled(True)
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

        self.agent = BotChatAgentAPI()
        self.worker = LLMWorker(prompt, self.agent)
        self.worker.newToken.connect(self._append_ai_token)
        self.worker.finished.connect(self._on_ai_done)
        self.worker.start()

    def _append_ai_token(self, token: str):
        self.ai_output.moveCursor(QTextCursor.MoveOperation.End)
        self.ai_output.insertPlainText(token)

    def _on_ai_done(self):
        self.btn_ask_ai.setEnabled(True)

    def apply_theme(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.theme['bg_primary']}; }}
            QLabel {{ color: {self.theme['text_main']}; }}
            QPushButton {{ 
                background-color: {self.theme['accent']}; color: white; 
                border-radius: 6px; padding: 6px 15px; font-weight: bold; 
            }}
            QPushButton:hover {{ background-color: #2980b9; }}
        """)

    def _create_card(self, title, value, subtext, color_code, icon="💰"):
        """Tạo thẻ hiển thị thông số đẹp mắt"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ 
                background-color: {self.theme['card_bg']}; 
                border-radius: 10px; 
                border-left: 5px solid {color_code};
            }}
        """)
        frame.setMinimumHeight(100)
        
        layout = QVBoxLayout(frame)
        
        # Tiêu đề
        lbl_title = QLabel(f"{icon} {title}")
        lbl_title.setStyleSheet(f"color: {self.theme['text_sub']}; font-size: 11px; text-transform: uppercase;")
        
        # Giá trị chính
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 22px; font-weight: bold;")
        
        # Chú thích phụ
        lbl_sub = QLabel(subtext)
        lbl_sub.setStyleSheet(f"color: {color_code}; font-size: 11px; font-style: italic;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_sub)
        layout.addStretch()
        return frame

    def populate_data(self):
        debts = self.engine.get_debts()
        
        # Xóa widget cũ nếu reload
        # (Ở đây làm đơn giản, thực tế nên clear layout)

        if not debts:
            self.content_layout.addWidget(QLabel("Chưa có dữ liệu nợ."))
            return

        # --- TÍNH TOÁN SỐ LIỆU ---
        total_borrowed = sum(d.outstanding() for d in debts if d.side == "IOWE") # Mình nợ
        total_lent = sum(d.outstanding() for d in debts if d.side == "THEY_OWE") # Người khác nợ
        total_interest = sum(self._total_interest(d) for d in debts)
        overdue_count = len([d for d in debts if d.is_overdue()])

        # --- 1. VẼ CÁC THẺ (CARDS) ---
        # Card 1: Mình nợ (Quan trọng nhất - Màu Đỏ)
        c1 = self._create_card("Tôi đang nợ", f"{total_borrowed:,.0f} đ", 
                               "Cần thanh toán sớm" if total_borrowed > 0 else "Tuyệt vời, sạch nợ!", 
                               self.theme['danger'], "💸")
        
        # Card 2: Người khác nợ (Màu Xanh)
        c2 = self._create_card("Cần thu hồi", f"{total_lent:,.0f} đ", 
                               "Tiền đang ở ngoài" if total_lent > 0 else "Không ai nợ bạn", 
                               self.theme['success'], "📥")
        
        # Card 3: Lãi phát sinh (Màu Vàng)
        c3 = self._create_card("Lãi tích lũy", f"{total_interest:,.0f} đ", 
                               "Số tiền mất đi do lãi" if total_interest > 0 else "Không chịu lãi", 
                               self.theme['warning'], "📈")
        
        # Card 4: Cảnh báo (Màu Cam)
        status_text = f"{overdue_count} khoản quá hạn" if overdue_count > 0 else "Tất cả đúng hạn"
        c4 = self._create_card("Trạng thái", status_text, 
                               "Kiểm tra kỹ hạn trả" if overdue_count > 0 else "An toàn", 
                               "#e67e22", "⚠️")

        self.stats_grid.addWidget(c1, 0, 0)
        self.stats_grid.addWidget(c2, 0, 1)
        self.stats_grid.addWidget(c3, 0, 2)
        self.stats_grid.addWidget(c4, 0, 3)

        # --- 2. VẼ BIỂU ĐỒ RADAR (Đã nâng cấp UX) ---
        self._build_radar_chart(debts)

    def _build_radar_chart(self, debts):
        """Vẽ biểu đồ Radar đánh giá rủi ro"""
        # Chọn khoản nợ rủi ro nhất (hoặc lớn nhất) để hiển thị làm mẫu
        target_debt = max(debts, key=lambda x: x.amount, default=None)
        if not target_debt: return

        radar = QPolarChart()
        radar.setTitle(f"Phân tích rủi ro: {target_debt.counterparty}")
        radar.setTitleFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        radar.legend().setVisible(False)

        # 5 Tiêu chí đánh giá (Các trục của Radar)
        categories = ["Gốc vay", "Lãi suất", "Đã trả", "Dư nợ", "Rủi ro"]
        
        # Tính toán điểm (giả lập 0-100 cho dễ nhìn)
        # Rủi ro: tính dựa trên ngày quá hạn hoặc lãi suất cao
        risk_score = min(100, target_debt.interest_rate * 2) 
        if target_debt.is_overdue(): risk_score = 100

        values = [
            100, # Gốc luôn là 100% tham chiếu
            min(100, target_debt.interest_rate * 5), # Scale lãi lên để dễ nhìn
            (target_debt.paid_back / target_debt.amount * 100) if target_debt.amount else 0,
            (target_debt.outstanding() / target_debt.amount * 100) if target_debt.amount else 0,
            risk_score
        ]

        series = QLineSeries()
        series.setName("Chỉ số")
        
        # Map giá trị vào các góc của Radar
        # Góc chia đều: 360 / 5 = 72 độ
        for i, val in enumerate(values):
            series.append(i, val) 
        series.append(len(values), values[0]) # Khép vòng

        radar.addSeries(series)

        # --- TRỤC GÓC (HIỂN THỊ CHỮ THAY VÌ SỐ) ---
        # Dùng QCategoryAxis để hiện chữ "Gốc", "Lãi"... thay vì 0, 72, 144
        angular_axis = QCategoryAxis()
        for i, cat in enumerate(categories):
            angular_axis.append(cat, i) # Gán nhãn tại vị trí i
        angular_axis.append("End", len(categories)) # Điểm kết thúc
        angular_axis.setRange(0, len(categories))
        angular_axis.setLabelsPosition(QCategoryAxis.AxisLabelsPosition.AxisLabelsPositionOnValue)
        
        radar.addAxis(angular_axis, QPolarChart.PolarOrientation.PolarOrientationAngular)
        series.attachAxis(angular_axis)

        # --- TRỤC BÁN KÍNH (ĐỘ LỚN) ---
        radial_axis = QValueAxis()
        radial_axis.setRange(0, 100)
        radial_axis.setLabelFormat("%d")
        radial_axis.setVisible(False) # Ẩn số đi cho đỡ rối, chỉ cần nhìn hình dáng
        radar.addAxis(radial_axis, QPolarChart.PolarOrientation.PolarOrientationRadial)
        series.attachAxis(radial_axis)

        chart_view = QChartView(radar)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(400)
        
        # Thêm chú thích bên cạnh biểu đồ
        container = QFrame()
        container.setStyleSheet(f"background-color: {self.theme['card_bg']}; border-radius: 10px;")
        lo = QVBoxLayout(container)
        lo.addWidget(QLabel("<b>Giải thích biểu đồ:</b>"))
        lo.addWidget(QLabel("- <b>Gốc vay:</b> Quy mô khoản vay."))
        lo.addWidget(QLabel("- <b>Dư nợ:</b> Phần phình ra cho thấy bạn còn nợ nhiều."))
        lo.addWidget(QLabel("- <b>Rủi ro:</b> Dựa trên lãi suất và quá hạn."))
        lo.addStretch()
        lo.addWidget(chart_view)
        
        self.charts_layout.addWidget(container, 0, 0)

    def _total_interest(self, d):
        # (Giữ nguyên logic tính lãi của bạn)
        if d.outstanding() <= 0 or d.interest_rate <= 0: return 0
        days = (date.today() - datetime.fromisoformat(d.start_date).date()).days
        if days <= 0: return 0
        yearly_rate = d.interest_rate / 100
        if d.compound: return d.amount * ((1 + yearly_rate) ** (days / 365) - 1)
        else: return d.amount * yearly_rate * (days / 365)



class DebtManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = DebtEngine()
        self.current_theme = "spring"

        # 1. Khởi tạo giao diện trước
        self.init_ui()

        # 2. Khởi tạo Overlay sau khi có centralWidget
        self.overlay = SeasonalOverlay(self.centralWidget())
        self.overlay.show()
        self.overlay.raise_()

        # 3. Apply theme (cần overlay đã khởi tạo)
        self.apply_theme("spring")

        # 4. Load data & check overdue
        self.refresh()
        self.check_overdue()

    # ------------------- UI BUILD -------------------
    def init_ui(self):
        self.setWindowTitle("Quản Lý Nợ - Module Độc Lập")
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
        self.btn_schedule = self.create_btn("📅 Export lịch trả", self.export_schedule)



        toolbar_lo.addWidget(self.btn_add)
        toolbar_lo.addWidget(self.btn_import)
        toolbar_lo.addWidget(self.btn_export)
        toolbar_lo.addWidget(self.btn_stats)
        toolbar_lo.addWidget(self.btn_schedule)
        toolbar_lo.addStretch()

        # Theme
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["spring", "summer", "autumn", "winter"])
        self.combo_theme.currentTextChanged.connect(self.apply_theme)
        toolbar_lo.addWidget(QLabel("Mùa:"))
        toolbar_lo.addWidget(self.combo_theme)
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

        # Lịch sử trả
        left_lo.addWidget(QLabel("Lịch sử trả gần đây:"))
        self.tab_history = QTableWidget(0, 3)
        self.tab_history.setHorizontalHeaderLabels(["Ngày", "Số tiền", "Còn lại"])
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

    # ------------------- THEME & UTIL -------------------
    def create_btn(self, text, func):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(func)
        btn.setFixedHeight(35)
        return btn

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


    # ------------------- CORE FEATURES -------------------
    def refresh(self):
        s = self.engine.summary()
        self.lbl_owe.setText(f"Cần trả: {s['i_owe']:,.0f} đ")
        self.lbl_receive.setText(f"Cần thu: {s['they_owe']:,.0f} đ")
        self.lbl_net.setText(f"Ròng: {s['net']:,.0f} đ")

        debts = self.engine.get_debts()
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

            # Nút Trả
            btn = QPushButton("Trả")
            btn.clicked.connect(lambda _, id=d.id: self.quick_pay(id))
            self.table.setCellWidget(row, 6, btn)

            # Lãi đến nay
            interest_today = self._daily_interest(d)
            self.table.setItem(row, 7, QTableWidgetItem(f"{interest_today:,.0f}"))

            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, d.id)

        self.update_charts(s)
        self._load_payment_log()

    def check_overdue(self):
        overdue = [d for d in self.engine.get_debts() if d.is_overdue()]
        if overdue:
            names = ", ".join(d.counterparty for d in overdue)
            QMessageBox.warning(
                self, "Nhắc hạn",
                f"Các khoản sau đã quá hạn:\n{names}\n\nVui lòng trả hoặc đàm phán gia hạn!"
            )

    def update_charts(self, s):
        # Pie
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
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setBackgroundVisible(False)
        self.pie_view.setChart(chart)

        # Bar
        bar_set = QBarSet("Còn lại")
        categories = []
        for d in self.engine.get_debts(active_only=True):
            categories.append(d.counterparty)
            bar_set.append(d.outstanding())
        bar_series = QBarSeries()
        bar_series.append(bar_set)
        chart2 = QChart()
        chart2.addSeries(bar_series)
        chart2.setTitle("Chi Tiết Theo Người")
        chart2.setBackgroundVisible(False)
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart2.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)
        self.bar_view.setChart(chart2)

    def export_debt_stats(self):
        debts = self.engine.get_debts()
        if not debts:
            self.stats_output.setHtml("<i>Không có dữ liệu nợ.</i>")
            return

        # Tổng hợp
        total_original   = sum(d.amount for d in debts)
        total_paid       = sum(d.paid_back for d in debts)
        total_outstanding= sum(d.outstanding() for d in debts)
        total_interest   = sum(self._total_interest(d) for d in debts)

        # Phân loại
        i_owe   = sum(d.outstanding() for d in debts if d.side == "IOWE")
        they_owe= sum(d.outstanding() for d in debts if d.side == "THEY_OWE")

        # Quá hạn
        overdue = [d for d in debts if d.is_overdue()]
        overdue_amount = sum(d.outstanding() for d in overdue)

        # Top 5 nợ lớn nhất
        top5 = sorted(debts, key=lambda x: x.outstanding(), reverse=True)[:5]

        # Build HTML
        html = f"""
        <h2>📊 Thống kê nợ</h2>
        <p><b>Tổng gốc:</b> {total_original:,.0f} đ</p>
        <p><b>Đã trả:</b> {total_paid:,.0f} đ</p>
        <p><b>Còn lại:</b> {total_outstanding:,.0f} đ</p>
        <p><b>Lãi tích lũy:</b> {total_interest:,.0f} đ</p>
        <p><b>Tôi phải trả:</b> {i_owe:,.0f} đ</p>
        <p><b>Tôi cần thu:</b> {they_owe:,.0f} đ</p>
        <p><b>Nợ quá hạn:</b> {overdue_amount:,.0f} đ ({len(overdue)} khoản)</p>

        <h3>Top 5 nợ lớn nhất</h3>
        <table border="1" cellpadding="5">
        <tr><th>Đối tác</th><th>Loại</th><th>Còn lại</th><th>Hạn</th></tr>
        """
        for d in top5:
            html += f"<tr><td>{d.counterparty}</td><td>{'Vay' if d.side=='IOWE' else 'Cho vay'}</td><td>{d.outstanding():,.0f} đ</td><td>{d.due_date or '-'}</td></tr>"
        html += "</table>"

        self.stats_output.setHtml(html)

    def _total_interest(self, d: Debt) -> float:
        """Tổng lãi đã phát sinh từ ngày bắt đầu đến nay"""
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



    # ------------------- ACTIONS -------------------
    def add_debt(self):
        form = DebtForm(parent=self, theme_key=self.current_theme)
        if form.exec():
            new_id = self.engine.next_id()
            debt = form.get_debt(new_id)
            self.engine.add_debt(debt)
            self.refresh()

    def edit_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        _id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        debt = next((d for d in self.engine.get_debts() if d.id == _id), None)
        if debt:
            form = DebtForm(debt, parent=self, theme_key=self.current_theme)
            if form.exec():
                updated_debt = form.get_debt(_id)
                self.engine.update_debt(updated_debt)
                self.refresh()

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ Xóa")
        action = menu.exec(self.table.mapToGlobal(pos))
        if action == delete_action:
            _id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            confirm = QMessageBox.question(self, "Xác nhận", "Bạn có chắc muốn xóa khoản này không?")
            if confirm == QMessageBox.StandardButton.Yes:
                self.engine.delete_debt(_id)
                self.refresh()

    def quick_pay(self, debt_id: int):
        debt = next((d for d in self.engine.get_debts() if d.id == debt_id), None)
        if not debt or debt.outstanding() <= 0:
            return
        amount, ok = QInputDialog.getDouble(
            self, "Trả nợ", f"Trả bao nhiêu? (còn {debt.outstanding():,.0f} đ)",
            value=min(1_000_000, debt.outstanding()), min=10_000, max=debt.outstanding()
        )
        if not ok or amount <= 0:
            return
        debt.paid_back += amount
        self.engine.update_debt(debt)

        # ✅ Tự động tạo giao dịch chi tiền
        self._create_repay_transaction(debt, amount)

        self._log_payment(debt_id, amount)
        QMessageBox.information(self, "OK", f"Đã trả {amount:,.0f} đ")
        self.refresh()

    def _log_payment(self, debt_id: int, amount: float):
        log = []
        if PAYMENT_LOG.exists():
            log = json.loads(PAYMENT_LOG.read_text(encoding="utf8"))
        debt = next(d for d in self.engine.get_debts() if d.id == debt_id)
        log.append({
            "debt_id": debt_id,
            "counterparty": debt.counterparty,
            "date": date.today().isoformat(),
            "amount": amount,
            "remain": debt.outstanding()
        })
        log = log[-20:]  # giữ 20 dòng gần nhất
        PAYMENT_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf8")
        self._load_payment_log()

    def _load_payment_log(self):
        if not PAYMENT_LOG.exists():
            return
        log = json.loads(PAYMENT_LOG.read_text(encoding="utf8"))
        self.tab_history.setRowCount(0)
        for entry in log[::-1]:  # mới nhất trước
            row = self.tab_history.rowCount()
            self.tab_history.insertRow(row)
            self.tab_history.setItem(row, 0, QTableWidgetItem(entry["date"]))
            self.tab_history.setItem(row, 1, QTableWidgetItem(f"{entry['amount']:,.0f}"))
            self.tab_history.setItem(row, 2, QTableWidgetItem(f"{entry['remain']:,.0f}"))

    def _daily_interest(self, d: Debt) -> float:
        if d.outstanding() <= 0 or d.interest_rate <= 0:
            return 0
        days = (date.today() - datetime.fromisoformat(d.start_date).date()).days
        if days <= 0:
            return 0
        yearly_rate = d.interest_rate / 100
        if d.compound:
            return d.outstanding() * ((1 + yearly_rate) ** (days / 365) - 1)
        else:
            return d.outstanding() * yearly_rate * (days / 365)
                
    def _selected_debt(self) -> Debt | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        _id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((d for d in self.engine.get_debts() if d.id == _id), None)

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

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file CSV", "", "CSV Files (*.csv)")
        if path:
            self.engine.import_csv(path)
            self.refresh()
            QMessageBox.information(self, "OK", "Import thành công!")

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu file CSV", "", "CSV Files (*.csv)")
        if path:
            self.engine.export_csv(path)
            QMessageBox.information(self, "OK", "Export thành công!")

    def open_stats(self):
        dlg = DebtStatsDialog(self.engine, self, self.current_theme)
        dlg.exec()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay'):
            self.overlay.setGeometry(self.centralWidget().rect())
            if not self.overlay.initialized:
                self.overlay.init_particles()

    def _create_repay_transaction(self, debt: Debt, amount: float):
        #TODO
        """
        Tự động tạo 1 giao dịch CHI TIỀN trong module Transaction
        """
        # Giả sử bạn có hàm tạo Transaction ở module Transaction
        from core._transaction import Transaction, DATA_FILE as TRANS_FILE

        new_id = f"R{random.randint(10000, 99999)}"
        trans = Transaction(
            id=new_id,
            date=date.today().isoformat(),
            category="Trả nợ",
            amount=amount,
            type="expense",
            role="Tôi" if debt.side == "IOWE" else debt.counterparty,
            description=f"Trả nợ {debt.counterparty} – {debt.purpose}",
            expiry_date="",
            is_recurring=False
        )

        # Đọc danh sách hiện tại, append, save
        transactions = []
        if TRANS_FILE.exists():
            import csv
            with open(TRANS_FILE, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                transactions = [
                    Transaction(
                        row["id"], row["date"], row["category"],
                        float(row["amount"]), row["type"], row["role"],
                        row["description"], row["expiry_date"],
                        row["is_recurring"].lower() == "true"
                    )
                    for row in reader
                ]
        transactions.append(trans)
        with open(TRANS_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "category", "amount", "type", "role", "description", "expiry_date", "is_recurring"])
            for t in transactions:
                writer.writerow([t.id, t.date, t.category, t.amount, t.type, t.role, t.description, t.expiry_date, t.is_recurring])

        # Thông báo nhẹ
        QMessageBox.information(self, "Tự động", f"Đã ghi giao dịch chi {amount:,.0f} đ vào Transaction!")


    def export_debt_stats(self):
        html = self.stats_output.toHtml()  # đã có ở bước 2
        path, _ = QFileDialog.getSaveFileName(self, "Lưu báo cáo nợ", "debt_report.csv", "CSV (*.csv)")
        if not path:
            return
        debts = self.engine.get_debts()
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Đối tác", "Loại", "Gốc", "Đã trả", "Còn lại", "Lãi %", "Hạn", "Lãi tích lũy"])
            for d in debts:
                writer.writerow([
                    d.counterparty,
                    "Vay" if d.side == "IOWE" else "Cho vay",
                    d.amount,
                    d.paid_back,
                    d.outstanding(),
                    d.interest_rate,
                    d.due_date or "-",
                    int(self._total_interest(d))
                ])
        QMessageBox.information(self, "OK", f"Đã xuất báo cáo:\n{path}")
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = DebtManager()
    win.show()
    sys.exit(app.exec())