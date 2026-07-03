"""
告警记录管理
对接 VPS /api/v1/disease/list
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel, QComboBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor


class AlarmWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)

        tool_bar = QHBoxLayout()
        tool_bar.addWidget(QLabel("严重程度:"))
        self.severity_cb = QComboBox()
        self.severity_cb.addItems(["全部", "Mild", "Moderate", "Severe"])
        self.severity_cb.currentTextChanged.connect(self._load)
        tool_bar.addWidget(self.severity_cb)
        tool_bar.addStretch()
        self.count_label = QLabel("共 0 条")
        self.count_label.setStyleSheet("color: #888;")
        tool_bar.addWidget(self.count_label)
        layout.addLayout(tool_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["时间", "作物", "病害", "置信度", "严重程度", "风险等级", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self._load)
        self.timer.start(5000)
        self._load()

    def _load(self):
        sev = self.severity_cb.currentText()
        params = {"page": 1, "page_size": 100}
        if sev != "全部":
            params["severity"] = sev
        res = self.api.raw_get("/disease/list", params)
        if res.get("code") != 0:
            return
        records = res.get("data", {}).get("records", [])
        total = res.get("data", {}).get("pagination", {}).get("total", 0)
        self.count_label.setText(f"共 {total} 条")

        self.table.setRowCount(len(records))
        colors = {"Mild": "#f39c12", "Moderate": "#e67e22", "Severe": "#e74c3c"}
        for row, d in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(
                (d.get("timestamp") or "")[:19]))
            self.table.setItem(row, 1, QTableWidgetItem(d.get("crop_type", "")))
            self.table.setItem(row, 2, QTableWidgetItem(d.get("disease_type", "")))
            conf = d.get("confidence", 0)
            self.table.setItem(row, 3, QTableWidgetItem(
                f"{conf*100:.1f}%" if conf else "--"))
            sev_item = QTableWidgetItem(d.get("severity", ""))
            sev_item.setBackground(QColor(colors.get(sev_item.text(), "#888")))
            sev_item.setForeground(Qt.white)
            self.table.setItem(row, 4, sev_item)
            self.table.setItem(row, 5, QTableWidgetItem(
                d.get("linkage_risk_level", "") or "--"))
            self.table.setItem(row, 6, QTableWidgetItem(
                d.get("action_taken", "") or "--"))
