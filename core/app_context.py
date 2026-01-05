import json
from PyQt6.QtCore import QObject, pyqtSignal

class AppContext(QObject):
    """
    Singleton Class quản lý trạng thái toàn cục của ứng dụng (Global State).
    Chịu trách nhiệm: Theme, User Session, Global Settings.
    """
    _instance = None

    # --- SIGNALS (Tín hiệu phát ra khi trạng thái thay đổi) ---
    # 1. Báo hiệu thay đổi giao diện (VD: "spring", "winter")
    theme_changed = pyqtSignal(str)
    
    # 2. Báo hiệu user đăng nhập/đăng xuất (Gửi dict data user hoặc None)
    user_state_changed = pyqtSignal(object)
    
    # 3. Báo hiệu cài đặt thay đổi (VD: Âm lượng, ngôn ngữ)
    setting_changed = pyqtSignal(str, object) 
    
    # 4. Điều hướng trang từ bất kỳ đâu (Gửi index trang)
    navigation_requested = pyqtSignal(int)

    @classmethod
    def instance(cls):
        """Phương thức lấy instance duy nhất (Singleton Pattern)"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        if AppContext._instance is not None:
            raise Exception("AppContext là Singleton! Hãy dùng AppContext.instance().")
        
        # --- KHỞI TẠO DỮ LIỆU MẶC ĐỊNH ---
        self._current_theme = "spring"
        
        self._user_data = None  # Chưa login
        
        self._settings = {
            "volume": 80,
            "show_notifications": True,
            "language": "vi",
            "auto_backup": False
        }
        
        print("✅ AppContext (Core) đã khởi động.")

    # =========================================
    # 1. QUẢN LÝ THEME (GIAO DIỆN)
    # =========================================
    @property
    def current_theme(self):
        return self._current_theme

    def set_theme(self, theme_key: str):
        """Đổi theme và bắn tín hiệu cho toàn bộ App cập nhật"""
        if self._current_theme != theme_key:
            self._current_theme = theme_key
            self.theme_changed.emit(theme_key)
            print(f"🎨 AppContext: Đã đổi theme sang '{theme_key}'")

    # =========================================
    # 2. QUẢN LÝ USER (ĐĂNG NHẬP/XUẤT)
    # =========================================
    @property
    def user_data(self):
        return self._user_data

    def login(self, user_info: dict):
        """Lưu thông tin user khi login thành công"""
        self._user_data = user_info
        self.user_state_changed.emit(user_info)
        print(f"👤 AppContext: User '{user_info.get('name')}' đã đăng nhập.")

    def logout(self):
        """Xóa thông tin user"""
        self._user_data = None
        self.user_state_changed.emit(None)
        print("👋 AppContext: User đã đăng xuất.")

    # =========================================
    # 3. QUẢN LÝ CÀI ĐẶT (SETTINGS)
    # =========================================
    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key, value):
        """Cập nhật 1 cài đặt và báo cho các module liên quan"""
        if self._settings.get(key) != value:
            self._settings[key] = value
            self.setting_changed.emit(key, value)
            
            # Nếu chỉnh âm lượng, gọi luôn SoundManager (nếu cần thiết kế chặt chẽ hơn)
            # Nhưng tốt nhất để UI lắng nghe signal 'setting_changed'
            print(f"⚙️ AppContext: Setting '{key}' đổi thành {value}")

    # =========================================
    # 4. ĐIỀU HƯỚNG (NAVIGATION)
    # =========================================
    def navigate_to(self, page_index: int):
        """Yêu cầu Main Window chuyển tab"""
        self.navigation_requested.emit(page_index)
