import csv
import json
import pathlib
from dataclasses import asdict
from typing import List, Dict
from core._const import DATA_FILE
from models._debt import Debt


class DebtEngine:
    def __init__(self, file: pathlib.Path = DATA_FILE):
        self.file = file
        self._debts: List[Debt] = []
        self._load()

    def _load(self):
        if self.file.exists():
            try:
                data = json.loads(self.file.read_text(encoding="utf8"))
                self._debts = [Debt(**d) for d in data]
            except Exception:
                self._debts = []

    def _save(self):
        self.file.write_text(json.dumps([asdict(d) for d in self._debts], ensure_ascii=False, indent=2), encoding="utf8")

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
        return [d for d in self._debts if d.outstanding() > 0] if active_only else self._debts

    def summary(self) -> Dict[str, float]:
        owe = sum(d.outstanding() for d in self._debts if d.side == "IOWE")
        they = sum(d.outstanding() for d in self._debts if d.side == "THEY_OWE")
        return {"i_owe": owe, "they_owe": they, "net": they - owe}

    def export_csv(self, path: str):
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=asdict(self._debts[0]).keys() if self._debts else [])
            writer.writeheader()
            writer.writerows([asdict(d) for d in self._debts])

    def import_csv(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self._debts = [Debt(
                    int(r["id"]), r["counterparty"], r["side"],
                    float(r["amount"]), float(r["paid_back"]),
                    float(r["interest_rate"]), int(r["term_months"]),
                    r["start_date"], r["due_date"] or None,
                    r["purpose"], r["compound"] == "True"
                ) for r in reader]
                self._save()
        except Exception as e:
            print(e)
