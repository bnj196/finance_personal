import sys
import datetime
import random
import math
import os
from pathlib import Path

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# --- IMPORT CORE ---
from core.data_manager import DataManager 

# --- 1. THƯ VIỆN BỔ TRỢ ---
try:
    from lunardate import LunarDate
    HAS_LUNAR = True
except ImportError:
    HAS_LUNAR = False
    print("⚠️ Chưa cài 'lunardate'.")

# --- 2. GOOGLE API ---
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False
    print("⚠️ Chưa cài thư viện Google.")

# --- CẤU HÌNH GOOGLE (File JSON vẫn ở local của App này) ---
BASE_DIR = Path(__file__).parent
FILE_TOKEN = BASE_DIR / 'token.json'
FILE_CRED  = BASE_DIR / 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# --- THEMES CONFIG ---
THEMES = {
    "spring": {"name": "Xuân", "bg": "#FFF8E1", "sec": "#b30000", "acc": "#FFD700", "txt": "#5D4037", "btn": "#d91e18"},
    "summer": {"name": "Hạ", "bg": "#E1F5FE", "sec": "#0277BD", "acc": "#4FC3F7", "txt": "#01579B", "btn": "#0288d1"},
    "autumn": {"name": "Thu", "bg": "#FFF3E0", "sec": "#E65100", "acc": "#FFB74D", "txt": "#3E2723", "btn": "#f57c00"},
    "winter": {"name": "Đông", "bg": "#ECEFF1", "sec": "#263238", "acc": "#90A4AE", "txt": "#37474F", "btn": "#455A64"}
}

# ======================
# 3. HELPER FUNCTIONS
# ======================
def format_money(val):
    try: return f"{int(val):,}"
    except: return "0"

def get_lunar_string(date_obj):
    if HAS_LUNAR:
        try:
            lunar = LunarDate.fromSolarDate(date_obj.year, date_obj.month, date_obj.day)
            return f"{lunar.day}/{lunar.month}"
        except: pass
    return ""

# ======================
# 4. GOOGLE SERVICE (Giữ nguyên logic của bạn)
# ======================
class GoogleService:
    def __init__(self):
        self.service = None
        self.creds = None

    def authenticate(self):
        if not HAS_GOOGLE: return False, "Thiếu thư viện Google"
        try:
            if os.path.exists(FILE_TOKEN):
                self.creds = Credentials.from_authorized_user_file(str(FILE_TOKEN), SCOPES)
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(FILE_CRED):
                        return False, "Thiếu file credentials.json"
                    flow = InstalledAppFlow.from_client_secrets_file(str(FILE_CRED), SCOPES)
                    self.creds = flow.run_local_server(port=0)
                with open(FILE_TOKEN, "w") as token:
                    token.write(self.creds.to_json())
            self.service = build("calendar", "v3", credentials=self.creds)
            return True, "Đã kết nối Google"
        except Exception as e:
            return False, str(e)

    def fetch_events(self, date_str):
        if not self.service: return []
        start = f"{date_str}T00:00:00Z"
        end   = f"{date_str}T23:59:59Z"
        try:
            res = self.service.events().list(calendarId='primary', timeMin=start, timeMax=end,
                                            singleEvents=True, orderBy='startTime').execute()
            return res.get('items', [])
        except: return []

    def create_event(self, summary, start_dt, end_dt, description, popup_min, email_min):
        if not self.service: return False, "Chưa đăng nhập Google"
        overrides = []
        if popup_min is not None: overrides.append({'method': 'popup', 'minutes': int(popup_min)})
        if email_min is not None: overrides.append({'method': 'email', 'minutes': int(email_min)})

        body = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Ho_Chi_Minh'},
            'end':   {'dateTime': end_dt.isoformat(),   'timeZone': 'Asia/Ho_Chi_Minh'},
            'reminders': {'useDefault': False, 'overrides': overrides}
        }
        try:
            self.service.events().insert(calendarId='primary', body=body).execute()
            return True, "Đã thêm sự kiện lên Google"
        except Exception as e:
            return False, str(e)

    def remove_event(self, event_id):
        if not self.service: return False
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return True
        except: return False

# ======================
# 5. WORKERS
# ======================
class SyncWorker(QThread):
    data_received = pyqtSignal(list)
    def __init__(self, svc, date_str): super().__init__(); self.svc, self.date = svc, date_str
    def run(self): self.data_received.emit(self.svc.fetch_events(self.date))

class PushWorker(QThread):
    finished = pyqtSignal(bool, str)
    def __init__(self, svc, summary, start, end, desc, popup_min, email_min):
        super().__init__()
        self.svc, self.s, self.st, self.en, self.desc = svc, summary, start, end, desc
        self.popup_min, self.email_min = popup_min, email_min
    def run(self):
        ok, msg = self.svc.create_event(self.s, self.st, self.en, self.desc, self.popup_min, self.email_min)
        self.finished.emit(ok, msg)

class DeleteWorker(QThread):
    finished = pyqtSignal(bool)
    def __init__(self, svc, eid): super().__init__(); self.svc, self.eid = svc, eid
    def run(self): self.finished.emit(self.svc.remove_event(self.eid))

# ======================
# 6. VISUAL EFFECTS (Giữ nguyên vì đẹp)
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
        elif self.mode == "summer":
             self.y = h if not first else random.uniform(0, h); self.speed_y = random.uniform(-3, -1); self.drift = random.uniform(-0.2, 0.2)
             self.color = QColor(255, 255, 255, 100); self.shape = "circle"
        elif self.mode == "autumn":
            self.y = random.uniform(-h, 0) if not first else random.uniform(0, h)
            self.speed_y = random.uniform(1, 2); self.drift = random.uniform(0.5, 1.5)
            self.color = QColor("#D35400"); self.shape = "circle"
        else:
            self.y = random.uniform(-h, 0); self.speed_y = 3; self.drift = 0
            self.color = QColor("white"); self.shape = "circle"
        self.path = QPainterPath()
        if self.shape == "flower": self.create_flower()
    def create_flower(self):
        c, r = QPointF(0, 0), self.size/2
        for i in range(5):
            a = math.radians(i*72); t = QPointF(c.x()+r*math.cos(a), c.y()+r*math.sin(a))
            c1 = QPointF(c.x()+r*0.6*math.cos(a-0.3), c.y()+r*0.6*math.sin(a-0.3))
            c2 = QPointF(c.x()+r*0.6*math.cos(a+0.3), c.y()+r*0.6*math.sin(a+0.3))
            if i == 0: self.path.moveTo(c)
            self.path.cubicTo(c1, t, c2)
        self.path.closeSubpath()
    def update(self, w, h):
        self.y += self.speed_y; self.x += self.drift + math.sin(self.y/50)*0.5; self.rotation += self.speed_rot
        if self.speed_y > 0 and self.y > h + 20: self.reset(w, h)
        if self.speed_y < 0 and self.y < -20: self.reset(w, h)

class SeasonalOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.particles = []; self.current = "spring"; self.timer = QTimer(self); self.timer.timeout.connect(self.anim); self.initialized = False
    def set_season(self, s): self.current = s; self.init_particles()
    def init_particles(self):
        if self.width() > 0:
            self.particles = [Particle(self.width(), self.height(), self.current) for _ in range(40)]
            if not self.timer.isActive(): self.timer.start(25)
            self.initialized = True
    def anim(self): w, h = self.width(), self.height(); [p.update(w, h) for p in self.particles]; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for pt in self.particles:
            p.save(); p.translate(pt.x, pt.y); p.rotate(pt.rotation); p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(pt.color))
            if pt.shape == "flower": p.drawPath(pt.path)
            else: p.drawEllipse(QPointF(0, 0), pt.size/2, pt.size/2)
            p.restore()

# ======================
# 7. UI COMPONENTS
# ======================
class CalendarCell(QFrame):
    clicked = pyqtSignal(str)
    def __init__(self, date_obj, data, theme, is_today=False):
        super().__init__()
        self.date_str = date_obj.strftime("%Y-%m-%d"); self.theme = theme; self.is_today = is_today; self.is_selected = False
        self.setFixedSize(110, 90); self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self); lay.setContentsMargins(4, 4, 4, 4); lay.setSpacing(1)
        
        top = QHBoxLayout(); lbl_day = QLabel(str(date_obj.day)); lbl_day.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        if date_obj.weekday() == 6: lbl_day.setStyleSheet("color:#D32F2F;")
        top.addWidget(lbl_day)
        if data.get('has_event'): top.addWidget(self.dot("#1976D2", "Google"))
        if data.get('has_trans'): top.addWidget(self.dot("#9C27B0", "TC"))
        if data.get('has_debt'): top.addWidget(self.dot("#E64A19", "Nợ"))
        top.addStretch(); lay.addLayout(top)
        
        mid = QHBoxLayout(); mid.setSpacing(1)
        if data.get('has_note'): mid.addWidget(self.dot("#795548", "Note"))
        if data.get('has_todo'): mid.addWidget(self.dot("#388E3C", "Mua sắm"))
        mid.addStretch(); lay.addLayout(mid); lay.addStretch()
        
        lunar = data.get('lunar', '')
        if lunar:
            l = QLabel(lunar); style = "color:#C2185B;font-weight:bold;" if lunar.startswith("1/") or lunar.startswith("15/") else "color:gray;"
            l.setStyleSheet(f"{style}font-size:9px;"); l.setAlignment(Qt.AlignmentFlag.AlignRight); lay.addWidget(l)
        self.update_style()
    def dot(self, color, tip): l = QLabel("●"); l.setToolTip(tip); l.setStyleSheet(f"color:{color};font-size:9px;margin-left:1px;"); return l
    def set_selected(self, val): self.is_selected = val; self.update_style()
    def update_style(self):
        bg, border, width = "white", self.theme['acc'], "1px"
        if self.is_today: bg, border = "#E3F2FD", self.theme['sec']
        if self.is_selected: bg, border, width = "#FFF9C4", "#E91E63", "2px"
        self.setStyleSheet(f"QFrame {{ background-color:{bg}; border:{width} solid {border}; border-radius:8px; }} QFrame:hover {{ border:2px solid {self.theme['sec']}; }}")
    def mousePressEvent(self, e): self.clicked.emit(self.date_str)

class EventItemWidget(QWidget):
    def __init__(self, title, sub, icon, color, eid=None):
        super().__init__(); self.eid = eid
        lay = QHBoxLayout(self); lay.setContentsMargins(5,5,5,5)
        lbl_ic = QLabel(icon); lbl_ic.setStyleSheet("font-size:16px;")
        v = QVBoxLayout(); t = QLabel(title); t.setStyleSheet(f"font-weight:bold;color:{color};"); s = QLabel(sub); s.setStyleSheet("color:#666;font-size:10px;")
        v.addWidget(t); v.addWidget(s); lay.addWidget(lbl_ic); lay.addLayout(v); lay.addStretch()
        self.setStyleSheet("background:rgba(255,255,255,0.7); border-radius:5px; margin-bottom:2px;")

class QuickGoogleDialog(QDialog):
    def __init__(self, parent, date_str, def_title="", def_desc=""):
        super().__init__(parent)
        self.setWindowTitle(f"Push Google - {date_str}"); self.setFixedSize(400, 280)
        lay = QFormLayout(self)
        self.inp_title = QLineEdit(def_title); self.inp_title.setPlaceholderText("Tiêu đề")
        self.inp_desc  = QLineEdit(def_desc); self.inp_desc.setPlaceholderText("Mô tả")
        now = QTime.currentTime()
        self.t_start = QTimeEdit(now.addSecs(300)); self.t_end = QTimeEdit(now.addSecs(3900))
        self.sb_pop = QSpinBox(); self.sb_pop.setValue(10); self.sb_pop.setSuffix(" phút"); self.sb_pop.setRange(-1, 1440)
        self.sb_mail= QSpinBox(); self.sb_mail.setValue(-1); self.sb_mail.setSuffix(" phút"); self.sb_mail.setSpecialValueText("Tắt"); self.sb_mail.setRange(-1, 1440)
        lay.addRow("Tiêu đề:", self.inp_title); lay.addRow("Mô tả:", self.inp_desc)
        lay.addRow("Bắt đầu:", self.t_start); lay.addRow("Kết thúc:", self.t_end)
        lay.addRow("Popup:", self.sb_pop); lay.addRow("Email:", self.sb_mail)
        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn.accepted.connect(self.accept); btn.rejected.connect(self.reject); lay.addRow(btn)
    def get_data(self): return self.inp_title.text(), self.t_start.time(), self.t_end.time(), self.inp_desc.text(), self.sb_pop.value(), self.sb_mail.value()

# ======================
# 8. MAIN CALENDAR MANAGER (REFACTORED)
# ======================
class CalendarMgr(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ultimate Calendar Manager v4.0 (Connected)")
        self.resize(1280, 850)
        
        # --- KẾT NỐI DATA MANAGER ---
        self.data_mgr = DataManager.instance()
        # Khi DataManager báo có thay đổi (từ bất kỳ đâu), reload lịch và chi tiết
        self.data_mgr.data_changed.connect(self.reload_calendar)
        self.data_mgr.data_changed.connect(lambda: self.load_details(self.sel_date))
        
        self.google_svc = GoogleService()
        self.curr_date = datetime.date.today().replace(day=1)
        self.sel_date = datetime.date.today().isoformat()
        self.google_cache = {}
        self.cells = []
        self.current_theme = "spring"
        
        self.init_ui()
        self.overlay = SeasonalOverlay(self.centralWidget()); self.overlay.show(); self.overlay.raise_()
        self.apply_theme("spring")

    def init_ui(self):
        w = QWidget(); self.setCentralWidget(w); main = QHBoxLayout(w)
        left = QFrame(); left.setObjectName("panel_left"); left_l = QVBoxLayout(left)
        nav = QHBoxLayout()
        btn_prev = QPushButton("◀"); btn_prev.clicked.connect(lambda: self.change_month(-1))
        self.lbl_my = QLabel(); self.lbl_my.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        btn_next = QPushButton("▶"); btn_next.clicked.connect(lambda: self.change_month(1))
        self.cmb_theme = QComboBox(); self.cmb_theme.addItems(list(THEMES.keys())); self.cmb_theme.currentTextChanged.connect(self.apply_theme)
        nav.addWidget(btn_prev); nav.addWidget(self.lbl_my); nav.addWidget(btn_next); nav.addStretch(); nav.addWidget(self.cmb_theme)
        left_l.addLayout(nav)
        self.grid = QGridLayout(); left_l.addLayout(self.grid); left_l.addStretch()
        main.addWidget(left, 2)
        
        right = QFrame(); right.setObjectName("panel_right"); right_l = QVBoxLayout(right)
        self.lbl_detail = QLabel("Chi tiết"); self.lbl_detail.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.btn_sync = QPushButton("🔄 Đồng bộ Google"); self.btn_sync.clicked.connect(self.sync_google)
        
        self.tabs = QTabWidget()
        self.lst_evt = QListWidget(); self.lst_evt.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.lst_evt.customContextMenuRequested.connect(self.ctx_evt)
        self.lst_not = QListWidget(); self.lst_not.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.lst_not.customContextMenuRequested.connect(self.ctx_not)
        self.lst_tod = QListWidget(); self.lst_tod.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.lst_tod.customContextMenuRequested.connect(self.ctx_tod)
        self.tabs.addTab(self.lst_evt, "Tài chính & Sự kiện"); self.tabs.addTab(self.lst_not, "Ghi chú"); self.tabs.addTab(self.lst_tod, "Mua sắm")
        
        grp_n = QGroupBox("Ghi chú nhanh"); gl1 = QHBoxLayout(grp_n)
        self.inp_n = QLineEdit(); self.inp_n.setPlaceholderText("Nội dung...")
        btn_n = QPushButton("Lưu"); btn_n.clicked.connect(self.add_note)
        gl1.addWidget(self.inp_n); gl1.addWidget(btn_n)
        
        grp_t = QGroupBox("Thêm mua sắm"); gl2 = QHBoxLayout(grp_t)
        self.inp_t_n = QLineEdit(); self.inp_t_n.setPlaceholderText("Tên món")
        self.inp_t_p = QLineEdit(); self.inp_t_p.setPlaceholderText("Giá"); self.inp_t_p.setFixedWidth(60)
        btn_t = QPushButton("Thêm"); btn_t.clicked.connect(self.add_todo)
        gl2.addWidget(self.inp_t_n); gl2.addWidget(self.inp_t_p); gl2.addWidget(btn_t)
        
        btn_push = QPushButton("📅 Tạo sự kiện Google (Tùy chỉnh)"); btn_push.clicked.connect(lambda: self.push_to_google("", ""))
        
        right_l.addWidget(self.lbl_detail); right_l.addWidget(self.btn_sync); right_l.addWidget(self.tabs)
        right_l.addWidget(grp_n); right_l.addWidget(grp_t); right_l.addWidget(btn_push)
        main.addWidget(right, 1)
        self.menuBar().addAction("Đăng nhập Google", self.do_auth)

    def apply_theme(self, key):
        self.current_theme = key; t = THEMES[key]; self.overlay.set_season(key)
        self.centralWidget().setStyleSheet(f"background-color:{t['bg']};")
        self.setStyleSheet(f"""
            QFrame#panel_left, QFrame#panel_right {{ background:rgba(255,255,255,0.9); border:1px solid {t['acc']}; border-radius:10px; }}
            QGroupBox {{ color:{t['sec']}; font-weight:bold; border:1px solid {t['sec']}; border-radius:5px; margin-top:5px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left:10px; padding:0 3px; }}
            QPushButton {{ background-color:{t['sec']}; color:white; border-radius:4px; padding:5px; }}
            QTabWidget::pane {{ border: 1px solid {t['acc']}; }}
        """)
        self.reload_calendar()

    def change_month(self, d):
        m, y = self.curr_date.month + d, self.curr_date.year
        if m > 12: m, y = 1, y+1
        elif m < 1: m, y = 12, y-1
        self.curr_date = datetime.date(y, m, 1)
        self.reload_calendar()

    def reload_calendar(self):
        for i in reversed(range(self.grid.count())): 
            if self.grid.itemAt(i).widget(): self.grid.itemAt(i).widget().setParent(None)
        self.cells = []
        self.lbl_my.setText(self.curr_date.strftime("Tháng %m / %Y"))
        headers = ["T2","T3","T4","T5","T6","T7","CN"]
        for i, h in enumerate(headers):
            l = QLabel(h); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setStyleSheet("font-weight:bold;")
            self.grid.addWidget(l, 0, i)
            
        # DATA SOURCES (Lấy từ Data Manager)
        trans_dates = {t.date for t in self.data_mgr.transactions}
        debt_dates = {d.due_date for d in self.data_mgr.debts if hasattr(d,'due_date')}
        
        first = self.curr_date.replace(day=1); start_w = first.weekday()
        days_n = (first.replace(month=first.month%12+1, day=1) - datetime.timedelta(days=1)).day
        r, c = 1, start_w; today = datetime.date.today()
        
        for d in range(1, days_n+1):
            dt = datetime.date(self.curr_date.year, self.curr_date.month, d); s_dt = dt.isoformat()
            
            # [REFACTORED] Kiểm tra dữ liệu qua Data Manager
            check = self.data_mgr.check_has_data(s_dt)
            
            data = {
                'has_note': check['has_note'],
                'has_todo': check['has_todo'],
                'has_event': s_dt in self.google_cache,
                'has_trans': s_dt in trans_dates,
                'has_debt': s_dt in debt_dates,
                'lunar': get_lunar_string(dt)
            }
            cell = CalendarCell(dt, data, THEMES[self.current_theme], is_today=(dt == today))
            cell.clicked.connect(self.load_details); 
            if s_dt == self.sel_date: cell.set_selected(True)
            self.grid.addWidget(cell, r, c); self.cells.append(cell)
            c += 1; 
            if c > 6: c = 0; r += 1
            
    def load_details(self, date_str):
        self.sel_date = date_str
        self.lbl_detail.setText(f"Chi tiết: {date_str}")
        for c in self.cells: c.set_selected(c.date_str == date_str)
        self.lst_evt.clear(); self.lst_not.clear(); self.lst_tod.clear()
        
        # 1. Google
        if date_str in self.google_cache:
            for e in self.google_cache[date_str]:
                t_str = e.get('start', {}).get('dateTime', 'All')[11:16]
                self.add_evt(e.get('summary','No Title'), f"Google: {t_str}", "📅", "#1976D2", e.get('id'))
        # 2. Finance
        for t in self.data_mgr.transactions:
            if t.date == date_str:
                self.add_evt(f"{t.category}: {format_money(t.amount)}", t.description or "", "💸" if t.type=="expense" else "💰", "#D32F2F" if t.type=="expense" else "#388E3C")
        for d in self.data_mgr.debts:
            if hasattr(d, 'due_date') and d.due_date == date_str:
                side = getattr(d, 'side', 'unknown')
                self.add_evt(f"Đáo hạn: {getattr(d,'name','?')}", f"{format_money(d.amount)}đ", "📤" if side in ['borrowing', 'payable'] else "📥", "#E64A19")
        
        # [REFACTORED] 3. Notes & Todos (Lấy từ Data Manager)
        for n in self.data_mgr.get_cal_notes(date_str): self.lst_not.addItem(n)
        
        for i, t in enumerate(self.data_mgr.get_cal_todos(date_str)):
            w = QWidget(); hl = QHBoxLayout(w); hl.setContentsMargins(0,0,0,0)
            cb = QCheckBox(); cb.setChecked(t['done'])
            # Gọi hàm toggle qua Data Manager
            cb.toggled.connect(lambda c, idx=i: self.tog_todo(idx, c))
            l = QLabel(f"{t['name']} - {format_money(t['price'])}đ")
            if t['done']: l.setStyleSheet("text-decoration:line-through; color:gray;")
            hl.addWidget(cb); hl.addWidget(l)
            item = QListWidgetItem(self.lst_tod); item.setSizeHint(w.sizeHint()); self.lst_tod.setItemWidget(item, w)

    def add_evt(self, t, s, i, c, eid=None):
        w = EventItemWidget(t, s, i, c, eid)
        it = QListWidgetItem(self.lst_evt); it.setSizeHint(w.sizeHint()); self.lst_evt.setItemWidget(it, w)

    # --- [REFACTORED] ACTIONS ---
    def add_note(self):
        t = self.inp_n.text()
        if t: 
            self.data_mgr.add_cal_note(self.sel_date, t) # Gọi Data Manager
            self.inp_n.clear()

    def add_todo(self):
        n = self.inp_t_n.text(); p = self.inp_t_p.text()
        if n:
            try: p_val = int(p)
            except: p_val = 0
            self.data_mgr.add_cal_todo(self.sel_date, n, p_val) # Gọi Data Manager
            self.inp_t_n.clear(); self.inp_t_p.clear()

    def tog_todo(self, idx, val):
        self.data_mgr.toggle_cal_todo(self.sel_date, idx, val) # Gọi Data Manager

    def del_item(self, type_, row):
        if type_ == 'note': self.data_mgr.delete_cal_note(self.sel_date, row)
        else: self.data_mgr.delete_cal_todo(self.sel_date, row)

    def ctx_not(self, pos): self.show_ctx(pos, self.lst_not, 'note')
    def ctx_tod(self, pos): self.show_ctx(pos, self.lst_tod, 'todo')
    
    def show_ctx(self, pos, lst, type_):
        item = lst.itemAt(pos)
        if not item: return
        row = lst.row(item)
        menu = QMenu()
        menu.addAction("❌ Xóa", lambda: self.del_item(type_, row))
        
        # Lấy text để push google cần gọi lại Data Manager để lấy đúng item
        txt = ""
        if type_ == 'note': 
            notes = self.data_mgr.get_cal_notes(self.sel_date)
            if row < len(notes): txt = notes[row]
        else: 
            todos = self.data_mgr.get_cal_todos(self.sel_date)
            if row < len(todos): 
                d = todos[row]
                txt = f"Mua {d['name']} ({format_money(d['price'])})"
            
        if txt: menu.addAction("📅 Push Google", lambda: self.push_to_google(txt, "Reminder"))
        menu.exec(lst.mapToGlobal(pos))
        
    def ctx_evt(self, pos):
        item = self.lst_evt.itemAt(pos); 
        if not item: return
        w = self.lst_evt.itemWidget(item)
        if w.eid: 
            m = QMenu(); m.addAction("🗑️ Xóa trên Google", lambda: self.del_google(w.eid)); m.exec(self.lst_evt.mapToGlobal(pos))

    # --- GOOGLE SYNC LOGIC (Giữ nguyên) ---
    def do_auth(self):
        ok, msg = self.google_svc.authenticate(); QMessageBox.information(self, "Google", msg)
        
    def sync_google(self):
        self.btn_sync.setText("⏳..."); self.worker = SyncWorker(self.google_svc, self.sel_date)
        self.worker.data_received.connect(self.on_sync); self.worker.start()
        
    def on_sync(self, res):
        self.google_cache[self.sel_date] = res; self.btn_sync.setText("Đồng bộ Google"); self.reload_calendar()
        
    def push_to_google(self, title_def, desc_def):
        dlg = QuickGoogleDialog(self, self.sel_date, title_def, desc_def)
        if dlg.exec():
            tit, start, end, desc, pop, mail = dlg.get_data()
            if not tit: return
            d = datetime.date.fromisoformat(self.sel_date)
            dt_s = datetime.datetime.combine(d, datetime.time(start.hour(), start.minute()))
            dt_e = datetime.datetime.combine(d, datetime.time(end.hour(), end.minute()))
            pop = pop if pop != -1 else None; mail = mail if mail != -1 else None
            self.pw = PushWorker(self.google_svc, tit, dt_s, dt_e, desc, pop, mail)
            self.pw.finished.connect(lambda ok, msg: [QMessageBox.information(self,"Info",msg), self.sync_google()])
            self.pw.start()

    def del_google(self, eid):
        if QMessageBox.question(self,"Confirm","Xóa sự kiện này?") == QMessageBox.StandardButton.Yes:
            self.dw = DeleteWorker(self.google_svc, eid)
            self.dw.finished.connect(lambda ok: [QMessageBox.information(self,"Info","Đã xóa" if ok else "Lỗi"), self.sync_google()])
            self.dw.start()

    def resizeEvent(self, e):
        self.overlay.resize(self.centralWidget().size())
        if not self.overlay.initialized: self.overlay.init_particles()
        super().resizeEvent(e)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    # Lưu ý: Cần file core/data_manager.py và models đã setup để chạy độc lập
    window = CalendarMgr()
    window.show()
    sys.exit(app.exec())