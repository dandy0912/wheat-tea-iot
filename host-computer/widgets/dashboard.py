"""
实时监控仪表盘
对接 VPS /api/v1/sensor/latest 并在明亮日系 VN 配色风格下进行多设备数据聚合与展示
"""
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, figsize=(10, 3)):
        self.fig = Figure(figsize=figsize, dpi=100)
        self.fig.patch.set_facecolor('#f5f7fa')  # 明亮背景
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.setup_axes()

    def setup_axes(self):
        self.ax.set_facecolor('#ffffff')  # 纯白画布
        self.ax.grid(True, color='#689fd226', linestyle='--', linewidth=0.5)
        for spine in ['top', 'right']:
            self.ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            self.ax.spines[spine].set_color('#689fd240')
        self.ax.tick_params(colors='#7f8c8d', labelsize=8)


class SensorCard(QFrame):
    def __init__(self, title, icon, unit, color="#4cd9c0"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid rgba(104, 159, 210, 0.15);
                border-radius: 12px;
                border-left: 4px solid {color};
                padding: 10px;
            }}
            QFrame:hover {{
                border-color: rgba(104, 159, 210, 0.35);
                background-color: #ffffff;
            }}
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.title_lbl = QLabel(f"{icon}  {title}")
        self.title_lbl.setStyleSheet("color: #7f8c8d; font-size: 13px; font-weight: bold;")

        self.value_lbl = QLabel("--")
        self.value_lbl.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: bold;")

        self.unit_lbl = QLabel(unit)
        self.unit_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px; font-weight: 500;")

        layout.addWidget(self.title_lbl)

        h = QHBoxLayout()
        h.addWidget(self.value_lbl)
        h.addWidget(self.unit_lbl)
        h.addStretch()
        layout.addLayout(h)
        self.setLayout(layout)

    def update_value(self, val, suffix=""):
        if val is None:
            self.value_lbl.setText("--")
        elif isinstance(val, float):
            self.value_lbl.setText(f"{val:.1f}{suffix}")
        else:
            self.value_lbl.setText(f"{val}{suffix}")


class DashboardWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.current_device_id = None  # None 表示全部设备

        self._time_data = []
        self._temp_data = []
        self._humi_data = []
        self._max_pts = 60

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 传感器卡片网格
        card_grid = QGridLayout()
        card_grid.setSpacing(12)
        self.cards = {}

        # (标题, 图标, 单位, 配色)
        titles = [
            ("温度", "🌡️", "°C", "#e57373"),        # 柔美红
            ("湿度", "💧", "%RH", "#689fd2"),       # 温柔蓝
            ("光照", "☀️", "lux", "#ffb74d"),       # 暖橙黄
            ("CO₂", "☁️", "ppm", "#b39ddb"),        # 淡紫色
            ("土壤氮(N)", "🧪", "mg/kg", "#b39ddb"),  # 淡紫色
            ("土壤磷(P)", "🌾", "mg/kg", "#f48fb1"),  # 柔美粉
            ("土壤钾(K)", "🌿", "mg/kg", "#4cd9c0"),  # 薄荷青
        ]

        for i, (title, icon, unit, color) in enumerate(titles):
            card = SensorCard(title, icon, unit, color)
            self.cards[title] = card
            card_grid.addWidget(card, i // 4, i % 4)

        layout.addLayout(card_grid)

        # 趋势图表
        self.canvas = MplCanvas()
        layout.addWidget(self.canvas)

        # 告警状态
        self.alarm_box = QGroupBox("系统运行状态")
        alarm_layout = QHBoxLayout()
        self.alarm_dot = QLabel("●")
        self.alarm_dot.setStyleSheet("color: #4cd9c0; font-size: 24px;")
        self.alarm_text = QLabel("数据加载中...")
        self.alarm_text.setStyleSheet("font-size: 14px; font-weight: 500; color: #34495e;")
        alarm_layout.addWidget(self.alarm_dot)
        alarm_layout.addWidget(self.alarm_text)
        alarm_layout.addStretch()
        self.alarm_box.setLayout(alarm_layout)
        layout.addWidget(self.alarm_box)

        self.setLayout(layout)

        # 定时器
        interval = self.api.cfg.get("refresh_interval", 3000)
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh)
        self.timer.start(interval)

        self._refresh()

    def set_device_filter(self, device_id):
        if self.current_device_id != device_id:
            self.current_device_id = device_id
            # 切换设备时清空历史趋势图，避免折线图混合
            self._time_data.clear()
            self._temp_data.clear()
            self._humi_data.clear()
            self.canvas.ax.clear()
            self.canvas.setup_axes()
            self.canvas.draw_idle()
            self._refresh()

    def cleanup(self):
        self.timer.stop()

    def _refresh(self):
        res = self.api.latest(device_id=self.current_device_id)

        if res.get("code") != 0:
            self.alarm_dot.setStyleSheet("color: #90a4ae; font-size: 24px;")
            self.alarm_text.setText(f"连接异常: {res.get('msg') or res.get('message') or '未知错误'}")
            self.alarm_text.setStyleSheet("font-size: 14px; color: #e57373;")
            return

        data = res.get("data")

        if self.current_device_id is None:
            # --- 全部设备模式 (数据聚合) ---
            if not isinstance(data, list):
                data = [data] if data else []

            if not data:
                for card in self.cards.values():
                    card.update_value(None)
                self.alarm_dot.setStyleSheet("color: #90a4ae; font-size: 24px;")
                self.alarm_text.setText("暂无任何在线设备数据")
                return

            # 计算各项平均值
            keys = [
                ("temperature", "温度"), ("humidity", "湿度"),
                ("light", "光照"), ("co2", "CO₂"),
                ("soil_n", "土壤氮(N)"), ("soil_p", "土壤磷(P)"),
                ("soil_k", "土壤钾(K)")
            ]

            agg_data = {}
            for field, title in keys:
                vals = [d.get(field) for d in data if d and d.get(field) is not None]
                agg_data[title] = sum(vals) / len(vals) if vals else None
                self.cards[title].update_value(agg_data[title], suffix=" (均值)" if agg_data[title] is not None else "")

            # 趋势图打点记录 (均值)
            self._time_data.append("")
            self._temp_data.append(agg_data["温度"] or 0.0)
            self._humi_data.append(agg_data["湿度"] or 0.0)

            # 告警检测
            alarming_devices = [d.get("device_id") for d in data if d and d.get("alarm_flag", 0) > 0]
            if alarming_devices:
                self.alarm_dot.setStyleSheet("color: #e57373; font-size: 24px;")
                devs_str = ", ".join(alarming_devices[:3])
                self.alarm_text.setText(f"⚠ 告警中 (异常设备: {devs_str}{'等' if len(alarming_devices) > 3 else ''})")
                self.alarm_text.setStyleSheet("font-size: 14px; color: #e57373; font-weight: bold;")
            else:
                self.alarm_dot.setStyleSheet("color: #4cd9c0; font-size: 24px;")
                self.alarm_text.setText(f"系统运行正常 (全部设备就绪，共 {len(data)} 台)")
                self.alarm_text.setStyleSheet("font-size: 14px; color: #34495e;")

        else:
            # --- 单设备模式 ---
            if isinstance(data, list):
                data = data[0] if data else {}
            elif data is None:
                data = {}

            self.cards["温度"].update_value(data.get("temperature"))
            self.cards["湿度"].update_value(data.get("humidity"))
            self.cards["光照"].update_value(data.get("light"))
            self.cards["CO₂"].update_value(data.get("co2"))
            self.cards["土壤氮(N)"].update_value(data.get("soil_n"))
            self.cards["土壤磷(P)"].update_value(data.get("soil_p"))
            self.cards["土壤钾(K)"].update_value(data.get("soil_k"))

            # 趋势图记录
            self._time_data.append("")
            self._temp_data.append(data.get("temperature") or 0.0)
            self._humi_data.append(data.get("humidity") or 0.0)

            # 告警状态
            alarm = data.get("alarm_flag", 0)
            if alarm:
                self.alarm_dot.setStyleSheet("color: #e57373; font-size: 24px;")
                self.alarm_text.setText("⚠ 当前设备告警中 (环境指标超出阈值)")
                self.alarm_text.setStyleSheet("font-size: 14px; color: #e57373; font-weight: bold;")
            else:
                self.alarm_dot.setStyleSheet("color: #4cd9c0; font-size: 24px;")
                self.alarm_text.setText("系统运行正常 (设备工作指标稳定)")
                self.alarm_text.setStyleSheet("font-size: 14px; color: #34495e;")

        if len(self._time_data) > self._max_pts:
            self._time_data.pop(0)
            self._temp_data.pop(0)
            self._humi_data.pop(0)

        self._update_chart()

    def _update_chart(self):
        ax = self.canvas.ax
        ax.clear()
        self.canvas.setup_axes()

        x = list(range(len(self._temp_data)))
        if x:
            # 温度曲线 - 柔美红
            ax.plot(x, self._temp_data, color='#e57373', lw=2, label="温度(°C)")
            ax.fill_between(x, self._temp_data, color='#e57373', alpha=0.1)

            # 湿度曲线 - 温柔蓝
            ax.plot(x, self._humi_data, color='#689fd2', lw=2, label="湿度(%RH)")
            ax.fill_between(x, self._humi_data, color='#689fd2', alpha=0.1)

            ax.set_xlim(0, max(len(self._temp_data) - 1, 1))
        else:
            ax.set_xlim(0, 10)

        ax.set_ylim(0, 100)

        # 优雅的图例样式
        leg = ax.legend(loc="upper right", fontsize=8, frameon=True)
        if leg:
            leg.get_frame().set_facecolor('#ffffff')
            leg.get_frame().set_edgecolor('#689fd240')
            for text in leg.get_texts():
                text.set_color('#34495e')

        self.canvas.draw_idle()
