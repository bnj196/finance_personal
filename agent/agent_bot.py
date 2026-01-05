
import sys, random, math

from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *

from .agent_api import BotChatAgentAPI          # module bạn đã setup xong
from core.data_manager import DataManager

class LLMWorker(QThread):
    """Chạy ở thread riêng, phát từng token về GUI"""
    newToken = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(qtl, prompt: str, agent: BotChatAgentAPI):
        super().__init__()
        qtl.prompt = prompt
        qtl.agent = agent

    def run(qtl):
        
        for tok in qtl.agent.stream_tokens(qtl.prompt):   # yield từng phần
            qtl.newToken.emit(tok)
        qtl.finished.emit()


# --------------- Theme / Particle (giữ nguyên code bạn) ---------------
THEMES = {
    "spring": {
        "name": "Xuân (Tết)", "sidebar_bg": "#b30000", "sidebar_border": "#FFD700",
        "content_bg": "#FFF8E1", "text_color": "#5D4037", "accent_color": "#FFD700",
        "btn_hover": "rgba(255, 215, 0, 0.2)",
        "user_bubble": "#FFCDD2", "bot_bubble": "#FFFFFF", "icon": "🌸"
    },
    "summer": {
        "name": "Hạ (Biển Xanh)", "sidebar_bg": "#0277BD", "sidebar_border": "#4FC3F7",
        "content_bg": "#E1F5FE", "text_color": "#01579B", "accent_color": "#E0F7FA",
        "btn_hover": "rgba(79, 195, 247, 0.3)",
        "user_bubble": "#B3E5FC", "bot_bubble": "#FFFFFF", "icon": "🏖️"
    },
    "autumn": {
        "name": "Thu (Lá Vàng)", "sidebar_bg": "#E65100", "sidebar_border": "#FFB74D",
        "content_bg": "#FFF3E0", "text_color": "#3E2723", "accent_color": "#FFCC80",
        "btn_hover": "rgba(255, 183, 77, 0.3)",
        "user_bubble": "#FFCCBC", "bot_bubble": "#FFFFFF", "icon": "🍁"
    },
    "winter": {
        "name": "Đông (Băng Giá)", "sidebar_bg": "#263238", "sidebar_border": "#B0BEC5",
        "content_bg": "#ECEFF1", "text_color": "#37474F", "accent_color": "#FFFFFF",
        "btn_hover": "rgba(176, 190, 197, 0.3)",
        "user_bubble": "#CFD8DC", "bot_bubble": "#FFFFFF", "icon": "❄️"
    }
}


class Particle:
    def __init__(qtl, w, h, mode="spring"):
        qtl.mode = mode
        qtl.reset(w, h, first_time=True)

    def reset(qtl, w, h, first_time=False):
        qtl.x = random.uniform(0, w)
        qtl.size = random.uniform(5, 15)
        qtl.rotation = random.uniform(0, 360)
        qtl.rotation_speed = random.uniform(-2, 2)

        if qtl.mode == "spring":
            qtl.y = random.uniform(-h, 0) if not first_time else random.uniform(0, h)
            qtl.speed_y = random.uniform(1, 3)
            qtl.drift = random.uniform(-0.5, 0.5)
            qtl.color = QColor("#FFD700") if random.choice([True, False]) else QColor("#FFB7C5")
            qtl.shape = "flower"
            qtl.size = random.uniform(10, 20)
        elif qtl.mode == "summer":
            qtl.y = h + random.uniform(0, 100) if not first_time else random.uniform(0, h)
            qtl.speed_y = random.uniform(-1, -3)
            qtl.drift = random.uniform(-0.2, 0.2)
            qtl.color = QColor(255, 255, 255, 100)
            qtl.shape = "bubble"
            qtl.size = random.uniform(5, 15)
        elif qtl.mode == "autumn":
            qtl.y = random.uniform(-h, 0) if not first_time else random.uniform(0, h)
            qtl.speed_y = random.uniform(1, 2)
            qtl.drift = random.uniform(-1, 1)
            qtl.color = random.choice([QColor("#D84315"), QColor("#F9A825"), QColor("#6D4C41")])
            qtl.shape = "leaf"
            qtl.size = random.uniform(12, 22)
        elif qtl.mode == "winter":
            qtl.y = random.uniform(-h, 0) if not first_time else random.uniform(0, h)
            qtl.speed_y = random.uniform(2, 5)
            qtl.drift = 0
            qtl.color = QColor("#FFFFFF")
            qtl.shape = "snow"
            qtl.size = random.uniform(3, 6)

        qtl.path = QPainterPath()
        if qtl.shape == "flower":
            qtl.create_flower_path()
        elif qtl.shape == "leaf":
            qtl.create_leaf_path()

    def create_flower_path(qtl):
        center = QPointF(0, 0)
        petal_radius = qtl.size / 2
        for i in range(5):
            angle = math.radians(i * 72)
            tip = QPointF(center.x() + petal_radius * math.cos(angle),
                          center.y() + petal_radius * math.sin(angle))
            ctrl1 = QPointF(center.x() + petal_radius * 0.6 * math.cos(angle - 0.3),
                            center.y() + petal_radius * 0.6 * math.sin(angle - 0.3))
            ctrl2 = QPointF(center.x() + petal_radius * 0.6 * math.cos(angle + 0.3),
                            center.y() + petal_radius * 0.6 * math.sin(angle + 0.3))
            if i == 0:
                qtl.path.moveTo(center)
            qtl.path.cubicTo(ctrl1, tip, ctrl2)
        qtl.path.closeSubpath()

    def create_leaf_path(qtl):
        qtl.path.moveTo(0, -qtl.size / 2)
        qtl.path.lineTo(qtl.size / 3, 0)
        qtl.path.lineTo(0, qtl.size / 2)
        qtl.path.lineTo(-qtl.size / 3, 0)
        qtl.path.closeSubpath()

    def update(qtl, w, h):
        qtl.y += qtl.speed_y
        qtl.x += qtl.drift
        if qtl.shape in ("leaf", "flower"):
            qtl.x += math.sin(qtl.y / 50) * 0.5
        qtl.rotation += qtl.rotation_speed
        if (qtl.speed_y > 0 and qtl.y > h + 20) or (qtl.speed_y < 0 and qtl.y < -20):
            qtl.reset(w, h)
        if qtl.x < -20 or qtl.x > w + 20:
            qtl.reset(w, h)


class SeasonalOverlay(QWidget):
    def __init__(qtl, parent=None):
        super().__init__(parent)
        qtl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        qtl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        qtl.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        qtl.particles = []
        qtl.current_season = "spring"
        qtl.timer = QTimer(qtl)
        qtl.timer.timeout.connect(qtl.update_animation)
        qtl.initialized = False

    def set_season(qtl, season):
        qtl.current_season = season
        qtl.particles = []
        qtl.init_particles()

    def init_particles(qtl):
        if qtl.width() > 0:
            count = 60 if qtl.current_season != "winter" else 150
            qtl.particles = [Particle(qtl.width(), qtl.height(), qtl.current_season)
                              for _ in range(count)]
            if not qtl.timer.isActive():
                qtl.timer.start(16)
            qtl.initialized = True

    def update_animation(qtl):
        w, h = qtl.width(), qtl.height()
        for p in qtl.particles:
            p.update(w, h)
        qtl.update()

    def paintEvent(qtl, event):
        painter = QPainter(qtl)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for p in qtl.particles:
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rotation)

            if p.shape == "bubble":
                painter.setPen(QPen(p.color, 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(0, 0), p.size / 2, p.size / 2)
            elif p.shape == "snow":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(p.color))
                painter.drawEllipse(QPointF(0, 0), p.size / 2, p.size / 2)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(p.color))
                painter.drawPath(p.path)

            painter.restore()


class ChatBubble(QFrame):
    def __init__(qtl, text, is_user=False, theme_key="spring"):
        super().__init__()
        qtl.is_user = is_user
        qtl.theme_key = theme_key

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        qtl.setLayout(layout)

        qtl.lbl_text = QLabel(text)
        qtl.lbl_text.setWordWrap(True)
        qtl.lbl_text.setFont(QFont("Segoe UI", 11))
        layout.addWidget(qtl.lbl_text)

        qtl.setMaximumWidth(400)
        qtl.apply_style()

    def apply_style(qtl):
        theme = THEMES[qtl.theme_key]
        bg_color = theme['user_bubble'] if qtl.is_user else theme['bot_bubble']
        text_color = theme['text_color']
        border_color = theme['sidebar_border']

        radius = "15px 15px 0px 15px" if qtl.is_user else "15px 15px 15px 0px"
        align = "margin-left: auto;" if qtl.is_user else "margin-right: auto;"

        qtl.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 15px;
                border-bottom-right-radius: {0 if qtl.is_user else 15}px;
                border-bottom-left-radius: {15 if qtl.is_user else 0}px;
                {align}
            }}
            QLabel {{
                border: none;
                color: {text_color};
                background-color: transparent;
            }}
        """)


# --------------- Main Chat Window ---------------
class BotChatAgent(QMainWindow):
    def __init__(qtl, start_season="spring"):
        super().__init__()
        qtl.setWindowTitle("AI Assistant")
        qtl.resize(450, 700)
        qtl.current_season = start_season
        qtl.data_manager = DataManager.instance()

        # ---- GUI skeleton (giữ nguyên) ----
        qtl.central_widget = QWidget()
        qtl.setCentralWidget(qtl.central_widget)
        qtl.main_layout = QVBoxLayout(qtl.central_widget)
        qtl.main_layout.setContentsMargins(0, 0, 0, 0)
        qtl.main_layout.setSpacing(0)

        # 1. Header
        qtl.header = QFrame()
        qtl.header.setFixedHeight(60)
        qtl.header_layout = QHBoxLayout(qtl.header)
        qtl.lbl_title = QLabel("🌸 AI Assistant")
        qtl.lbl_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        qtl.btn_theme = QPushButton("Đổi Mùa 🎨")
        qtl.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        qtl.btn_theme.clicked.connect(qtl.rotate_theme)
        qtl.header_layout.addWidget(qtl.lbl_title)
        qtl.header_layout.addStretch()
        qtl.header_layout.addWidget(qtl.btn_theme)
        qtl.main_layout.addWidget(qtl.header)

        # 2. Chat scroll
        qtl.scroll_area = QScrollArea()
        qtl.scroll_area.setWidgetResizable(True)
        qtl.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        qtl.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        qtl.chat_container = QWidget()
        qtl.chat_layout = QVBoxLayout(qtl.chat_container)
        qtl.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        qtl.chat_layout.setSpacing(15)
        qtl.chat_layout.setContentsMargins(15, 20, 15, 20)
        qtl.scroll_area.setWidget(qtl.chat_container)
        qtl.main_layout.addWidget(qtl.scroll_area)

        # 3. Input
        qtl.input_frame = QFrame()
        qtl.input_frame.setFixedHeight(80)
        qtl.input_layout = QHBoxLayout(qtl.input_frame)
        qtl.input_layout.setContentsMargins(10, 10, 10, 10)
        qtl.txt_input = QLineEdit()
        qtl.txt_input.setPlaceholderText("Nhập tin nhắn...")
        qtl.txt_input.setFixedHeight(45)
        qtl.txt_input.returnPressed.connect(qtl.send_message)
        qtl.btn_send = QPushButton("➤")
        qtl.btn_send.setFixedSize(50, 45)
        qtl.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        qtl.btn_send.clicked.connect(qtl.send_message)
        qtl.input_layout.addWidget(qtl.txt_input)
        qtl.input_layout.addWidget(qtl.btn_send)
        qtl.main_layout.addWidget(qtl.input_frame)

        # 4. Particle overlay
        qtl.overlay = SeasonalOverlay(qtl)
        qtl.overlay.raise_()

        # ---- apply theme & greeting ----
        qtl.llm_agent = BotChatAgentAPI()
        qtl.apply_theme(start_season)
        QTimer.singleShot(500, lambda: qtl.add_message(
            "Xin chào! Tôi là trợ lý ảo AI. Bạn cần giúp gì hôm nay?", False))


    def _build_rag_context(self) -> str:
            """Tạo ngữ cảnh RAG từ toàn bộ dữ liệu người dùng"""
            try:
                summary = self.data_manager.get_dashboard_summary()
                trans_list = summary.get("recent_transactions", [])[:3]
                debts = self.data_manager.debts
                funds = self.data_manager.funds
                goals = self.data_manager.goals

                # Tạo context dạng văn bản có cấu trúc
                ctx = "=== CONTEXT TÀI CHÍNH NGƯỜI DÙNG (CẬP NHẬT THỰC TẾ) ===\n"

                # Tổng quan
                ctx += f"- Số dư hiện tại: {summary['balance']:,.0f}đ\n"
                ctx += f"- Thu nhập tháng này: {summary['income']:,.0f}đ\n"
                ctx += f"- Chi tiêu tháng này: {summary['expense']:,.0f}đ\n"
                ctx += f"- Tài sản ròng: {summary['net_worth']:,.0f}đ\n"
                ctx += f"- Tiền tiết kiệm (hũ): {summary['savings']:,.0f}đ\n"

                # Nợ
                if debts:
                    ctx += "- NỢ:\n"
                    for d in debts:
                        ctx += f"  • {getattr(d, 'name', 'Ẩn danh')}: {getattr(d, 'amount', 0):,.0f}đ ({'Tôi nợ' if getattr(d, 'is_ower', True) else 'Họ nợ tôi'})\n"

                # Hũ tiết kiệm
                if funds:
                    ctx += "- HŨ TIẾT KIỆM:\n"
                    for f in funds:
                        ctx += f"  • {getattr(f, 'name', 'Không tên')}: {getattr(f, 'current', 0):,.0f}đ / {getattr(f, 'target', 0):,.0f}đ\n"

                # Mục tiêu nhóm
                if goals:
                    ctx += "- MỤC TIÊU NHÓM:\n"
                    for g in goals:
                        ctx += f"  • {getattr(g, 'title', 'Không tên')}: {getattr(g, 'current', 0):,.0f}đ / {getattr(g, 'target', 0):,.0f}đ\n"

                # Giao dịch gần đây
                if trans_list:
                    ctx += "- GIAO DỊCH GẦN ĐÂY:\n"
                    for t in trans_list:
                        d = t.get('date', '???')
                        c = t.get('category', 'Khác')
                        a = t.get('amount', 0)
                        ty = t.get('type', 'unknown')
                        sign = "-" if ty == "expense" else "+"
                        ctx += f"  • [{d}] {c}: {sign}{a:,.0f}đ\n"

                ctx += "=== HẾT CONTEXT ===\n"
                return ctx
            except Exception as e:
                print(f"⚠️ Lỗi khi tạo RAG context: {e}")
                return "=== CONTEXT TẠM THỜI KHÔNG CÓ DỮ LIỆU ===\n"


    # -------- theme handling --------
    def rotate_theme(qtl):
        seasons = list(THEMES.keys())
        idx = seasons.index(qtl.current_season)
        next_season = seasons[(idx + 1) % len(seasons)]
        qtl.apply_theme(next_season)

    def apply_theme(qtl, season_name):
        qtl.current_season = season_name
        theme = THEMES[season_name]
        qtl.overlay.set_season(season_name)

        qtl.header.setStyleSheet(f"""
            background-color: {theme['sidebar_bg']};
            border-bottom: 2px solid {theme['sidebar_border']};
        """)
        qtl.lbl_title.setText(f"{theme['icon']} AI Assistant – {theme['name']}")
        qtl.lbl_title.setStyleSheet(f"color: {theme['accent_color']}; font-weight: bold; font-size: 16px;")

        qtl.btn_theme.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255,255,255,0.2);
                color: {theme['accent_color']};
                border: 1px solid {theme['sidebar_border']};
                border-radius: 5px; padding: 5px;
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.4); }}
        """)

        qtl.chat_container.setStyleSheet("background-color: transparent;")
        qtl.scroll_area.setStyleSheet(f"background-color: {theme['content_bg']}; border: none;")

        qtl.input_frame.setStyleSheet(f"background-color: white; border-top: 1px solid {theme['sidebar_border']};")
        qtl.txt_input.setStyleSheet(f"""
            border: 2px solid {theme['sidebar_bg']};
            border-radius: 20px; padding-left: 15px; font-size: 14px;
            color: {theme['text_color']};
        """)
        qtl.btn_send.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['sidebar_bg']};
                color: {theme['accent_color']};
                border-radius: 22px; font-size: 20px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {theme['sidebar_border']}; }}
        """)

        # refresh old bubbles
        for i in range(qtl.chat_layout.count()):
            item = qtl.chat_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), ChatBubble):
                item.widget().theme_key = season_name
                item.widget().apply_style()

    # -------- resize & painting --------
    def resizeEvent(qtl, event):
        super().resizeEvent(event)
        qtl.overlay.setGeometry(qtl.rect())
        if not qtl.overlay.initialized:
            qtl.overlay.init_particles()

    # -------- message handling --------
    def send_message(qtl):
        text = qtl.txt_input.text().strip()
        if not text:
            return
        qtl.add_message(text, True)
        qtl.txt_input.clear()
        # gọi LLM thật
        qtl.stream_llm_response(text)

    def add_message(qtl, text, is_user):
        bubble = ChatBubble(text, is_user, qtl.current_season)
        h_layout = QHBoxLayout()
        if is_user:
            h_layout.addStretch()
            h_layout.addWidget(bubble)
        else:
            h_layout.addWidget(bubble)
            h_layout.addStretch()
        container = QWidget()
        container.setLayout(h_layout)
        qtl.chat_layout.addWidget(container)
        # scroll bottom
        QTimer.singleShot(10, lambda: qtl.scroll_area.verticalScrollBar().setValue(
            qtl.scroll_area.verticalScrollBar().maximum()))

    def update_theme(qtl, season_name): qtl.apply_theme(season_name)
    # -------- LLM streaming (thay thế fake_llm_response) --------
    def stream_llm_response(qtl, user_text):
        rag_context = {
            "context": qtl._build_rag_context(),
            "user_input": user_text
        }

        # 1) tạo worker & thread
        qtl._llm_thread = QThread()
        qtl._worker = LLMWorker(str(rag_context), qtl.llm_agent)
        qtl._worker.moveToThread(qtl._llm_thread)

        # 2) nối signal
        qtl._llm_thread.started.connect(qtl._worker.run)
        qtl._worker.newToken.connect(qtl._append_token)
        qtl._worker.finished.connect(qtl._on_llm_finished)

        # 3) khởi chạy
        qtl._llm_thread.start()

    # ---- slot: nối token vào bubble cuối ----
    def _append_token(qtl, tok: str):
        lay = qtl.chat_layout
        if lay.count() == 0:
            return
        last_container = lay.itemAt(lay.count() - 1).widget()
        bubble = last_container.layout().itemAt(0).widget()
        if not isinstance(bubble, ChatBubble) or bubble.is_user:
            # chưa có bubble bot -> tạo mới
            qtl.add_message(tok, False)
        else:
            # nối token vào label có sẵn
            cur = bubble.lbl_text.text()
            bubble.lbl_text.setText(cur + tok)
            # tự động scroll theo dõi
            qtl.scroll_area.verticalScrollBar().setValue(
                qtl.scroll_area.verticalScrollBar().maximum())

    # ---- slot: dọn dẹp thread ----
    def _on_llm_finished(qtl):
        qtl._llm_thread.quit()
        qtl._llm_thread.wait()
        qtl._llm_thread.deleteLater()
        qtl._worker.deleteLater()


# --------------- run ---------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = BotChatAgent("spring")
    win.show()
    sys.exit(app.exec())