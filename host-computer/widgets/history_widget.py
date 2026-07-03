"""
历史数据查询
对接 VPS /api/v1/sensor/history，支持设备过滤限制与界面美化 (日系明亮配色)
"""
from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDateTimeEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class HistoryWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.current_device_id = None  # None 表示全部设备

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 筛选工具栏
        time_layout = QHBoxLayout()
        time_layout.setSpacing(8)

        time_layout.addWidget(QLabel("起始时间:"))
        self.start_dt = QDateTimeEdit()
        self.start_dt.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.start_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_dt.setCalendarPopup(True)
        time_layout.addWidget(self.start_dt)

        time_layout.addWidget(QLabel("结束时间:"))
        self.end_dt = QDateTimeEdit()
        self.end_dt.setDateTime(QDateTime.currentDateTime())
        self.end_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_dt.setCalendarPopup(True)
        time_layout.addWidget(self.end_dt)

        self.query_btn = QPushButton("🔍 查询")
        self.query_btn.setStyleSheet("""
            QPushButton {
                background-color: #4cd9c0;
                color: #ffffff;
                border: none;
                padding: 6px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3bc4ab;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        self.query_btn.clicked.connect(self._query)
        time_layout.addWidget(self.query_btn)
        time_layout.addStretch()
        layout.addLayout(time_layout)

        # 历史数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["采集时间", "温度(°C)", "湿度(%RH)", "光照(lux)", "CO₂(ppm)",
             "土壤氮(N)", "土壤磷(P)", "土壤钾(K)", "监测距离(cm)", "告警标志"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # 提示与结果条数
        self.count_label = QLabel("请选择时间范围后查询")
        self.count_label.setStyleSheet("color: #7f8c8d; font-size: 13px; font-weight: 500; padding: 4px 0;")
        layout.addWidget(self.count_label)

        self.setLayout(layout)
        self._update_state()

    def set_device_filter(self, device_id):
        if self.current_device_id != device_id:
            self.current_device_id = device_id
            self._update_state()

    def _update_state(self):
        has_device = self.current_device_id is not None
        self.query_btn.setEnabled(has_device)
        self.table.setRowCount(0)

        if not has_device:
            self.count_label.setText("⚠️ 请在左侧选择具体设备后再查询历史数据")
            self.count_label.setStyleSheet("color: #ffb74d; font-weight: bold;")
        else:
            self.count_label.setText("就绪：请设定时间范围并点击查询")
            self.count_label.setStyleSheet("color: #7f8c8d;")

    def _query(self):
        if not self.current_device_id:
            return

        start = self.start_dt.dateTime().toString("yyyy-MM-ddThh:mm:ss")
        end = self.end_dt.dateTime().toString("yyyy-MM-ddThh:mm:ss")

        res = self.api.history(self.current_device_id, start=start, end=end)

        if res.get("code") != 0:
            self.count_label.setText(f"查询失败: {res.get('msg') or res.get('message') or '未知错误'}")
            self.count_label.setStyleSheet("color: #e57373; font-weight: bold;")
            return

        records = res.get("data", {}).get("records", [])
        self.table.setRowCount(len(records))

        for row, d in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem((d.get("timestamp") or "")[:19]))
            self.table.setItem(row, 1, QTableWidgetItem(f"{d.get('temperature', '--')}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{d.get('humidity', '--')}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{d.get('light', '--')}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{d.get('co2', '--')}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{d.get('soil_n', '--')}"))
            self.table.setItem(row, 6, QTableWidgetItem(f"{d.get('soil_p', '--')}"))
            self.table.setItem(row, 7, QTableWidgetItem(f"{d.get('soil_k', '--')}"))
            self.table.setItem(row, 8, QTableWidgetItem(f"{d.get('distance', '--')}"))

            alarm = d.get("alarm_flag", 0)
            alarm_item = QTableWidgetItem(str(alarm))
            if alarm > 0:
                alarm_item.setForeground(QColor("#e57373"))
                alarm_item.setText(f"⚠ {alarm}")
            else:
                alarm_item.setText("正常")
                alarm_item.setForeground(QColor("#4cd9c0"))
            self.table.setItem(row, 9, alarm_item)

            for col in range(10):
                item = self.table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self.count_label.setText(f"共查询到 {len(records)} 条历史记录")
        self.count_label.setStyleSheet("color: #4cd9c0; font-weight: bold;")
