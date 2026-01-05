import sys
import shutil
import pathlib
from datetime import datetime, date
from PyQt6.QtCore import QObject, pyqtSignal
from models._tran import *

# Import Engine từ các module con

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


        from services.debt_mgr.engine import DebtEngine
        from services.transaction_mgr.engine import TransactionEngine
        from services.buget_mgr.engine import BudgetEngine
        # --- KHỞI TẠO CÁC ENGINE ---
        # DataManager nắm giữ quyền điều khiển các engine này
        print("🔄 DataManager: Đang khởi động các Engine...")
        self.trans_engine = TransactionEngine()
        self.debt_engine = DebtEngine()
        self.budget_engine = BudgetEngine()
        
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
        total_savings = sum(fund.current for fund in self.funds)
        
        
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
                    
                    "savings": total_savings, # <--- Dữ liệu thật từ các hũ
                    
                    # Tài sản ròng = (Tiền mặt + Tiết kiệm + Khoản phải thu) - Nợ phải trả
                    "net_worth": trans_sum["balance"] + total_savings + debt_sum["net"],
                    
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
    

    
    # --- FUNDS (CÁ NHÂN) ---
    @property
    def funds(self): 
        """Lấy danh sách quỹ cá nhân từ Engine"""
        return self.budget_engine.funds
    
    def add_fund(self, f):
        self.budget_engine.add_fund(f)
        self.notify_change()
        
    def update_fund(self, f):
        self.budget_engine.update_fund(f)
        self.notify_change()

    def delete_fund(self, fid: int): # <--- Bổ sung cái này cho đủ bộ
        self.budget_engine.delete_fund(fid)
        self.notify_change()

    # --- GOALS (NHÓM) ---
    @property
    def goals(self): 
        """Lấy danh sách quỹ nhóm từ Engine"""
        return self.budget_engine.goals

    def add_goal(self, g):
        """Thêm quỹ nhóm mới"""
        self.budget_engine.add_goal(g)
        self.notify_change() 

    def update_goal(self, g):
        """
        Cập nhật thông tin quỹ nhóm (Tên, Target, Members, Node Positions...)
        """
        self.budget_engine.update_goal(g)
        self.notify_change()

    def delete_goal(self, gid: int):
        """Xóa quỹ nhóm"""
        self.budget_engine.delete_goal(gid)
        self.notify_change()
    # Nhớ đảm bảo đã import các thư viện này ở đầu file data_manager.py
    # import uuid
    # from datetime import datetime, date

    def execute_fund_transaction(self, fund_id: str, amount: float, note: str, is_deposit: bool):
        """
        Hàm xử lý giao dịch quỹ (Cash Flow Logic):
        - Nếu Nạp (Deposit): Tiền trong Ví giảm (Expense) -> Tiền trong Hũ tăng.
        - Nếu Rút (Withdraw): Tiền trong Hũ giảm -> Tiền trong Ví tăng (Income).
        """
        # 1. Tìm quỹ theo ID (UUID string)
        fund = self.budget_engine.get_fund_by_id(fund_id)
        
        if not fund: 
            print(f"❌ DataManager: Không tìm thấy quỹ ID {fund_id}")
            return

        # 2. XÁC ĐỊNH LOGIC GIAO DỊCH
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if is_deposit:
            # Nạp tiền: Hũ tăng tiền
            fund.current += amount
            
            # History của Hũ
            hist_type = "in"
            
            # Giao dịch của Ví
            trans_type = "expense"        # Ví mất tiền
            trans_cat = "Tiết kiệm & Đầu tư"
            prefix = "Nạp quỹ"
        else:
            # Rút tiền: Hũ giảm tiền
            fund.current -= amount
            
            # History của Hũ
            hist_type = "out"
            
            # Giao dịch của Ví
            trans_type = "income"         # Ví nhận lại tiền
            trans_cat = "Chi tiêu từ quỹ" # Hoặc "Thu nhập khác"
            prefix = "Rút quỹ"

        # 3. CẬP NHẬT LỊCH SỬ QUỸ (BUDGET ENGINE)
        if not hasattr(fund, 'history') or fund.history is None: 
            fund.history = []
            
        fund.history.append({
            "date": current_time,
            "amount": amount,
            "note": note,
            "type": hist_type
        })
        
        # Lưu thay đổi của Quỹ xuống ổ cứng ngay lập tức
        self.budget_engine.save()

        # 4. TẠO GIAO DỊCH TRONG VÍ (TRANSACTION ENGINE)
        # Import uuid ở đây hoặc đầu file
        import uuid
        
        new_trans = Transaction(
            id=str(uuid.uuid4()),
            date=date.today().isoformat(), # YYYY-MM-DD
            category=trans_cat,
            amount=amount,
            type=trans_type, 
            role="CaNhan",
            description=f"[{prefix}] {fund.name}: {note}",
            is_recurring=False,
            cycle="" # Trường này cần nếu Model Transaction yêu cầu
        )
        
        self.trans_engine.add_transaction(new_trans)

        # 5. THÔNG BÁO UI CẬP NHẬT
        print(f"✅ DataManager: Đã xử lý {prefix} {amount:,.0f}đ -> {fund.name}")
        self.data_changed.emit() # Refresh toàn bộ Dashboard và UI


# --- THÊM VÀO CLASS DataManager ---
    
    def update_fund(self, fund):
        """Cập nhật thông tin quỹ (Tên, Target, Icon...)"""
        self.budget_engine.update_fund(fund)
        self.notify_change() # Báo cho UI refresh

    def delete_fund(self, fund_id: str):
        """Xóa quỹ vĩnh viễn"""
        self.budget_engine.delete_fund(fund_id)
        self.notify_change() # Báo cho UI refresh