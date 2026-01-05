from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import *
from agent import BotChatAgentAPI, LLMWorker


class AIAnalyticsPane(QWidget):
    """Pane phân tích AI – dễ mở rộng, dễ gắn vào bất kỳ dialog nào"""
    def __init__(self, transactions, parent=None):
        super().__init__(parent)
        self.transactions = transactions
        self.agent = BotChatAgentAPI()  # Sử dụng agent đã được định nghĩa
        self._worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Dãy nút chức năng
        btn_row = QHBoxLayout()
        self.btn_analyze = QPushButton("📊 Phân tích nhanh")
        self.btn_analyze.clicked.connect(self.ai_quick_analysis)
        btn_row.addWidget(self.btn_analyze)

        btn_row.addWidget(QPushButton("💡 Gợi ý tiết kiệm", clicked=self.ai_saving_tips))
        btn_row.addWidget(QPushButton("📈 Dự báo chi", clicked=self.ai_forecast_expense))
        btn_row.addWidget(QPushButton("🧹 Xóa kết quả", clicked=self.clear_output))
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Vùng hiển thị stream
        self.output = QTextEdit(readOnly=True)
        self.output.setPlaceholderText("Chọn chức năng AI bên trên...")
        layout.addWidget(self.output)

    # -------- API chính – gọi từ bên ngoài --------
    def ai_quick_analysis(self):
        self._ai_generic("📊 Phân tích nhanh",
                         "Bạn là chuyên gia tài chính cá nhân. Hãy phân tích NGẮN GỌN (≤150 từ) và đưa ra 2-3 lời khuyên thực tế cho gia đình Việt.")

    def ai_saving_tips(self):
        self._ai_generic("💡 Gợi ý tiết kiệm",
                         "Dựa trên dữ liệu chi, hãy đưa 3-4 cách tiết kiệm thiết thực, ngắn gọn.")

    def ai_forecast_expense(self):
        self._ai_generic("📈 Dự báo chi",
                         "Với xu hướng chi hiện tại, hãy dự báo chi tiêu 1 tháng tới và cảnh báo nếu vượt thu nhập.")

    def clear_output(self):
        self.output.clear()

    # -------- logic chung – chỉ cần đổi prompt --------
    def _ai_generic(self, title: str, prompt_suffix: str):
        self.output.clear()
        self.btn_analyze.setEnabled(False)  # chỉ disable nút chính, còn lại tự do

        # Build prompt từ data thật
        total_income = sum(t.amount for t in self.transactions if t.type == "income")
        total_expense = sum(t.amount for t in self.transactions if t.type == "expense")
        balance = total_income - total_expense

        prompt = f"{prompt_suffix}\n\nDữ liệu:\n- Tổng thu: {total_income:,.0f} đ\n- Tổng chi: {total_expense:,.0f} đ\n- Số dư: {balance:,.0f} đ\n"
        if self.transactions:
            role_exp, cat_exp = {}, {}
            for t in self.transactions:
                if t.type == "expense":
                    role_exp[t.role] = role_exp.get(t.role, 0) + t.amount
                    cat_exp[t.category] = cat_exp.get(t.category, 0) + t.amount
            top_role = max(role_exp.items(), key=lambda x: x[1]) if role_exp else ("không có", 0)
            top_cat = max(cat_exp.items(), key=lambda x: x[1]) if cat_exp else ("không có", 0)
            prompt += f"- Người chi nhiều: {top_role[0]} ({top_role[1]:,.0f} đ)\n- Danh mục chi nhiều: {top_cat[0]} ({top_cat[1]:,.0f} đ)\n"

        # Stream
        self._worker = LLMWorker(prompt, self.agent)
        self._worker.newToken.connect(self._append_token)
        self._worker.finished.connect(self._on_stream_done)
        self._worker.start()

    # -------- slot nội bộ --------
    def _append_token(self, token: str):
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertPlainText(token)
        
    def _on_stream_done(self):
        self.btn_analyze.setEnabled(True)
        if self._worker:
            self._worker.quit()
            self._worker.wait()
            self._worker.deleteLater()
            self._worker = None   # tránh dangling


class HeatmapWidget(QWidget):
    def __init__(qtl, transactions, parent=None):
        super().__init__(parent)
        qtl.transactions = [t for t in transactions if t.type == "expense"]
        qtl.setMinimumSize(700, 300)
        qtl.calc_day_totals()

    def calc_day_totals(qtl):
        qtl.day_totals = {}
        for t in qtl.transactions:
            d = QDate.fromString(t.date, "yyyy-MM-dd")
            qtl.day_totals[d.toPyDate()] = qtl.day_totals.get(d.toPyDate(), 0) + t.amount
        qtl.max_amt = max(qtl.day_totals.values()) if qtl.day_totals else 1

    def paintEvent(qtl, event):
        painter = QPainter(qtl)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cell_size = 20
        margin = 10
        cols = 7
        start_date = QDate(2025, 1, 1)
        x = margin
        y = margin
        for i, (date, amt) in enumerate(sorted(qtl.day_totals.items())):
            if i % cols == 0 and i > 0:
                x = margin
                y += cell_size + 4
            ratio = amt / qtl.max_amt
            color_intensity = int(50 + ratio * 205)
            color = QColor(color_intensity, 0, 0)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawRect(x, y, cell_size, cell_size)
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(x + 2, y + 14, str(date.day))
            x += cell_size + 4


class StatisticsDialog(QDialog):
    def __init__(qtl, parent=None, transactions=None):
        super().__init__(parent)
        qtl.transactions = transactions or []
        qtl.setWindowTitle("Thống Kê")
        qtl.resize(1000, 700)
        qtl.init_ui()

    def init_ui(qtl):
        layout = QVBoxLayout()
        tabs = QTabWidget()

        # 1. Tổng quan
        summary = QTextEdit()
        summary.setReadOnly(True)
        stats = qtl.calc_stats()
        html = ""
        if stats['expense_category']:
            html += f"<p><b>Chi nhiều nhất:</b> {stats['expense_category'][0]} ({stats['expense_category'][1]:,.0f} VNĐ)</p>"
        if stats['biggest_spender']:
            html += f"<p><b>Người chi nhiều:</b> {stats['biggest_spender'][0]} ({stats['biggest_spender'][1]:,.0f} VNĐ)</p>"
        if stats['biggest_earner']:
            html += f"<p><b>Người thu nhiều:</b> {stats['biggest_earner'][0]} ({stats['biggest_earner'][1]:,.0f} VNĐ)</p>"
        summary.setHtml(html or "<i>Chưa có dữ liệu</i>")
        tabs.addTab(summary, "Tổng quan")

        # 2. AI Assistant – nhiều chức năng
        ai_pane = AIAnalyticsPane(qtl.transactions, qtl)
        tabs.addTab(ai_pane, "AI Phân tích")


        # 2. Biểu đồ tròn - Chi theo danh mục
        if any(t.type == "expense" for t in qtl.transactions):
            chart_view = QChartView()
            chart = QChart()
            series = QPieSeries()
            cat_exp = {}
            for t in qtl.transactions:
                if t.type == "expense":
                    cat_exp[t.category] = cat_exp.get(t.category, 0) + t.amount
            for cat, amt in cat_exp.items():
                series.append(cat, amt)
            chart.addSeries(series)
            chart.setTitle("Chi theo danh mục")
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            chart_view.setChart(chart)
            tabs.addTab(chart_view, "Biểu đồ tròn")

        # 3. Biểu đồ đường - Thu/chi theo tháng
        if any(t.type == "income" for t in qtl.transactions) or any(t.type == "expense" for t in qtl.transactions):
            line_tab = QWidget()
            line_layout = QVBoxLayout(line_tab)
            line_chart = qtl.build_line_chart()
            line_layout.addWidget(line_chart)
            tabs.addTab(line_tab, "Biểu đồ thu/chi theo tháng")

        # 4. Bar thu/chi theo người
        if qtl.transactions:
            bar_tab = QWidget()
            bar_layout = QVBoxLayout(bar_tab)
            bar_chart = qtl.build_bar_chart()
            bar_layout.addWidget(bar_chart)
            tabs.addTab(bar_tab, "Bar thu/chi theo người")

        # 5. Heatmap chi theo ngày
        if any(t.type == "expense" for t in qtl.transactions):
            heat_tab = QWidget()
            heat_layout = QVBoxLayout(heat_tab)
            heat_widget = HeatmapWidget(qtl.transactions)
            heat_layout.addWidget(heat_widget)
            tabs.addTab(heat_tab, "Heatmap chi theo ngày")

        # 6. Top 5 chi đắt nhất
        if any(t.type == "expense" for t in qtl.transactions):
            top_tab = QWidget()
            top_layout = QVBoxLayout(top_tab)
            top_chart = qtl.build_top5_chart()
            top_layout.addWidget(top_chart)
            tabs.addTab(top_tab, "Top 5 chi đắt nhất")

        layout.addWidget(tabs)
        layout.addWidget(QPushButton("Đóng", clicked=qtl.accept))
        qtl.setLayout(layout)


    # ----- Các hàm build biểu đồ -----
    def calc_stats(qtl):
        cat_exp, role_exp, role_inc = {}, {}, {}
        for t in qtl.transactions:
            if t.type == "expense":
                cat_exp[t.category] = cat_exp.get(t.category, 0) + t.amount
                role_exp[t.role] = role_exp.get(t.role, 0) + t.amount
            else:
                role_inc[t.role] = role_inc.get(t.role, 0) + t.amount
        return {
            'expense_category': max(cat_exp.items(), key=lambda x: x[1]) if cat_exp else None,
            'biggest_spender': max(role_exp.items(), key=lambda x: x[1]) if role_exp else None,
            'biggest_earner': max(role_inc.items(), key=lambda x: x[1]) if role_inc else None
        }

    def build_line_chart(qtl):
        monthly = {}
        for t in qtl.transactions:
            ym = t.date[:7]
            monthly.setdefault(ym, {"income": 0, "expense": 0})
            if t.type == "income":
                monthly[ym]["income"] += t.amount
            else:
                monthly[ym]["expense"] += t.amount

        sorted_keys = sorted(monthly.keys())

        income_series = QLineSeries()
        income_series.setName("Thu nhập")
        expense_series = QLineSeries()
        expense_series.setName("Chi tiêu")

        for ym in sorted_keys:
            dt = QDateTime.fromString(ym + "-01", "yyyy-MM-dd")
            ms = dt.toMSecsSinceEpoch()
            income_series.append(ms, monthly[ym]["income"])
            expense_series.append(ms, monthly[ym]["expense"])

        chart = QChart()
        chart.addSeries(income_series)
        chart.addSeries(expense_series)
        chart.setTitle("Thu chi theo tháng")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("MM/yyyy")
        axis_x.setTitleText("Tháng")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        income_series.attachAxis(axis_x)
        expense_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("VNĐ")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        income_series.attachAxis(axis_y)
        expense_series.attachAxis(axis_y)

        income_series.setColor(QColor("#27ae60"))
        expense_series.setColor(QColor("#c0392b"))

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return chart_view

    def build_bar_chart(qtl):
        role_income = {}
        role_expense = {}
        for t in qtl.transactions:
            role_income[t.role] = role_income.get(t.role, 0) + (t.amount if t.type == "income" else 0)
            role_expense[t.role] = role_expense.get(t.role, 0) + (t.amount if t.type == "expense" else 0)
        roles = sorted(set(role_income.keys()) | set(role_expense.keys()))

        income_set = QBarSet("Thu nhập")
        expense_set = QBarSet("Chi tiêu")
        for r in roles:
            income_set.append(role_income.get(r, 0))
            expense_set.append(role_expense.get(r, 0))

        series = QBarSeries()
        series.append(income_set)
        series.append(expense_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Thu chi theo thành viên")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        axis_x = QBarCategoryAxis()
        axis_x.append(roles)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("VNĐ")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        income_set.setColor(QColor("#27ae60"))
        expense_set.setColor(QColor("#c0392b"))

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return chart_view

    def build_top5_chart(qtl):
        expenses = [(t.description or t.category, t.amount) for t in qtl.transactions if t.type == "expense"]
        expenses.sort(key=lambda x: x[1], reverse=True)
        top5 = expenses[:5]

        series = QHorizontalBarSeries()
        bar_set = QBarSet("Chi")
        labels = []
        for desc, amt in top5:
            bar_set.append(amt)
            labels.append(desc[:20])
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Top 5 khoản chi đắt nhất")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        axis_y = QBarCategoryAxis()
        axis_y.append(labels)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        axis_x = QValueAxis()
        axis_x.setTitleText("VNĐ")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        bar_set.setColor(QColor("#c0392b"))

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return chart_view



