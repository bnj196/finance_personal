import sys, json, csv, datetime, random, math, os.path, shutil
from pathlib import Path

from lunardate import LunarDate
from style import SeasonalOverlay, THEMES
from core import *

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *



# -------------- GOOGLE --------------
class GoogleService:
    def __init__(self):
        self.service = None
        self.creds = None

    def authenticate(self):
        try:
            if os.path.exists(FILE_TOKEN):
                self.creds = Credentials.from_authorized_user_file(str(FILE_TOKEN), SCOPES)
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(FILE_CRED):
                        return False, "Không tìm thấy file credentials"
                    flow = InstalledAppFlow.from_client_secrets_file(str(FILE_CRED), SCOPES)
                    self.creds = flow.run_local_server(port=0)
                with open(FILE_TOKEN, "w") as token:
                    token.write(self.creds.to_json())
            self.service = build("calendar", "v3", credentials=self.creds)
            return True, "Kết nối Google thành công"
        except Exception as e:
            return False, str(e)

    def fetch_events(self, date_str):
        if not self.service: return []
        start_time = f"{date_str}T00:00:00Z"
        end_time   = f"{date_str}T23:59:59Z"
        try:
            res = self.service.events().list(calendarId='primary', timeMin=start_time, timeMax=end_time,
                                             singleEvents=True, orderBy='startTime').execute()
            return res.get('items', [])
        except Exception as e:
            print("fetch_events", e); return []

    # def create_event_advanced(self, summary, start_dt, end_dt, description,
    #                           popup_min, email_min):
    #     if not self.service: return False, "Chưa đăng nhập Google"
    #     overrides = []
    #     if popup_min is not None:
    #         overrides.append({'method': 'popup', 'minutes': popup_min})
    #     if email_min is not None:
    #         overrides.append({'method': 'email', 'minutes': email_min})

    #     body = {
    #         'summary': summary,
    #         'description': description,
    #         'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Ho_Chi_Minh'},
    #         'end':   {'dateTime': end_dt.isoformat(),   'timeZone': 'Asia/Ho_Chi_Minh'},
    #         'reminders': {'useDefault': False, 'overrides': overrides}
    #     }
    #     try:
    #         self.service.events().insert(calendarId='primary', body=body).execute()
    #         return True, "Đã thêm sự kiện lên Google"
    #     except Exception as e:
    #         return False, str(e)

    # def remove_event(self, event_id):
    #     if not self.service: return False
    #     try:
    #         self.service.events().delete(calendarId='primary', eventId=event_id).execute()
    #         return True
    #     except: return False

# 👇 Thay thế hàm cũ bằng hàm này để đảm bảo logic thông báo chuẩn xác
    def create_event_advanced(self, summary, start_dt, end_dt, description,
                              popup_min, email_min):
        """
        popup_min: số phút báo trước (int), nếu None là không báo
        email_min: số phút báo trước qua email (int)
        """
        if not self.service: return False, "Chưa đăng nhập Google"
        
        overrides = []
        
        # Xử lý Popup (Thông báo trên điện thoại)
        if popup_min is not None:
            try:
                # Ép kiểu int để tránh lỗi nếu lỡ truyền string
                val = int(popup_min)
                overrides.append({'method': 'popup', 'minutes': val})
            except: pass

        # Xử lý Email
        if email_min is not None:
            try:
                val = int(email_min)
                overrides.append({'method': 'email', 'minutes': val})
            except: pass

        # Cấu hình Body chuẩn ISO
        body = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(), 
                'timeZone': 'Asia/Ho_Chi_Minh' # Quan trọng để đúng giờ VN
            },
            'end': {
                'dateTime': end_dt.isoformat(),   
                'timeZone': 'Asia/Ho_Chi_Minh'
            },
            'reminders': {
                'useDefault': False, 
                'overrides': overrides
            }
        }
        
        try:
            event = self.service.events().insert(calendarId='primary', body=body).execute()
            link = event.get('htmlLink', '')
            return True, f"Đã thêm sự kiện!\nLink: {link}"
        except Exception as e:
            return False, str(e)

# -------------- WORKERS --------------
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
        ok, msg = self.svc.create_event_advanced(self.s, self.st, self.en, self.desc,
                                                 self.popup_min, self.email_min)
        self.finished.emit(ok, msg)

class DeleteWorker(QThread):
    finished = pyqtSignal(bool)
    def __init__(self, svc, eid): super().__init__(); self.svc, self.eid = svc, eid
    def run(self): self.finished.emit(self.svc.remove_event(self.eid))


# -------------- UI COMPONENTS --------------
class CalendarCell(QFrame):
    clicked = pyqtSignal(str)
    
    def __init__(self, date_obj, data, theme, is_today=False):
        super().__init__()
        self.date_str = date_obj.strftime("%Y-%m-%d")
        self.theme = theme
        self.is_today = is_today
        self.is_selected = False # Trạng thái chọn
        
        self.setFixedSize(110, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(4, 4, 4, 4); self.main_lay.setSpacing(1)
        
        top = QHBoxLayout()
        lbl_day = QLabel(str(date_obj.day))
        lbl_day.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        if date_obj.weekday() == 6: lbl_day.setStyleSheet("color:red;")
        top.addWidget(lbl_day)
        
        # Dots
        if data['has_note']: top.addWidget(self.dot("blue"))
        if data['has_todo']: top.addWidget(self.dot("green"))
        if data['has_event']: top.addWidget(self.dot("red"))
        top.addStretch()
        self.main_lay.addLayout(top)
        
        # Marker message
        if data['marker_msg']:
            lbl_m = QLabel(data['marker_msg'])
            lbl_m.setStyleSheet("background-color:#FFF9C4;color:#F57F17;font-size:9px;padding:2px;border-radius:3px;")
            lbl_m.setWordWrap(True)
            self.main_lay.addWidget(lbl_m)
        else:
            self.main_lay.addStretch()
            
        # Lunar
        lbl_lun = QLabel(data['lunar'])
        lbl_lun.setStyleSheet("color:gray;font-size:9px;")
        lbl_lun.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.main_lay.addWidget(lbl_lun)
        
        self.update_style() # Khởi tạo style lần đầu

    def dot(self, c):
        l = QLabel("●"); l.setStyleSheet(f"color:{c};font-size:8px;border:none;background:transparent;")
        return l

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()

    def update_style(self):...
        # # Màu nền
        # bg = "white"
        # if self.is_today: bg = "#E3F2FD" # Màu hôm nay
        
        # # Viền
        # border_color = self.theme['acc']
        # border_width = "1px"
        
        # if self.is_today:
        #     border_color = self.theme['sec']
            
        # if self.is_selected:
        #     bg = "#FFF9C4" # Màu nền khi chọn (vàng nhạt)
        #     border_color = "#E91E63" # Màu viền khi chọn (hồng đậm)
        #     border_width = "3px" # Viền dày lên
            
        # self.setStyleSheet(f"""
        #     QFrame{{
        #         background-color:{bg};
        #         border:{border_width} solid {border_color};
        #         border-radius:8px;
        #     }}
        #     QFrame:hover{{
        #         background-color:{self.theme['bg']};
        #         border:2px solid {self.theme['sec']};
        #     }}
        # """)

    def mousePressEvent(self, e):
        self.clicked.emit(self.date_str)

class EventItemWidget(QWidget):
    def __init__(self, title, time_str, is_google=False, eid=None):
        super().__init__(); self.eid = eid
        lay = QVBoxLayout(self); lay.setContentsMargins(5, 5, 5, 5)
        lbl_title = QLabel(title); lbl_title.setStyleSheet("font-weight:bold;font-size:12px;border:none;")
        lbl_time = QLabel(time_str); lbl_time.setStyleSheet("color:#555;font-size:10px;border:none;")
        lay.addWidget(lbl_title); lay.addWidget(lbl_time)
        bg = "#E8F5E9" if is_google else "#FFF3E0"
        self.setStyleSheet(f"background-color:{bg};border-radius:5px;")

# -------------- DIALOG PUSH CUSTOM --------------
class QuickGoogleDialog(QDialog):
    # [FIX] Thêm giá trị mặc định cho summary và desc để tránh lỗi
    def __init__(self, parent, date_str, default_summary="", default_desc=""):
        super().__init__(parent)
        self.setWindowTitle(f"Push Google – {date_str}")
        self.setFixedSize(400, 300)
        self.date_str = date_str

        lay = QFormLayout(self)

        self.inp_title = QLineEdit(default_summary)
        self.inp_desc  = QLineEdit(default_desc)
        now = QTime.currentTime()
        self.time_start = QTimeEdit(now.addSecs(60))   # mặc định sau 1 phút
        self.time_end   = QTimeEdit(now.addSecs(180)) # sau 3 phút
        # popup
        self.sb_popup = QSpinBox()
        self.sb_popup.setRange(-1, 999)
        self.sb_popup.setValue(0)
        self.sb_popup.setSuffix(" phút")
        self.sb_popup.setSpecialValueText("Tắt")
        # email
        self.sb_email = QSpinBox()
        self.sb_email.setRange(-1, 999)
        self.sb_email.setValue(1)
        self.sb_email.setSuffix(" phút")
        self.sb_email.setSpecialValueText("Tắt")

        lay.addRow("Tiêu đề:", self.inp_title)
        lay.addRow("Mô tả:",  self.inp_desc)
        lay.addRow("Giờ bắt đầu:", self.time_start)
        lay.addRow("Giờ kết thúc:", self.time_end)
        lay.addRow("Nhắc Popup:", self.sb_popup)
        lay.addRow("Nhắc Email:", self.sb_email)

        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        lay.addRow(btn)

    def get_data(self):
        d = datetime.date.fromisoformat(self.date_str)
        start_time = datetime.time(self.time_start.time().hour(), self.time_start.time().minute())
        end_time   = datetime.time(self.time_end.time().hour(), self.time_end.time().minute())
        dt_start = datetime.datetime.combine(d, start_time)
        dt_end   = datetime.datetime.combine(d, end_time)
        popup_min = None if self.sb_popup.value() == -1 else self.sb_popup.value()
        email_min = None if self.sb_email.value() == -1 else self.sb_email.value()
        return self.inp_title.text(), dt_start, dt_end, self.inp_desc.text(), popup_min, email_min

# -------------- MAIN APP --------------
class CalendarMgr(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lịch Vạn Năng & Tài Chính – v2.1")
        self.resize(1300, 800)
        init_csv_files()
        self.google_service = GoogleService()
        self.notes = load_json(FILE_NOTES); self.todos = load_json(FILE_TODOS); self.markers = load_csv_dict(FILE_MARKERS)
        self.trans = []; self.loans = []; self.reload_finance()
        self.current_date = datetime.date.today().replace(day=1)
        self.selected_date_str = datetime.date.today().isoformat()
        self.google_events_cache = {}; self.current_theme_key = "spring"
        
        # [NEW] Danh sách quản lý các ô lịch
        self.cells = [] 

        self.init_ui()
        self.overlay = SeasonalOverlay(self.centralWidget()); self.overlay.show(); self.overlay.raise_()
        self.apply_theme("spring")

    def reload_finance(self):
        self.trans = load_csv_dict(TRANS_CSV); self.loans = load_csv_dict(LOAN_CSV)

    # ---------- UI ----------
    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); main = QHBoxLayout(central)

        left = QFrame(); left.setObjectName("panel_left"); leftLay = QVBoxLayout(left)
        nav = QHBoxLayout()
        btn_prev = QPushButton("◀"); btn_prev.clicked.connect(lambda: self.change_month(-1))
        self.lbl_month_year = QLabel(); self.lbl_month_year.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        btn_next = QPushButton("▶"); btn_next.clicked.connect(lambda: self.change_month(1))
        self.combo_theme = QComboBox(); self.combo_theme.addItems(list(THEMES.keys())); self.combo_theme.currentTextChanged.connect(self.apply_theme); self.combo_theme.setFixedWidth(100)
        nav.addWidget(btn_prev); nav.addWidget(self.lbl_month_year); nav.addWidget(btn_next); nav.addStretch()
        nav.addWidget(QLabel("Giao diện:")); nav.addWidget(self.combo_theme)
        leftLay.addLayout(nav)
        self.calendar_grid = QGridLayout(); leftLay.addLayout(self.calendar_grid); leftLay.addStretch()
        main.addWidget(left)

        right = QFrame(); right.setObjectName("panel_right"); right.setFixedWidth(420); rightLay = QVBoxLayout(right)
        self.lbl_selected_date = QLabel("Chọn một ngày..."); self.lbl_selected_date.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold)); rightLay.addWidget(self.lbl_selected_date)
        self.btn_sync_google = QPushButton("🔄 Đồng bộ Google Calendar"); self.btn_sync_google.clicked.connect(self.sync_google); rightLay.addWidget(self.btn_sync_google)
        self.tabs = QTabWidget()
        self.list_events = QListWidget(); self.list_events.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.list_events.customContextMenuRequested.connect(self.ctx_event)
        self.list_notes  = QListWidget(); self.list_notes.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.list_notes.customContextMenuRequested.connect(self.ctx_note)
        self.list_todos  = QListWidget(); self.list_todos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.list_todos.customContextMenuRequested.connect(self.ctx_todo)
        self.tabs.addTab(self.list_events, "Sự kiện"); self.tabs.addTab(self.list_notes, "Ghi chú"); self.tabs.addTab(self.list_todos, "Mua sắm"); rightLay.addWidget(self.tabs)

        grp_note = QGroupBox("Thêm Ghi chú"); lay_note = QHBoxLayout(grp_note)
        self.inp_note_content = QLineEdit(); self.inp_note_content.setPlaceholderText("Nội dung..."); btn_note = QPushButton("Lưu"); btn_note.clicked.connect(self.add_note)
        lay_note.addWidget(self.inp_note_content); lay_note.addWidget(btn_note); rightLay.addWidget(grp_note)

        grp_todo = QGroupBox("Thêm Mua sắm"); lay_todo = QHBoxLayout(grp_todo)
        self.inp_todo_name = QLineEdit(); self.inp_todo_name.setPlaceholderText("Tên món...")
        self.inp_todo_price = QLineEdit(); self.inp_todo_price.setPlaceholderText("Giá..."); self.inp_todo_price.setFixedWidth(80)
        btn_todo = QPushButton("Thêm"); btn_todo.clicked.connect(self.add_todo)
        lay_todo.addWidget(self.inp_todo_name); lay_todo.addWidget(self.inp_todo_price); lay_todo.addWidget(btn_todo); rightLay.addWidget(grp_todo)

        btn_add_google = QPushButton("📅 Đặt lịch Google (hẹn giờ)")
        btn_add_google.setStyleSheet("background-color:#4285F4;color:white;font-weight:bold;padding:8px;")
        btn_add_google.clicked.connect(self.open_google_add)
        rightLay.addWidget(btn_add_google)

        main.addWidget(right)

        # menu bar
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Import CSV giao dịch", self.import_csv_trans)
        google_menu = self.menuBar().addMenu("Google")
        google_menu.addAction("Đăng nhập / Refresh", self.do_google_auth)

        self.render_calendar()

    # ---------- THEME ----------
    def apply_theme(self, key):...
        # self.current_theme_key = key; t = THEMES[key]; self.overlay.set_season(key)
        # self.centralWidget().setStyleSheet(f"background-color:{t['bg']};")
        # style = f"""
        #     QFrame#panel_left, QFrame#panel_right{{background-color:rgba(255,255,255,0.85);border:1px solid {t['acc']};border-radius:12px;}}
        #     QLabel{{color:{t['txt']};}} QGroupBox{{border:1px solid {t['sec']};border-radius:5px;margin-top:10px;font-weight:bold;color:{t['sec']};}} QGroupBox::title{{subcontrol-origin: margin;left:10px;padding:0 3px;}}
        # """
        # self.setStyleSheet(style)
        # btn_style = f"QPushButton{{background-color:{t['sec']};color:white;border-radius:4px;padding:6px;}}"
        # for btn in self.findChildren(QPushButton):
        #     if "Google" not in btn.text(): btn.setStyleSheet(btn_style)
        
        # # Reload để update style của các ô lịch
        # self.render_calendar()

    # ---------- CALENDAR ----------
    def change_month(self, delta):
        m, y = self.current_date.month + delta, self.current_date.year
        if m > 12: m, y = 1, y + 1
        elif m < 1: m, y = 12, y - 1
        self.current_date = datetime.date(y, m, 1); self.render_calendar()

    def render_calendar(self):
        # Clear cũ
        for i in reversed(range(self.calendar_grid.count())):
            self.calendar_grid.itemAt(i).widget().setParent(None)
        
        self.cells = [] # Reset list cell

        self.lbl_month_year.setText(self.current_date.strftime("Tháng %m / %Y"))
        headers = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        for i, h in enumerate(headers):
            lbl = QLabel(h); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); lbl.setStyleSheet("font-weight:bold;"); self.calendar_grid.addWidget(lbl, 0, i)
        
        first_weekday = self.current_date.weekday()
        days_in_month = (self.current_date.replace(month=self.current_date.month % 12 + 1, day=1) - datetime.timedelta(days=1)).day
        
        row, col = 1, first_weekday
        theme = THEMES[self.current_theme_key]
        today_date = datetime.date.today()
        
        for day in range(1, days_in_month + 1):
            d_date = datetime.date(self.current_date.year, self.current_date.month, day)
            d_str = d_date.isoformat()
            
            marker_txt = next((m['message'] for m in self.markers if m.get('date') == d_str), "")
            cell_data = {'has_note': d_str in self.notes and len(self.notes[d_str]) > 0,
                         'has_todo': d_str in self.todos and len(self.todos[d_str]) > 0,
                         'has_event': d_str in self.google_events_cache,
                         'lunar': get_lunar_string(d_date), 'marker_msg': marker_txt}
            
            is_today = (d_date == today_date)
            
            # Tạo Cell
            cell = CalendarCell(d_date, cell_data, theme, is_today)
            
            # [FIX] Đánh dấu nếu đang được chọn (để giữ trạng thái khi đổi tháng/reload)
            if d_str == self.selected_date_str:
                cell.set_selected(True)
            
            cell.clicked.connect(self.load_date_details)
            self.calendar_grid.addWidget(cell, row, col)
            self.cells.append(cell) # Lưu vào list để quản lý selection

            col += 1
            if col > 6: col = 0; row += 1

    # ---------- DETAILS ----------
    def load_date_details(self, date_str):
        self.selected_date_str = date_str
        
        # [NEW] Cập nhật giao diện Selection
        for c in self.cells:
            if c.date_str == date_str:
                c.set_selected(True)
            else:
                c.set_selected(False)

        self.lbl_selected_date.setText(f"Chi tiết: {date_str}")
        
        # notes
        self.list_notes.clear()
        for note in self.notes.get(date_str, []): self.list_notes.addItem(note)
        # todos
        self.list_todos.clear()
        todos = self.todos.get(date_str, [])
        for i, t in enumerate(todos):
            w = QWidget(); lay = QHBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0)
            cb = QCheckBox(); cb.setChecked(t.get('done', False)); cb.toggled.connect(lambda c, idx=i: self.toggle_todo(idx, c))
            name = t.get('name', t.get('text', 'Không tên')); price_text = format_money(t.get('price', 0))
            lbl = QLabel(f"{name} – {price_text} đ")
            if t.get('done'): lbl.setStyleSheet("text-decoration:line-through;color:gray;")
            lay.addWidget(cb); lay.addWidget(lbl)
            item = QListWidgetItem(self.list_todos); item.setSizeHint(w.sizeHint()); self.list_todos.setItemWidget(item, w)
        # events
        self.list_events.clear()
        # local
        for l in self.loans:
            if l.get('due_date') == date_str:
                w = EventItemWidget(f"Vay: {l.get('counterparty', '')}", f"{format_money(l.get('amount', 0))}đ", is_google=False); item = QListWidgetItem(self.list_events); item.setSizeHint(w.sizeHint()); self.list_events.setItemWidget(item, w)
        for t in self.trans:
            if t.get('expiry_date') == date_str:
                w = EventItemWidget(f"Hết hạn: {t.get('description', '')}", t.get('category', ''), is_google=False); item = QListWidgetItem(self.list_events); item.setSizeHint(w.sizeHint()); self.list_events.setItemWidget(item, w)
        # google
        if date_str in self.google_events_cache:
            for ev in self.google_events_cache[date_str]:
                summary = ev.get('summary', '(Không tiêu đề)')
                start_raw = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date', ''))
                time_display = "Cả ngày"
                if 'T' in start_raw:
                    try: time_display = datetime.datetime.fromisoformat(start_raw).strftime("%H:%M")
                    except: pass
                w = EventItemWidget(summary, time_display, is_google=True, eid=ev.get('id')); item = QListWidgetItem(self.list_events); item.setSizeHint(w.sizeHint()); self.list_events.setItemWidget(item, w)

    # ---------- ACTIONS ----------
    def add_note(self):
        txt = self.inp_note_content.text().strip()
        if not txt: return
        self.notes.setdefault(self.selected_date_str, []).append(txt)
        save_json(self.notes, FILE_NOTES); self.inp_note_content.clear(); self.load_date_details(self.selected_date_str); self.render_calendar()

    def add_todo(self):
        name = self.inp_todo_name.text().strip()
        if not name: return
        try: price = int(self.inp_todo_price.text().strip())
        except: price = 0
        self.todos.setdefault(self.selected_date_str, []).append({"name": name, "price": price, "done": False})
        save_json(self.todos, FILE_TODOS); self.inp_todo_name.clear(); self.inp_todo_price.clear(); self.load_date_details(self.selected_date_str); self.render_calendar()

    def toggle_todo(self, idx, checked):
        if self.selected_date_str in self.todos:
            self.todos[self.selected_date_str][idx]['done'] = checked
            save_json(self.todos, FILE_TODOS); self.load_date_details(self.selected_date_str)

    # ---------- CONTEXT ----------
    def ctx_note(self, pos):
        item = self.list_notes.itemAt(pos)
        if not item: return
        row = self.list_notes.row(item)
        menu = QMenu()
        menu.addAction("❌ Xóa", lambda: self.del_note(row))
        menu.addAction("📅 Push Google", lambda: self.push_to_google(item.text(), "Ghi chú"))
        menu.exec(self.list_notes.mapToGlobal(pos))

    def del_note(self, row):
        notes = self.notes.get(self.selected_date_str, [])
        if isinstance(notes, str): notes = [notes]
        notes.pop(row)
        if not notes: self.notes.pop(self.selected_date_str, None)
        else: self.notes[self.selected_date_str] = notes
        save_json(self.notes, FILE_NOTES); self.load_date_details(self.selected_date_str); self.render_calendar()

    def ctx_todo(self, pos):
        item = self.list_todos.itemAt(pos)
        if not item: return
        row = self.list_todos.row(item)
        menu = QMenu()
        menu.addAction("❌ Xóa", lambda: self.del_todo(row))
        t = self.todos[self.selected_date_str][row]
        txt = f"Mua: {t.get('name', '')} – {format_money(t.get('price', 0))}đ"
        menu.addAction("📅 Push Google", lambda: self.push_to_google(txt, "Mua sắm"))
        menu.exec(self.list_todos.mapToGlobal(pos))

    def del_todo(self, row):
        self.todos[self.selected_date_str].pop(row)
        if not self.todos[self.selected_date_str]: self.todos.pop(self.selected_date_str, None)
        save_json(self.todos, FILE_TODOS); self.load_date_details(self.selected_date_str); self.render_calendar()

    def ctx_event(self, pos):
        item = self.list_events.itemAt(pos)
        if not item: return
        widget = self.list_events.itemWidget(item)
        if not widget or not widget.eid: return
        menu = QMenu(); menu.addAction("🗑️ Xóa trên Google", lambda: self.del_google_event(widget.eid))
        menu.exec(self.list_events.mapToGlobal(pos))

    def del_google_event(self, eid):
        if QMessageBox.question(self, "Xác nhận", "Xóa vĩnh viễn sự kiện này?") != QMessageBox.StandardButton.Yes: return
        self.btn_sync_google.setEnabled(False); self.btn_sync_google.setText("⏳ Xóa...")
        self.delete_worker = DeleteWorker(self.google_service, eid); self.delete_worker.finished.connect(self.on_del_done); self.delete_worker.start()

    def on_del_done(self, ok):
        self.btn_sync_google.setEnabled(True); self.btn_sync_google.setText("🔄 Đồng bộ Google Calendar")
        if ok: QMessageBox.information(self, "OK", "Đã xóa"); self.sync_google()
        else: QMessageBox.warning(self, "Lỗi", "Không thể xóa")

    # ---------- GOOGLE ----------
    def do_google_auth(self):
        ok, msg = self.google_service.authenticate(); QMessageBox.information(self, "Google", msg)

    def sync_google(self):
        self.btn_sync_google.setEnabled(False); self.btn_sync_google.setText("⏳ Tải...")
        self.sync_worker = SyncWorker(self.google_service, self.selected_date_str); self.sync_worker.data_received.connect(self.on_sync_done); self.sync_worker.start()

    def on_sync_done(self, events):
        self.google_events_cache[self.selected_date_str] = events; self.btn_sync_google.setEnabled(True); self.btn_sync_google.setText("🔄 Đồng bộ Google Calendar"); self.load_date_details(self.selected_date_str); self.render_calendar()

    def open_google_add(self):
        # [FIX] Đã sửa lỗi: QuickGoogleDialog giờ có giá trị mặc định, nên gọi 2 tham số là OK
        dlg = QuickGoogleDialog(self, self.selected_date_str)
        if dlg.exec():
            title, start, end, desc, popup, email = dlg.get_data()
            if not title: return
            self.btn_sync_google.setEnabled(False); self.btn_sync_google.setText("⏳ Push...")
            self.push_worker = PushWorker(self.google_service, title, start, end, desc, popup, email)
            self.push_worker.finished.connect(self.on_push_done)
            self.push_worker.start()

    def on_push_done(self, ok, msg):
        self.btn_sync_google.setEnabled(True); self.btn_sync_google.setText("🔄 Đồng bộ Google Calendar")
        if ok: QMessageBox.information(self, "OK", msg); self.sync_google()
        else: QMessageBox.warning(self, "Lỗi", msg)

    # 👇 PUSH CÓ TÙY CHỈNH THỜI GIAN & LOẠI NHẮC
    def push_to_google(self, summary, desc=""):
        dlg = QuickGoogleDialog(self, self.selected_date_str, summary, desc)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        title, start, end, desc, popup_min, email_min = dlg.get_data()
        self.btn_sync_google.setEnabled(False); self.btn_sync_google.setText("⏳ Push...")
        self.push_worker = PushWorker(self.google_service, title, start, end, desc, popup_min, email_min)
        self.push_worker.finished.connect(self.on_push_done)
        self.push_worker.start()

    # ---------- IMPORT ----------
    def import_csv_trans(self):
        f, _ = QFileDialog.getOpenFileName(self, "Chọn CSV giao dịch", "", "CSV (*.csv)")
        if f:
            Path(f).replace(TRANS_CSV); self.reload_finance(); QMessageBox.information(self, "OK", "Đã import & reload giao dịch.")

    # ---------- RESIZE ----------
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'overlay'):
            self.overlay.setGeometry(self.centralWidget().rect())
            if not self.overlay.initialized: self.overlay.init_particles()

# -------------- RUN --------------
if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion"); app.setFont(QFont("Segoe UI", 10))
    win = CalendarMgr(); win.show(); sys.exit(app.exec())