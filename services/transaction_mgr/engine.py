import csv
import pathlib
import shutil
import random
from typing import List, Dict
from datetime import datetime
from PyQt6.QtCore import QDateTime

# Import Model (Giả sử bạn đã có file models.py chứa Transaction class)
from models import Transaction 

# Cấu hình đường dẫn file
DATA_FILE = pathlib.Path(__file__).parent.parent.parent / "transactions.csv"
BACKUP_FOLDER = pathlib.Path(__file__).parent.parent.parent / "backups"

class TransactionEngine:
    """
    Class chịu trách nhiệm duy nhất: Đọc/Ghi/Xử lý file transactions.csv
    Không dính dáng gì đến PyQt Widget.
    """
    def __init__(self, file_path: pathlib.Path = DATA_FILE):
        self.file_path = file_path
        self._transactions: List[Transaction] = []
        self.load()

    # ==========================
    # CORE: LOAD & SAVE
    # ==========================
    def load(self):
        self._transactions = []
        if not self.file_path.exists():
            return
        
        try:
            with open(self.file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    t = Transaction(
                        id=row["id"],
                        date=row["date"],
                        category=row["category"],
                        amount=float(row["amount"]),
                        type=row["type"],
                        role=row["role"],
                        description=row.get("description", ""),
                        expiry_date=row.get("expiry_date", ""),
                        is_recurring=row.get("is_recurring", "False") == "True",
                        cycle=row.get("cycle", "Tháng")
                    )
                    self._transactions.append(t)
        except Exception as e:
            print(f"❌ Error loading transactions: {e}")

    def save(self):
        try:
            # Tạo thư mục nếu chưa có
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Lấy tên trường từ Transaction Model (hoặc hardcode list cho chuẩn)
            fieldnames = ["id", "date", "category", "amount", "type", "role", 
                          "description", "expiry_date", "is_recurring", "cycle"]
            
            with open(self.file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for t in self._transactions:
                    # Convert Object -> Dict
                    row = {
                        "id": t.id,
                        "date": t.date,
                        "category": t.category,
                        "amount": t.amount,
                        "type": t.type,
                        "role": t.role,
                        "description": t.description,
                        "expiry_date": t.expiry_date,
                        "is_recurring": "True" if t.is_recurring else "False",
                        "cycle": getattr(t, "cycle", "Tháng")
                    }
                    writer.writerow(row)
        except Exception as e:
            print(f"❌ Error saving transactions: {e}")

    # ==========================
    # CRUD METHODS
    # ==========================
    def get_all(self) -> List[Transaction]:
        return self._transactions

    def add_transaction(self, t: Transaction):
        self._transactions.append(t)
        self.save()

    def update_transaction(self, new_t: Transaction):
        for i, t in enumerate(self._transactions):
            if t.id == new_t.id:
                self._transactions[i] = new_t
                break
        self.save()

    def delete_transaction(self, tid: str):
        self._transactions = [t for t in self._transactions if t.id != tid]
        self.save()

    # ==========================
    # UTILS (Import/Export/Backup)
    # ==========================
    def import_csv(self, path: str):
        try:
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                imported_count = 0
                for row in reader:
                    # Tự tạo ID mới nếu import
                    new_id = str(random.randint(100000, 999999))
                    t = Transaction(
                        id=row.get("id", new_id),
                        date=row["date"],
                        category=row["category"],
                        amount=float(row["amount"]),
                        type=row["type"],
                        role=row["role"],
                        description=row.get("description", ""),
                        expiry_date=row.get("expiry_date", ""),
                        is_recurring=row.get("is_recurring", "False").lower() == "true",
                        cycle=row.get("cycle", "Tháng")
                    )
                    self._transactions.append(t)
                    imported_count += 1
                self.save()
                return imported_count
        except Exception as e:
            raise e

    def export_csv(self, path: str):
        if not path.endswith(".csv"): path += ".csv"
        # Chỉ cần gọi lại hàm save nhưng đổi path tạm thời
        temp_engine = TransactionEngine(pathlib.Path(path))
        temp_engine._transactions = self._transactions
        temp_engine.save()

    def backup(self):
        try:
            BACKUP_FOLDER.mkdir(exist_ok=True)
            timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
            backup_file = BACKUP_FOLDER / f"transactions_backup_{timestamp}.csv"
            shutil.copy(self.file_path, backup_file)
            return str(backup_file)
        except Exception as e:
            print(f"Backup error: {e}")
            return None