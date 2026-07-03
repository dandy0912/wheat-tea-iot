"""
实时监控仪表盘
对接 VPS /api/v1/sensor/latest
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QGridLayout, QFrame)
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("Qt5Agg")


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, figsize=(5, 2.5)):
        self.fig = Figure(figsize=figsize, dpi=100)
        super().__init__(self.fig)


class SensorCard(QFrame):
    def __init__(self, title, unit, color="#1a6b3c"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{ background: #fff; border-radius: 8px;
                       border-left: 4px solid {color}; padding: 8px; }}
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #888; font-size: 11px;")
        self.value_lbl = QLabel("--")
        self.value_lbl.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        self.unit_lbl = QLabel(unit)
        self.unit_lbl.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(self.title_lbl)
        h = QHBoxLayout()
        h.addWidget(self.value_lbl)
        h.addWidget(self.unit_lbl)
        h.addStretch()
        layout.addLayout(h)
        self.setLayout(layout)

    def update_value(self, val):
        self.value_lbl.setText(str(val) if val is not None else "--")


class DashboardWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self._time_data = []
        self._temp_data = []
        self._humi_data = []
        self._max_pts = 60

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)

        card_grid = QGridLayout()
        card_grid.setSpacing(10)
        self.cards = {}
        titles = [
            ("温度", "°C", "#e74c3c"), ("湿度", "%RH", "#3498db"),
            ("光照", "lux", "#f39c12"), ("CO₂", "ppm", "#9b59b6"),
            ("氮(N)", "mg/kg", "#8e44ad"), ("磷(P)", "mg/kg", "#e67e22"),
            ("钾(K)", "mg/kg", "#2ecc71"),
        ]
        for i, (title, unit, color) in enumerate(titles):
            card = SensorCard(title, unit, color)
            self.cards[title] = card
            card_grid.addWidget(card, i // 4, i % 4)
        layout.addLayout(card_grid)

        chart_layout = QHBoxLayout()
        self.canvas = MplCanvas(figsize=(10, 2.5))
        self.ax = self.canvas.fig.add_subplot(111)
        self.ax.set_title("温度 & 湿度", fontsize=10)
        self.ax.set_ylim(0, 100)
        self.line_temp, = self.ax.plot([], [], "r-", lw=1.5, label="温度(°C)")
        self.line_humi, = self.ax.plot([], [], "b-", lw=1.5, label="湿度(%)")
        self.ax.legend(fontsize=8, loc="upper right")
        self.ax.set_xticks([])
        chart_layout.addWidget(self.canvas)
        layout.addLayout(chart_layout)

        alarm_box = QGroupBox("当前告警状态")
        alarm_layout = QHBoxLayout()
        self.alarm_dot = QLabel("●")
        self.alarm_dot.setStyleSheet("color: #27ae60; font-size: 24px;")
        self.alarm_text = QLabel("系统运行正常")
        self.alarm_text.setStyleSheet("font-size: 14px;")
        alarm_layout.addWidget(self.alarm_dot)
        alarm_layout.addWidget(self.alarm_text)
        alarm_layout.addStretch()
        alarm_box.setLayout(alarm_layout)
        layout.addWidget(alarm_box)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh)
        self.timer.start(3000)

    def _refresh(self):
        device_id = self.api.cfg.get("device_id", "wheat_001")
        res = self.api.latest(device_id=device_id)
        if res.get("code") != 0:
            return
        data = res.get("data") or {}
        if isinstance(data, list):
            data = data[0] if data else {}
        self.cards["温度"].update_value(data.get("temperature"))
        self.cards["湿度"].update_value(data.get("humidity"))
        self.cards["光照"].update_value(data.get("light"))
        self.cards["CO₂"].update_value(data.get("co2"))
        self.cards["氮(N)"].update_value(data.get("soil_n"))
        self.cards["磷(P)"].update_value(data.get("soil_p"))
        self.cards["钾(K)"].update_value(data.get("soil_k"))
        self.cards["温度"].update_value(data.get("temperature"))

        self._time_data.append("")
        self._temp_data.append(data.get("temperature", 0) or 0)
        self._humi_data.append(data.get("humidity", 0) or 0)
        if len(self._time_data) > self._max_pts:
            self._time_data.pop(0)
            self._temp_data.pop(0)
            self._humi_data.pop(0)

        self.line_temp.set_data(range(len(self._temp_data)), self._temp_data)
        self.line_humi.set_data(range(len(self._humi_data)), self._humi_data)
        self.ax.set_xlim(0, max(len(self._temp_data), 1))
        self.canvas.draw_idle()

        alarm = data.get("alarm_flag", 0)
        if alarm:
            self.alarm_dot.setStyleSheet("color: #e74c3c; font-size: 24px;")
            self.alarm_text.setText("⚠ 告警中")
            self.alarm_text.setStyleSheet("font-size: 14px; color: #e74c3c;")
        else:
            self.alarm_dot.setStyleSheet("color: #27ae60; font-size: 24px;")
            self.alarm_text.setText("系统运行正常")
            self.alarm_text.setStyleSheet("font-size: 14px;")
