"""
设备控制面板
对接 VPS /api/v1/device/list + /api/v1/command/send + /api/v1/command/logs
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# API 指令格式: {cmd} ON / {cmd} OFF（空格分隔）
DEVICES = [
    ("irrig", "灌溉器", "#3498db", "💧"),
    ("light", "补光灯", "#f39c12", "💡"),
    ("spray", "喷雾器", "#2ecc71", "🌫"),
    ("fertilize", "施肥器", "#9b59b6", "🌱"),
]


class DeviceBtn(QPushButton):
    def __init__(self, cmd_id, name, color, icon):
        super().__init__(f"🔴  打开{name}")
        self._cmd_id = cmd_id
        self._name = name
        self._color = color
        self._on = False
        self.setStyleSheet(f"""
            QPushButton {{ background: {color}; color: #fff; border: none;
                           border-radius: 10px; padding: 20px; font-size: 14px; }}
        """)


class ControlWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(16)
        self._btns = {}
        for cmd_id, name, color, icon in DEVICES:
            btn = DeviceBtn(cmd_id, name, color, icon)
            btn.clicked.connect(lambda checked, c=cmd_id, n=name: self._control(c, n))
            self._btns[name] = btn
            btn_grid.addWidget(btn)
        layout.addLayout(btn_grid)

        status_box = QGroupBox("设备列表")
        status_layout = QVBoxLayout()
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(4)
        self.status_table.setHorizontalHeaderLabels(["设备 ID", "名称", "在线状态", "最后在线"])
        self.status_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.status_table.verticalHeader().setVisible(False)
        status_layout.addWidget(self.status_table)
        status_box.setLayout(status_layout)
        layout.addWidget(status_box)

        log_box = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(5)
        self.log_table.setHorizontalHeaderLabels(["时间", "设备", "指令", "来源", "结果"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.verticalHeader().setVisible(False)
        log_layout.addWidget(self.log_table)
        log_box.setLayout(log_layout)
        layout.addWidget(log_box)

        self.setLayout(layout)

        self._refresh_logs()
        self._refresh_devices()

    def _control(self, cmd_id, name):
        btn = self._btns[name]
        cmd = f"{cmd_id} OFF" if btn._on else f"{cmd_id} ON"
        device_id = self.api.cfg.get("device_id", "farmeye_guard_ws63")
        res = self.api.device_control(device_id, cmd)
        if res.get("code") == 0:
            btn._on = not btn._on
            icon = "🟢" if btn._on else "🔴"
            action = "关闭" if btn._on else "打开"
            btn.setText(f"{icon}  {action}{name}")
            bg = "#e74c3c" if btn._on else btn._color
            btn.setStyleSheet(f"""
                QPushButton {{ background: {bg}; color: #fff; border: none;
                               border-radius: 10px; padding: 20px; font-size: 14px; }}
            """)
        self._refresh_logs()

    def _refresh_logs(self):
        res = self.api.command_logs(page=1, page_size=20)
        if res.get("code") != 0:
            return
        records = res.get("data", {}).get("records", [])
        self.log_table.setRowCount(len(records))
        for row, d in enumerate(records):
            self.log_table.setItem(row, 0, QTableWidgetItem(
                (d.get("timestamp") or "")[:19]))
            self.log_table.setItem(row, 1, QTableWidgetItem(d.get("device_id", "")))
            self.log_table.setItem(row, 2, QTableWidgetItem(d.get("command", "")))
            self.log_table.setItem(row, 3, QTableWidgetItem(d.get("source", "")))
            self.log_table.setItem(row, 4, QTableWidgetItem(
                "成功" if d.get("result_code") == 0 else d.get("result_msg", "")))

    def _refresh_devices(self):
        res = self.api.device_list()
        if res.get("code") != 0:
            return
        devices = res.get("data", [])
        self.status_table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            self.status_table.setItem(row, 0, QTableWidgetItem(d.get("device_id", "")))
            self.status_table.setItem(row, 1, QTableWidgetItem(
                d.get("device_name", "") or "--"))
            online = d.get("online", False)
            status_item = QTableWidgetItem("在线" if online else "离线")
            status_item.setForeground(Qt.GlobalColor.green if online else Qt.GlobalColor.red)
            self.status_table.setItem(row, 2, status_item)
            self.status_table.setItem(row, 3, QTableWidgetItem(
                (d.get("last_seen") or "")[:19]))

