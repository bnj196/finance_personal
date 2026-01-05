import csv
import json
import shutil
import pathlib
from datetime import datetime
from dataclasses import asdict
from typing import List, Dict

# Import Model
from models._debt import Debt
from core._const import BACKUP_DIR, DEBT_DATA



class DebtEngine:
    def __init__(self, file: pathlib.Path = DEBT_DATA):
        self.file = file
        self._debts: List[Debt] = []
        self._load()

    def _load(self):
        self._debts = []
        if self.file.exists():
            try:
                text = self.file.read_text(encoding="utf8")
                if not text: return
                data = json.loads(text)
                
                # Xử lý trường hợp file cũ lưu dạng Dict {"debts": []} hoặc List []
                raw_list = data if isinstance(data, list) else data.get("debts", [])
                
                self._debts = [Debt(**d) for d in raw_list]
            except Exception as e:
                print(f"❌ DebtEngine Load Error: {e}")
                self._debts = []

    def _save(self):
        try:
            # Tạo thư mục cha nếu chưa có
            self.file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert Object -> Dict
            data = [asdict(d) for d in self._debts]
            self.file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")
        except Exception as e:
            print(f"❌ DebtEngine Save Error: {e}")

    # ==========================
    # CRUD
    # ==========================
    def next_id(self) -> int:
        return max([d.id for d in self._debts], default=0) + 1

    def add_debt(self, d: Debt):
        self._debts.append(d)
        self._save()

    def update_debt(self, d: Debt):
        for idx, old in enumerate(self._debts):
            if old.id == d.id:
                self._debts[idx] = d
                break
        self._save()

    def delete_debt(self, _id: int):
        self._debts = [d for d in self._debts if d.id != _id]
        self._save()

    def get_debts(self, active_only=False) -> List[Debt]:
        if active_only:
            return [d for d in self._debts if d.outstanding() > 0]
        return self._debts

    def summary(self) -> Dict[str, float]:
        owe = sum(d.outstanding() for d in self._debts if d.side == "IOWE")
        they = sum(d.outstanding() for d in self._debts if d.side == "THEY_OWE")
        return {"i_owe": owe, "they_owe": they, "net": they - owe}

    # ==========================
    # IMPORT / EXPORT / BACKUP
    # ==========================
    def export_csv(self, path: str):
        try:
            if not path.endswith(".csv"): path += ".csv"
            
            # Lấy header chuẩn từ Model thay vì từ data (tránh lỗi khi list rỗng)
            fieldnames = [field for field in Debt.__annotations__.keys()]
            
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for d in self._debts:
                    writer.writerow(asdict(d))
            return True
        except Exception as e:
            print(f"Export Error: {e}")
            return False

    def import_csv(self, path: str):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                imported_count = 0
                for r in reader:
                    # Xử lý an toàn cho boolean và None
                    is_compound = str(r.get("compound", "")).lower() in ("true", "1", "yes")
                    due = r.get("due_date")
                    if not due or due == "None" or due == "":
                        due = None

                    new_debt = Debt(
                        id=int(r.get("id", self.next_id() + imported_count)), # Tự sinh ID nếu trùng
                        counterparty=r["counterparty"],
                        side=r["side"],
                        amount=float(r["amount"]),
                        paid_back=float(r["paid_back"]),
                        interest_rate=float(r["interest_rate"]),
                        term_months=int(r["term_months"]),
                        start_date=r["start_date"],
                        due_date=due,
                        purpose=r["purpose"],
                        compound=is_compound
                    )
                    self._debts.append(new_debt)
                    imported_count += 1
                self._save()
                return imported_count
        except Exception as e:
            print(f"Import Error: {e}")
            raise e

    def backup(self):
        """Hàm này CẦN PHẢI CÓ để DataManager gọi"""
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = BACKUP_DIR / f"debts_backup_{timestamp}.json"
            
            if self.file.exists():
                shutil.copy(self.file, backup_file)
                return str(backup_file)
        except Exception as e:
            print(f"Backup Debt Error: {e}")
            return None