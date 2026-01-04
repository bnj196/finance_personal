from pathlib import Path
from platformdirs import user_data_dir




APP_NAME   = "__fainance_personal__"
APP_AUTHOR = "tiensthienvo"  


DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
DATA_DIR.mkdir(parents=True, exist_ok=True)   
print(f"Data directory: {DATA_DIR}")

DATA_FILE = Path(__file__).parent / "transactions.csv"
BACKUP_FOLDER = Path(__file__).parent / "backups"

DATA_FILE = Path("debts.json")
DATA_FILE      = Path("debts.json")
PAYMENT_LOG    = Path("payment_log.json")
SCHEDULE_FILE  = Path("schedule_export.csv")


BASE_DIR = Path(__file__).parent
FILE_NOTES   = BASE_DIR / "notes.json"
FILE_TODOS   = BASE_DIR / "todos.json"
FILE_MARKERS = BASE_DIR / "markers.csv"
FILE_TOKEN   = BASE_DIR / "token.json"

FILE_CRED    = BASE_DIR / "credentials.json"

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

TRANS_CSV = BASE_DIR / "transactions.csv"
LOAN_CSV  = BASE_DIR / "loans.csv"