"""
设备控制面板
对接 VPS /api/v1/device/list + /api/v1/command/send + /api/v1/command/logs
并支持多设备全局联动、状态智能初始化及交互动作 (日系明亮配色)
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

DEVICES = [
    ("irrig", "灌溉器", "#689fd2", "💧"),      # 温柔蓝
    ("light", "补光灯", "#ffb74d", "💡"),      # 暖橙黄
    ("spray", "喷雾器", "#4cd9c0", "🌫️"),      # 薄荷青
    ("fertilize", "施肥器", "#b39ddb", "🌱"),    # 淡紫色
]


class DeviceBtn(QPushButton):
    def __init__(self, cmd_id, name, color, icon):
        super().__init__()
        self._cmd_id = cmd_id
        self._name = name
        self._color = color
        self._icon = icon
        self._on = False
        self.setText(f"{icon} {name}\n🔴 已关闭")
        self.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #7f8c8d;
                border: 1px solid rgba(104, 159, 210, 0.25);
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(104, 159, 210, 0.08);
            }
        """)


class ControlWidget(QWidget):
    device_selected = pyqtSignal(str)  # 双击表格行时发射此信号，通知主窗口切换全局设备

    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.current_device_id = None  # None 表示全部设备

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 4个主控制开关
        self.ctrl_box = QGroupBox("远程控制器")
        ctrl_layout = QVBoxLayout(self.ctrl_box)

        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(12)
        self._btns = {}

        for cmd_id, name, color, icon in DEVICES:
            btn = DeviceBtn(cmd_id, name, color, icon)
            btn.clicked.connect(lambda checked, c=cmd_id, n=name: self._control(c, n))
            self._btns[name] = btn
            self.btn_layout.addWidget(btn)

        ctrl_layout.addLayout(self.btn_layout)

        # 禁用提示
        self.tip_lbl = QLabel("⚠️ 请在左侧选择特定设备以启用控制功能")
        self.tip_lbl.setStyleSheet("color: #ffb74d; font-size: 13px; font-weight: bold; padding: 4px;")
        self.tip_lbl.setVisible(True)
        ctrl_layout.addWidget(self.tip_lbl)

        layout.addWidget(self.ctrl_box)

        # 设备列表
        status_box = QGroupBox("在线设备列表 (双击某行可快速选定该设备)")
        status_layout = QVBoxLayout()
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(4)
        self.status_table.setHorizontalHeaderLabels(["设备 ID", "设备名称", "在线状态", "最后在线时间"])
        self.status_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.status_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.status_table.verticalHeader().setVisible(False)
        self.status_table.doubleClicked.connect(self._on_device_double_clicked)
        status_layout.addWidget(self.status_table)
        status_box.setLayout(status_layout)
        layout.addWidget(status_box)

        # 操作日志
        log_box = QGroupBox("操作执行日志")
        log_layout = QVBoxLayout()
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(5)
        self.log_table.setHorizontalHeaderLabels(["下发时间", "设备 ID", "控制指令", "操作来源", "执行结果"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.verticalHeader().setVisible(False)
        log_layout.addWidget(self.log_table)
        log_box.setLayout(log_layout)
        layout.addWidget(log_box)

        self.setLayout(layout)

        self._refresh_logs()
        self._refresh_devices()
        self._update_ui_state()

    def set_device_filter(self, device_id):
        if self.current_device_id != device_id:
            self.current_device_id = device_id
            self._update_ui_state()
            self._init_actuator_states(device_id)
            self._refresh_logs()

    def _update_ui_state(self):
        has_device = self.current_device_id is not None
        self.tip_lbl.setVisible(not has_device)
        for btn in self._btns.values():
            btn.setEnabled(has_device)
            if not has_device:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #eef3f7;
                        color: #90a4ae;
                        border: 1px dashed rgba(104, 159, 210, 0.15);
                        border-radius: 8px;
                        padding: 12px;
                        font-size: 14px;
                    }
                """)

    def _init_actuator_states(self, device_id):
        if not device_id:
            for btn in self._btns.values():
                btn._on = False
                self._update_btn_style(btn)
            return

        res = self.api.command_logs(page=1, page_size=40, device_id=device_id)
        if res.get("code") == 0:
            records = res.get("data", {}).get("records", [])
            found = {}
            for r in records:
                cmd = r.get("command", "")
                parts = cmd.split(" ")
                if len(parts) == 2:
                    actuator, state = parts[0], parts[1]
                    if actuator not in found:
                        found[actuator] = (state == "ON")

            actuator_to_name = {
                "irrig": "灌溉器",
                "light": "补光灯",
                "spray": "喷雾器",
                "fertilize": "施肥器"
            }
            for actuator, name in actuator_to_name.items():
                btn = self._btns[name]
                btn._on = found.get(actuator, False)
                self._update_btn_style(btn)
        else:
            for btn in self._btns.values():
                btn._on = False
                self._update_btn_style(btn)

    def _update_btn_style(self, btn):
        status_text = "运行中" if btn._on else "已关闭"
        icon_dot = "🟢" if btn._on else "🔴"
        btn.setText(f"{btn._icon} {btn._name}\n{icon_dot} {status_text}")

        if btn._on:
            bg = btn._color
            color = "#ffffff"
        else:
            bg = "#ffffff"
            color = "#34495e"

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid rgba(104, 159, 210, 0.25);
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {btn._color if not btn._on else "rgba(104, 159, 210, 0.08)"};
            }}
        """)

    def _control(self, cmd_id, name):
        if not self.current_device_id:
            return

        btn = self._btns[name]
        cmd = f"{cmd_id} OFF" if btn._on else f"{cmd_id} ON"

        res = self.api.device_control(self.current_device_id, cmd)
        if res.get("code") == 0:
            btn._on = not btn._on
            self._update_btn_style(btn)
        else:
            QMessageBox.warning(
                self,
                "控制失败",
                f"指令下发失败: {res.get('msg') or res.get('message') or '未知错误'}\n(错误码: {res.get('code')})"
            )
        self._refresh_logs()

    def _refresh_logs(self):
        res = self.api.command_logs(page=1, page_size=20, device_id=self.current_device_id)
        if res.get("code") != 0:
            return
        records = res.get("data", {}).get("records", [])
        self.log_table.setRowCount(len(records))
        for row, d in enumerate(records):
            self.log_table.setItem(row, 0, QTableWidgetItem((d.get("timestamp") or "")[:19]))
            self.log_table.setItem(row, 1, QTableWidgetItem(d.get("device_id", "")))
            self.log_table.setItem(row, 2, QTableWidgetItem(d.get("command", "")))
            self.log_table.setItem(row, 3, QTableWidgetItem(d.get("source", "")))

            result_code = d.get("result_code", 0)
            res_item = QTableWidgetItem("成功" if result_code == 0 else d.get("result_msg", "失败"))
            if result_code == 0:
                res_item.setForeground(QColor("#4cd9c0"))  # 薄荷青
            else:
                res_item.setForeground(QColor("#e57373"))  # 柔美红
            self.log_table.setItem(row, 4, res_item)

            for col in range(5):
                item = self.log_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _refresh_devices(self):
        res = self.api.device_list()
        if res.get("code") != 0:
            return
        devices = res.get("data", [])
        self.status_table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            self.status_table.setItem(row, 0, QTableWidgetItem(d.get("device_id", "")))
            self.status_table.setItem(row, 1, QTableWidgetItem(d.get("device_name", "") or "--"))

            online = d.get("online", False)
            status_item = QTableWidgetItem("在线 🟢" if online else "离线 🔴")
            if online:
                status_item.setForeground(QColor("#4cd9c0"))
            else:
                status_item.setForeground(QColor("#e57373"))
            self.status_table.setItem(row, 2, status_item)

            self.status_table.setItem(row, 3, QTableWidgetItem((d.get("last_seen") or "")[:19]))

            for col in range(4):
                item = self.status_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _on_device_double_clicked(self, index):
        row = index.row()
        device_id_item = self.status_table.item(row, 0)
        if device_id_item:
            device_id = device_id_item.text()
            self.device_selected.emit(device_id)
