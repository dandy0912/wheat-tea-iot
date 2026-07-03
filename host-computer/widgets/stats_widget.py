"""
病虫害统计分析
对接 VPS /api/v1/disease/stats
饼图: 按严重程度 / 按作物 / 按病害类型
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class MplCanvas(FigureCanvas):
    def __init__(self, figsize=(4, 3)):
        self.fig = Figure(figsize=figsize, dpi=90)
        super().__init__(self.fig)


class StatsWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        refresh_btn = QPushButton("🔄 刷新统计")
        refresh_btn.setStyleSheet("background: #1a6b3c; color: #fff; border: none; "
                                  "padding: 8px 24px; border-radius: 6px; font-size: 13px;")
        refresh_btn.clicked.connect(self._refresh)
        layout.addWidget(refresh_btn, alignment=Qt.AlignLeft)

        chart_layout = QHBoxLayout()
        self.canvas_severity = MplCanvas()
        self.canvas_crop = MplCanvas()
        self.canvas_disease = MplCanvas()
        chart_layout.addWidget(self.canvas_severity)
        chart_layout.addWidget(self.canvas_crop)
        chart_layout.addWidget(self.canvas_disease)
        layout.addLayout(chart_layout)

        summary_box = QGroupBox("统计摘要")
        summary_layout = QHBoxLayout()
        self.total_label = QLabel("总检测数: --")
        self.total_label.setStyleSheet("font-size: 14px;")
        summary_layout.addWidget(self.total_label)
        summary_layout.addStretch()
        summary_box.setLayout(summary_layout)
        layout.addWidget(summary_box)

        self.setLayout(layout)
        self._refresh()

    def _refresh(self):
        res = self.api.alarm_stats()
        data = res.get("data", {}) if res.get("code") == 0 else {}
        total = data.get("total_detections", 0)
        self.total_label.setText(f"总检测数: {total}")
        self._pie(self.canvas_severity, data.get("by_severity", {}), "按严重程度")
        self._pie(self.canvas_crop, data.get("by_crop", {}), "按作物类型")
        self._pie(self.canvas_disease, data.get("by_disease", {}), "按病害类型")

    def _pie(self, canvas, data, title):
        canvas.fig.clear()
        ax = canvas.fig.add_subplot(111)
        data = {k: v for k, v in data.items() if v > 0}
        if not data:
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center",
                    fontsize=11, color="#888")
            ax.set_title(title, fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            labels = list(data.keys())
            sizes = list(data.values())
            colors = ["#e74c3c", "#e67e22", "#f39c12", "#27ae60",
                      "#3498db", "#9b59b6", "#1abc9c", "#2ecc71"]
            wedges, texts, autotexts = ax.pie(
                sizes, labels=None, autopct="%1.0f%%",
                colors=colors[:len(labels)], startangle=90,
                pctdistance=0.75,
            )
            ax.legend(wedges, [f"{l} ({s})" for l, s in zip(labels, sizes)],
                      loc="upper right", fontsize=7)
            ax.set_title(title, fontsize=10)
        canvas.draw_idle()
