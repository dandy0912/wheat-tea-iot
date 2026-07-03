"""
告警记录管理
对接 VPS /api/v1/disease/list，并支持设备过滤与表格展示优化 (日系明亮配色)
"""
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AlarmWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.current_device_id = None  # None 表示全部设备

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 工具栏
        tool_bar = QHBoxLayout()
        tool_bar.addWidget(QLabel("严重程度:"))
        self.severity_cb = QComboBox()
        self.severity_cb.addItems(["全部", "Mild", "Moderate", "Severe"])
        self.severity_cb.currentTextChanged.connect(self._load)
        tool_bar.addWidget(self.severity_cb)
        tool_bar.addStretch()

        self.count_label = QLabel("共 0 条")
        self.count_label.setStyleSheet("color: #7f8c8d; font-size: 13px; font-weight: 500;")
        tool_bar.addWidget(self.count_label)
        layout.addLayout(tool_bar)

        # 告警数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["时间", "设备 ID", "作物", "病害类型", "置信度", "严重程度", "风险等级", "防治处置"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.setLayout(layout)

        # 轮询定时器
        interval = self.api.cfg.get("refresh_interval", 5000)
        self.timer = QTimer()
        self.timer.timeout.connect(self._load)
        self.timer.start(interval)

        self._load()

    def set_device_filter(self, device_id):
        if self.current_device_id != device_id:
            self.current_device_id = device_id
            self._load()

    def cleanup(self):
        self.timer.stop()

    def _load(self):
        sev = self.severity_cb.currentText()
        severity = sev if sev != "全部" else None

        res = self.api.alarm_list(
            page=1,
            page_size=100,
            severity=severity,
            device_id=self.current_device_id
        )

        if res.get("code") != 0:
            self.count_label.setText(f"加载失败: {res.get('msg') or res.get('message') or '未知错误'}")
            self.count_label.setStyleSheet("color: #e57373;")
            return

        records = res.get("data", {}).get("records", [])
        total = res.get("data", {}).get("pagination", {}).get("total", 0)
        self.count_label.setText(f"共 {total} 条记录")
        self.count_label.setStyleSheet("color: #7f8c8d;")

        self.table.setRowCount(len(records))
        colors = {
            "Mild": "#ffb74d",      # 暖橙黄
            "Moderate": "#f48fb1",  # 柔美粉
            "Severe": "#e57373"     # 柔美红
        }

        for row, d in enumerate(records):
            # 时间
            self.table.setItem(row, 0, QTableWidgetItem((d.get("timestamp") or "")[:19]))
            # 设备 ID
            self.table.setItem(row, 1, QTableWidgetItem(d.get("device_id", "")))
            # 作物
            crop = d.get("crop_type", "")
            crop_map = {"wheat": "小麦 🌾", "tea": "茶叶 🌿"}
            self.table.setItem(row, 2, QTableWidgetItem(crop_map.get(crop, crop)))
            # 病害
            disease = d.get("disease_type", "")
            disease_map = {
                "rust": "锈病", "powdery_mildew": "白粉病",
                "anthracnose": "炭疽病", "leafhopper": "小绿叶蝉"
            }
            self.table.setItem(row, 3, QTableWidgetItem(disease_map.get(disease, disease)))
            # 置信度
            conf = d.get("max_conf", 0)
            self.table.setItem(row, 4, QTableWidgetItem(f"{conf*100:.1f}%" if conf else "--"))

            # 严重程度 (带背景色的 Badge)
            sev_str = d.get("severity", "")
            sev_item = QTableWidgetItem(sev_str)
            sev_item.setBackground(QColor(colors.get(sev_str, "#90a4ae")))
            sev_item.setForeground(Qt.white)
            sev_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, sev_item)

            # 风险等级
            risk = d.get("linkage_risk_level", "")
            risk_map = {"low": "低风险", "medium": "中风险", "high": "高风险"}
            self.table.setItem(row, 6, QTableWidgetItem(risk_map.get(risk, risk or "--")))
            # 防治处置
            action = d.get("action_taken", "")
            action_map = {
                "manual_inspect": "人工巡检 🔍",
                "auto_spray": "自动喷洒 🌫️",
                "spray ON": "开启喷雾 🌫️",
                "none": "无特别处置"
            }
            self.table.setItem(row, 7, QTableWidgetItem(action_map.get(action, action or "--")))

            # 设置文字居中对齐
            for col in range(8):
                if col != 5:
                    item = self.table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
