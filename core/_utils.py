import shutil, csv, json, os, pathlib, datetime
from lunardate import LunarDate

from ._const import *


def backup_csv(file_save: str)-> bool:
    try:
        os.makedirs(BACKUP_FOLDER, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_FOLDER / f"{file_save}_backup_{timestamp}.csv"
        shutil.copy(DATA_FILE, backup_file)
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False
    return True


# -------------- UTILS --------------
def format_money(amount):
    try:
        return f"{int(float(amount)):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

def get_lunar_string(d: datetime.date):
    lunar = LunarDate.fromSolarDate(d.year, d.month, d.day)
    return f"{lunar.day}/{lunar.month}"


def load_json(path):
    if path.exists():
        try: return json.loads(path.read_text(encoding='utf-8'))
        except: return {}
    return {}

def save_json(data, path):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def load_csv_dict(path):
    if not path.exists(): return []
    try:
        with path.open(newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except: return []

def save_csv_dict(path, rows, fieldnames):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def init_csv_files():
    if not TRANS_CSV.exists():
        save_csv_dict(TRANS_CSV, [], ["date","category","amount","type","role","description","expiry_date","is_recurring"])
    if not LOAN_CSV.exists():
        save_csv_dict(LOAN_CSV, [], ["id","counterparty","side","amount","due_date"])