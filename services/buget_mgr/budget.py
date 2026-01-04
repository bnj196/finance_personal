
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from ..setting import SoundManager
from . import *



class BudgetMgr(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Master Budget Pro - Âm Thanh Sống Động")
        self.resize(1100, 750)
        self.setup_ui()
        self.apply_theme("spring")
        
        # --- Khởi động nhạc nền ---
        SoundManager.instance() 

    def setup_ui(self):
        toolbar = QToolBar("Main Toolbar"); toolbar.setIconSize(QSize(24, 24)); self.addToolBar(toolbar)
        lbl_theme = QLabel("  🎨 Giao diện: "); self.combo_theme = QComboBox(); self.combo_theme.addItems(THEMES.keys())
        self.combo_theme.currentTextChanged.connect(self.apply_theme) # signal 
        toolbar.addWidget(lbl_theme); toolbar.addWidget(self.combo_theme)
        
        # --- Volume Control ---
        toolbar.addSeparator()
        lbl_vol = QLabel("  🔊 Nhạc nền: ")
        self.sld_vol = QSlider(Qt.Orientation.Horizontal)
        self.sld_vol.setRange(0, 100); self.sld_vol.setValue(80); self.sld_vol.setFixedWidth(100)
        self.sld_vol.valueChanged.connect(lambda v: SoundManager.instance().set_bgm_volume(v/100))
        toolbar.addWidget(lbl_vol); toolbar.addWidget(self.sld_vol)

        self.tabs = QTabWidget(); 
        self.tabs.setTabPosition(QTabWidget.TabPosition.North); 
        self.setCentralWidget(self.tabs)
        
        self.tab_personal = BudgetApp(); 
        self.tabs.addTab(self.tab_personal, "🔐 Két Sắt Cá Nhân")

        self.tab_group = GroupFundMgr(); 
        self.tabs.addTab(self.tab_group, "👥 Quỹ Nhóm & Dự Án")
        self.tabs.setStyleSheet(""" QTabBar::tab { height: 40px; width: 200px; font-weight: bold; font-size: 14px; } QTabWidget::pane { border-top: 2px solid #bdc3c7; } """)

    def apply_theme(self, key):...
    #     t = THEMES[key]
    #     self.setStyleSheet(f"QMainWindow {{ background-color: {t['bg']}; }}")
    #     self.tab_personal.update_theme(t); self.tab_group.update_theme(t)
    #     self.tabs.setStyleSheet(f""" QTabBar::tab {{ background: #e0e0e0; color: #555; height: 40px; width: 200px; font-weight: bold; }} QTabBar::tab:selected {{ background: {t['btn']}; color: white; }} QTabWidget::pane {{ border: 2px solid {t['btn']}; }} """)
    #     btn_style = f"QPushButton {{ background-color: {t['btn']}; color: white; border-radius: 5px; padding: 6px; font-weight: bold; }}"
    #     self.tab_personal.setStyleSheet(btn_style)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = BudgetMgr()
    window.show()
    sys.exit(app.exec())