

#--------------------region transaction ------
class Transaction:
    def __init__(self, id, date, category, amount, type, role, description="", expiry_date="", is_recurring=False, cycle="Tháng"):
        self.id = id
        self.date = date
        self.category = category
        self.amount = amount
        self.type = type
        self.role = role
        self.description = description
        self.expiry_date = expiry_date
        self.is_recurring = is_recurring
        self.cycle = cycle

class FamilyMember:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.total_income = 0
        self.total_expense = 0
