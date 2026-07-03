"""
病虫害统计分析
对接 VPS /api/v1/disease/stats，并支持单设备前端数据聚合计算与美化展示
饼环图: 按严重程度 / 按作物 / 按病害类型 (日系明亮配色)
"""
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class MplCanvas(FigureCanvas):
    def __init__(self, figsize=(5, 4.5)):
        self.fig = Figure(figsize=figsize, dpi=100)
        self.fig.patch.set_facecolor('#f5f7fa')  # 明亮背景
        super().__init__(self.fig)


class StatsWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.current_device_id = None  # None 表示全部设备

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 顶部工具栏
        tool_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新统计")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4cd9c0;
                color: #ffffff;
                border: none;
                padding: 8px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3bc4ab;
            }
        """)
        refresh_btn.clicked.connect(self._refresh)
        tool_layout.addWidget(refresh_btn, alignment=Qt.AlignLeft)
        tool_layout.addStretch()
        layout.addLayout(tool_layout)

        # 图表展示区域
        chart_layout = QHBoxLayout()
        chart_layout.setSpacing(12)

        from PyQt5.QtWidgets import QSizePolicy
        self.canvas_severity = MplCanvas()
        self.canvas_crop = MplCanvas()
        self.canvas_disease = MplCanvas()

        for canvas in [self.canvas_severity, self.canvas_crop, self.canvas_disease]:
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        chart_layout.addWidget(self.canvas_severity)
        chart_layout.addWidget(self.canvas_crop)
        chart_layout.addWidget(self.canvas_disease)
        layout.addLayout(chart_layout)

        # 底部统计显示（修改为单行，放在最下面）
        summary_layout = QHBoxLayout()
        summary_layout.setContentsMargins(16, 8, 16, 16)
        self.total_label = QLabel("全部设备总警告数: --")
        self.total_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #4cd9c0;")
        summary_layout.addWidget(self.total_label)
        summary_layout.addStretch()
        layout.addLayout(summary_layout)

        self.setLayout(layout)
        self._refresh()

    def set_device_filter(self, device_id):
        if self.current_device_id != device_id:
            self.current_device_id = device_id
            self._refresh()

    def _refresh(self):
        # 1. 判断是否需要前端计算统计（因为后端API不支持设备ID过滤）
        if self.current_device_id is None:
            # --- 全部设备模式 (调用后端统计 API) ---
            res = self.api.alarm_stats()
            if res.get("code") == 0:
                data = res.get("data", {})
                total = data.get("total_detections", 0)
                self.total_label.setText(f"全部设备总警告数: {total}")
                self.total_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #4cd9c0;")
            else:
                data = {}
                self.total_label.setText(f"加载失败: {res.get('msg') or res.get('message') or '未知错误'}")
                self.total_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #e57373;")
        else:
            # --- 单设备模式 (拉取历史记录并在前端统计) ---
            res = self.api.alarm_list(page=1, page_size=1000, device_id=self.current_device_id)
            if res.get("code") == 0:
                records = res.get("data", {}).get("records", [])

                # 初始化统计结构
                by_crop = {"wheat": 0, "tea": 0}
                by_severity = {"Mild": 0, "Moderate": 0, "Severe": 0}
                by_disease = {"rust": 0, "powdery_mildew": 0, "anthracnose": 0, "leafhopper": 0}

                for r in records:
                    crop = r.get("crop_type")
                    if crop in by_crop:
                        by_crop[crop] += 1

                    sev = r.get("severity")
                    if sev in by_severity:
                        by_severity[sev] += 1

                    dis = r.get("disease_type")
                    if dis in by_disease:
                        by_disease[dis] += 1

                data = {
                    "total_detections": len(records),
                    "by_crop": by_crop,
                    "by_severity": by_severity,
                    "by_disease": by_disease
                }
                self.total_label.setText(f"设备 [{self.current_device_id}] 总警告数: {len(records)}")
                self.total_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #4cd9c0;")
            else:
                data = {}
                self.total_label.setText(f"加载单设备数据失败: {res.get('msg') or res.get('message') or '未知错误'}")
                self.total_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #e57373;")

        # 2. 映射翻译并绘制环形图
        # 严重程度
        sev_raw = data.get("by_severity", {})
        sev_map = {"Mild": "轻度", "Moderate": "中度", "Severe": "重度"}
        sev_translated = {sev_map.get(k, k): v for k, v in sev_raw.items()}
        sev_colors = ["#ffb74d", "#f48fb1", "#e57373"]  # 暖橙黄 / 柔美粉 / 柔美红
        self._donut_chart(self.canvas_severity, sev_translated, "按严重程度", sev_colors)

        # 作物类型
        crop_raw = data.get("by_crop", {})
        crop_map = {"wheat": "小麦", "tea": "茶叶"}
        crop_translated = {crop_map.get(k, k): v for k, v in crop_raw.items()}
        crop_colors = ["#689fd2", "#4cd9c0"]  # 温柔蓝 / 薄荷青
        self._donut_chart(self.canvas_crop, crop_translated, "按作物类型", crop_colors)

        # 病害类型
        dis_raw = data.get("by_disease", {})
        dis_map = {"rust": "锈病", "powdery_mildew": "白粉病", "anthracnose": "炭疽病", "leafhopper": "小绿叶蝉"}
        dis_translated = {dis_map.get(k, k): v for k, v in dis_raw.items()}
        dis_colors = ["#b39ddb", "#4cd9c0", "#f48fb1", "#689fd2"]  # 淡紫 / 薄荷青 / 柔美粉 / 温柔蓝
        self._donut_chart(self.canvas_disease, dis_translated, "按病害类型", dis_colors)

    def _donut_chart(self, canvas, data, title, colors=None):
        canvas.fig.clear()
        ax = canvas.fig.add_subplot(111)
        ax.set_facecolor('#f5f7fa')

        # 过滤掉数值为 0 的项
        data = {k: v for k, v in data.items() if v > 0}

        if not data:
            ax.text(0.5, 0.5, "暂无分析数据", ha="center", va="center", fontsize=11, color="#7f8c8d")
            ax.set_title(title, fontsize=12, color='#1e2a38', weight='bold')
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            # 调整图表子图边距，为顶部标题和底部图例留出足够空间，防止遮挡
            canvas.fig.subplots_adjust(top=0.85, bottom=0.28, left=0.1, right=0.9)

            labels = list(data.keys())
            sizes = list(data.values())
            if not colors:
                colors = ["#689fd2", "#4cd9c0", "#ffb74d", "#f48fb1", "#e57373", "#b39ddb"]

            # 绘制环形图 (width=0.35 实现内空，radius=1.1 放大圆环大小)
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=None,
                autopct="%1.0f%%",
                colors=colors[:len(labels)],
                startangle=90,
                pctdistance=0.8,
                radius=1.1,
                wedgeprops=dict(width=0.35, edgecolor='#f5f7fa', linewidth=2)
            )

            # 内嵌比例数值样式
            for autotext in autotexts:
                autotext.set_color('#ffffff')
                autotext.set_fontsize(8)
                autotext.set_weight('bold')

            # 极简化精美图例 (bbox_to_anchor 稍微向下移动以防止与圆环重合，ncol=2 保持美观)
            ax.legend(
                wedges,
                [f"{lb} ({s})" for lb, s in zip(labels, sizes)],
                loc="center",
                bbox_to_anchor=(0.5, -0.20),
                ncol=2,
                fontsize=8,
                frameon=True
            )

            leg = ax.get_legend()
            if leg:
                leg.get_frame().set_facecolor('#ffffff')
                leg.get_frame().set_edgecolor('#689fd240')
                for text in leg.get_texts():
                    text.set_color('#34495e')

            ax.set_title(title, fontsize=12, color='#1e2a38', weight='bold', pad=10)

        canvas.draw_idle()
