import sys
import shutil
import pathlib
from datetime import datetime, date
from PyQt6.QtCore import QObject, pyqtSignal

# Import Engine từ các module con
from services.debt_mgr.engine import DebtEngine
from services.transaction_mgr.engine import TransactionEngine

# Định nghĩa đường dẫn backup chung (Engine tự lo file data của nó)
BACKUP_DIR = pathlib.Path(__file__).parent.parent / "backups"

class DataManager(QObject):
    """
    Singleton Facade quản lý toàn bộ dữ liệu nghiệp vụ.
    Nó sở hữu các Engine con (Transaction, Debt) và điều phối luồng dữ liệu.
    """
    _instance = None
    
    # Signal: Bắn ra khi bất kỳ dữ liệu nào thay đổi
    data_changed = pyqtSignal()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        if DataManager._instance is not None:
            raise Exception("DataManager là Singleton!")
        
        # --- KHỞI TẠO CÁC ENGINE ---
        # DataManager nắm giữ quyền điều khiển các engine này
        print("🔄 DataManager: Đang khởi động các Engine...")
        self.trans_engine = TransactionEngine()
        self.debt_engine = DebtEngine()
        
        # TODO: Sau này thêm BudgetEngine, CalendarEngine vào đây
        
        print("✅ DataManager: Đã load dữ liệu thành công.")

    # ==========================================
    # 1. TRANSACTION PROXY (Ủy quyền)
    # ==========================================
    @property
    def transactions(self):
        """Trả về list Transaction Objects từ Engine"""
        return self.trans_engine.get_all()

    def add_transaction(self, t):
        self.trans_engine.add_transaction(t)
        self.notify_change()

    def update_transaction(self, t):
        self.trans_engine.update_transaction(t)
        self.notify_change()

    def delete_transaction(self, tid):
        self.trans_engine.delete_transaction(tid)
        self.notify_change()

    # ==========================================
    # 2. DEBT PROXY (Ủy quyền)
    # ==========================================
    @property
    def debts(self):
        """Trả về list Debt Objects từ Engine"""
        return self.debt_engine.get_debts()

    def add_debt(self, d):
        self.debt_engine.add_debt(d)
        self.notify_change()

    def update_debt(self, d):
        self.debt_engine.update_debt(d)
        self.notify_change()

    def delete_debt(self, did):
        self.debt_engine.delete_debt(did)
        self.notify_change()

    # ==========================================
    # 3. DASHBOARD AGGREGATION (TỔNG HỢP)
    # ==========================================
    def get_dashboard_summary(self):
        """
        Tổng hợp số liệu từ tất cả các nguồn để hiển thị lên Dashboard.
        """
        # 1. Từ Transaction Engine
        trans_sum = self.trans_engine.summary() # {income, expense, balance}
        
        # 2. Từ Debt Engine
        debt_sum = self.debt_engine.summary()   # {i_owe, they_owe, net}
        
        # 3. Từ Budget/Goal (Chưa có Engine nên tạm tính giả lập hoặc để 0)
        total_savings = 0 
        
        # 4. Giao dịch gần đây
        all_trans = self.trans_engine.get_all()
        # Sắp xếp theo ngày giảm dần (nếu chưa sắp xếp)
        # Giả sử date format là YYYY-MM-DD
        recent = sorted(all_trans, key=lambda x: x.date, reverse=True)[:5]
        
        # Convert Transaction Object -> Dict cho Dashboard dễ dùng (nếu Dashboard dùng Dict)
        # Hoặc trả về Object luôn tùy Dashboard
        recent_dicts = [t.to_dict() for t in recent]

        return {
            "income": trans_sum["income"],
            "expense": trans_sum["expense"],
            "balance": trans_sum["balance"],
            
            "debt_owe": debt_sum["i_owe"],
            "debt_recv": debt_sum["they_owe"],
            
            "savings": total_savings,
            
            # Tài sản ròng = Tiền mặt + (Khoản phải thu - Khoản phải trả) + Tiết kiệm
            "net_worth": trans_sum["balance"] + debt_sum["net"] + total_savings,
            
            "recent_transactions": recent_dicts
        }

    # ==========================================
    # 4. NOTIFICATION & UTILS
    # ==========================================
    def notify_change(self):
        """Bắn tín hiệu để toàn bộ UI cập nhật"""
        print("📢 DataManager: Dữ liệu thay đổi -> Notify UI")
        self.data_changed.emit()

    def create_backup(self):
        """Sao lưu toàn bộ dữ liệu"""
        if not BACKUP_DIR.exists():
            BACKUP_DIR.mkdir(parents=True)
        
        # Gọi từng Engine thực hiện backup của riêng nó
        t_backup = self.trans_engine.backup()
        # d_backup = self.debt_engine.backup() # Cần implement hàm backup trong DebtEngine
        
        if t_backup:
            print(f"✅ Backup Transaction tại: {t_backup}")
            return True
        return False