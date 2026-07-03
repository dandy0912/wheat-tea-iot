"""
历史数据查询
对接 VPS /api/v1/sensor/history
"""
from PyQt5.QtCore import QDateTime
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
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("起始:"))
        self.start_dt = QDateTimeEdit()
        self.start_dt.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.start_dt.setDisplayFormat("yyyy-MM-ddThh:mm:ss")
        time_layout.addWidget(self.start_dt)
        time_layout.addWidget(QLabel("结束:"))
        self.end_dt = QDateTimeEdit()
        self.end_dt.setDateTime(QDateTime.currentDateTime())
        self.end_dt.setDisplayFormat("yyyy-MM-ddThh:mm:ss")
        time_layout.addWidget(self.end_dt)
        query_btn = QPushButton("查询")
        query_btn.setStyleSheet("background: #1a6b3c; color: #fff; border: none; "
                                "padding: 6px 20px; border-radius: 6px;")
        query_btn.clicked.connect(self._query)
        time_layout.addWidget(query_btn)
        time_layout.addStretch()
        layout.addLayout(time_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["时间", "温度(°C)", "湿度(%)", "光照", "CO₂",
             "氮(N)", "磷(P)", "钾(K)", "距离(cm)", "告警标志"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.count_label = QLabel("请选择时间范围后查询")
        self.count_label.setStyleSheet("color: #888; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.count_label)

        self.setLayout(layout)

    def _query(self):
        start = self.start_dt.dateTime().toString("yyyy-MM-ddThh:mm:ss")
        end = self.end_dt.dateTime().toString("yyyy-MM-ddThh:mm:ss")
        device_id = self.api.cfg.get("device_id", "farmeye_guard_ws63")
        res = self.api.history(device_id, start=start, end=end)
        if res.get("code") != 0:
            self.count_label.setText(f"查询失败: {res.get('msg', '')}")
            return
        records = res.get("data", {}).get("records", [])
        self.table.setRowCount(len(records))
        for row, d in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(
                (d.get("timestamp") or "")[:19]))
            self.table.setItem(row, 1, QTableWidgetItem(str(d.get("temperature", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(d.get("humidity", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(d.get("light", ""))))
            self.table.setItem(row, 4, QTableWidgetItem(str(d.get("co2", ""))))
            self.table.setItem(row, 5, QTableWidgetItem(str(d.get("soil_n", ""))))
            self.table.setItem(row, 6, QTableWidgetItem(str(d.get("soil_p", ""))))
            self.table.setItem(row, 7, QTableWidgetItem(str(d.get("soil_k", ""))))
            self.table.setItem(row, 8, QTableWidgetItem(str(d.get("distance", ""))))
            self.table.setItem(row, 9, QTableWidgetItem(str(d.get("alarm_flag", ""))))
        self.count_label.setText(f"共 {len(records)} 条记录")
