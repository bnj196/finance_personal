import sys
import shutil
import pathlib
from datetime import datetime, date
from PyQt6.QtCore import QObject, pyqtSignal
from models._tran import *


from core._const import BACKUP_DIR

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
        from services.calendar_mgr.engine import CalendarEngine
        # --- KHỞI TẠO CÁC ENGINE ---
        # DataManager nắm giữ quyền điều khiển các engine này
        print("🔄 DataManager: Đang khởi động các Engine...")
        self.trans_engine = TransactionEngine()
        self.debt_engine = DebtEngine()
        self.budget_engine = BudgetEngine()
        self.calendar_engine = CalendarEngine()
        

        
        print("✅ DataManager: Đã load dữ liệu thành công.")





# --- GETTERS (Để UI lấy dữ liệu hiển thị) ---
    def get_cal_todos(self, date_str):
        return self.calendar_engine.get_todos(date_str)

    def get_cal_notes(self, date_str):
        return self.calendar_engine.get_notes(date_str)
    
    # Hàm hỗ trợ vẽ chấm trên lịch (kiểm tra ngày đó có data không)
    def check_has_data(self, date_str):

        todos = self.calendar_engine.get_todos(date_str)
        notes = self.calendar_engine.get_notes(date_str)
        return {
            'has_todo': len(todos) > 0,
            'has_note': len(notes) > 0
        }

    # --- ACTIONS (Để UI gọi khi người dùng thao tác) ---
    def add_cal_todo(self, date_str, name, price):
        self.calendar_engine.add_todo(date_str, name, price)
        self.notify_change() # Báo UI reload

    def toggle_cal_todo(self, date_str, index, is_done):
        self.calendar_engine.update_todo_status(date_str, index, is_done)
        # Checkbox toggle thường không cần reload toàn bộ lịch, 
        # nhưng reload để đồng bộ chấm màu/gạch ngang cũng tốt.
        self.notify_change()

    def delete_cal_todo(self, date_str, index):
        self.calendar_engine.delete_todo(date_str, index)
        self.notify_change()

    def add_cal_note(self, date_str, content):
        self.calendar_engine.add_note(date_str, content)
        self.notify_change()

    def delete_cal_note(self, date_str, index):
        self.calendar_engine.delete_note(date_str, index)
        self.notify_change()

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

    def get_dashboard_summary(self):
        """
        Tổng hợp số liệu từ tất cả các nguồn để hiển thị lên Dashboard.
        Trả về dict với dữ liệu đã được chuẩn hóa, an toàn và sẵn sàng cho UI.
        """
        from datetime import date

        today_str = date.today().isoformat()

        # --- 1. Transaction Summary ---
        try:
            trans_sum = self.trans_engine.summary()  # {income, expense, balance}
            income = trans_sum.get("income", 0)
            expense = trans_sum.get("expense", 0)
            balance = trans_sum.get("balance", 0)
        except Exception:
            income = expense = balance = 0

        # --- 2. Debt Summary ---
        try:
            debt_sum = self.debt_engine.summary()  # {i_owe, they_owe, net}
            debt_owe = debt_sum.get("i_owe", 0)
            debt_recv = debt_sum.get("they_owe", 0)
            debt_net = debt_sum.get("net", 0)
        except Exception:
            debt_owe = debt_recv = debt_net = 0

        # --- 3. Savings (Từ BudgetEngine) ---
        try:
            funds = self.funds or []
            total_savings = sum(getattr(fund, 'current', 0) for fund in funds)
        except Exception:
            total_savings = 0

        # --- 4. Giao dịch gần đây (5 giao dịch mới nhất) ---
        try:
            all_trans = self.trans_engine.get_all() or []
            # Sắp xếp theo ngày giảm dần (hỗ trợ cả str "YYYY-MM-DD" và date object)
            def parse_date(trans):
                d = getattr(trans, 'date', '')
                if isinstance(d, str):
                    return d
                elif hasattr(d, 'isoformat'):
                    return d.isoformat()
                else:
                    return "1970-01-01"
            recent = sorted(all_trans, key=parse_date, reverse=True)[:5]
            recent_dicts = [t.to_dict() if hasattr(t, 'to_dict') else vars(t) for t in recent]
        except Exception:
            recent_dicts = []

        # --- 5. Dữ liệu Lịch (Todo + Notes) ---
        try:
            calendar_todos = self.calendar_engine.get_todos(today_str) or []
            calendar_notes = self.calendar_engine.get_notes(today_str) or []
        except Exception:
            calendar_todos = []
            calendar_notes = []

        # --- 6. Tính toán tài sản ròng ---
        net_worth = balance + total_savings + debt_net

        return {
            "income": income,
            "expense": expense,
            "balance": balance,
            "debt_owe": debt_owe,
            "debt_recv": debt_recv,
            "savings": total_savings,
            "net_worth": net_worth,
            "recent_transactions": recent_dicts,
            "calendar_todos": calendar_todos,   # ← Đã đổi tên để rõ nghĩa
            "calendar_notes": calendar_notes    # ← Mới: ghi chú hôm nay
        }
    

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