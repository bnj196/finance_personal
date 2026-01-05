from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Dict


@dataclass
class Debt:
    id: int
    counterparty: str
    side: str          # "IOWE" | "THEY_OWE"
    amount: float
    paid_back: float
    interest_rate: float
    term_months: int
    start_date: str
    due_date: str | None
    purpose: str
    compound: bool


    def outstanding(self) -> float:
        return max(self.amount - self.paid_back, 0)

    def is_overdue(self) -> bool:
        if self.due_date:
            return date.fromisoformat(self.due_date) < date.today() and self.outstanding() > 0
        return False

    def repayment_schedule(self) -> List[Dict]:
        if self.term_months <= 0 or self.amount <= 0:
            due = self.due_date or self.start_date
            return [{"date": due, "amount": self.amount, "paid": self.paid_back >= self.amount}]
        years = self.term_months / 12
        if self.compound:
            total = self.amount * (1 + self.interest_rate / 100) ** years
        else:
            total = self.amount * (1 + self.interest_rate / 100 * years)
        monthly = total / self.term_months
        start = datetime.fromisoformat(self.start_date).date()
        schedule = []
        paid_cum = 0.0
        for i in range(self.term_months):
            due_date = start + timedelta(days=30 * (i + 1))
            paid_cum += monthly
            schedule.append({
                "date": due_date.isoformat(),
                "amount": monthly,
                "paid": self.paid_back >= paid_cum - 1e-5
            })
        return schedule


