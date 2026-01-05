from services import FinanceApp
from services.setting import SoundManager, SoundFilter

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    my_filter = SoundFilter()
    app.installEventFilter(my_filter)

    window = FinanceApp()
    window.show()
    sys.exit(app.exec())