"""
农眼卫士 — 上位机主入口
PyQt5 桌面应用，采用现代深色扁平化（Slate & Emerald）风格与多设备管理逻辑
"""
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient
from config import load as load_config
from config import save as save_config
from widgets.alarm_widget import AlarmWidget
from widgets.control_widget import ControlWidget
from widgets.dashboard import DashboardWidget
from widgets.history_widget import HistoryWidget
from widgets.stats_widget import StatsWidget


class SettingsDialog(QDialog):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("连接设置")
        self.setFixedSize(450, 240)

        layout = QVBoxLayout()
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("VPS API 地址:"))
        self.url_edit = QLineEdit(cfg.get("server_url", "http://152.42.170.165"))
        h1.addWidget(self.url_edit)
        layout.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("API Key:"))
        self.key_edit = QLineEdit(cfg.get("server_api_key", "farmeye_prod_key_001"))
        h2.addWidget(self.key_edit)
        layout.addLayout(h2)

        h3 = QHBoxLayout()
        h3.addWidget(QLabel("默认设备 ID:"))
        self.device_edit = QLineEdit(cfg.get("device_id", "farmeye_guard_ws63"))
        h3.addWidget(self.device_edit)
        layout.addLayout(h3)

        h4 = QHBoxLayout()
        h4.addWidget(QLabel("刷新间隔(ms):"))
        self.interval_edit = QLineEdit(str(cfg.get("refresh_interval", 3000)))
        h4.addWidget(self.interval_edit)
        layout.addLayout(h4)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存并重连")
        save_btn.setStyleSheet(
            "background: #4cd9c0; color: #fff; padding: 8px 24px; border: none; border-radius: 6px; font-weight: bold;"
        )
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _save(self):
        self.cfg["server_url"] = self.url_edit.text().strip()
        self.cfg["server_api_key"] = self.key_edit.text().strip()
        self.cfg["device_id"] = self.device_edit.text().strip()
        try:
            self.cfg["refresh_interval"] = int(self.interval_edit.text().strip())
        except ValueError:
            pass
        save_config(self.cfg)
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.api = ApiClient(self.cfg)
        self.current_device_id = None  # None 表示全部设备

        self.setWindowTitle("农眼卫士 - IoT 上位机监控中心")
        self.setMinimumSize(1250, 800)
        self._setup_ui()
        self._setup_menu()

        # 定时更新设备列表
        self.device_timer = QTimer()
        self.device_timer.timeout.connect(self._refresh_devices_combo)
        self.device_timer.start(15000)  # 15秒刷新一次设备列表
        self._refresh_devices_combo()

    def _setup_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 左侧侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(12)

        # 标题/Logo
        title_lbl = QLabel("🌾 农眼卫士 IoT")
        title_lbl.setStyleSheet("color: #10b981; font-size: 20px; font-weight: bold; padding-bottom: 10px;")
        sidebar_layout.addWidget(title_lbl)

        # 导航按钮
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        pages = [
            ("📊  实时监控", 0),
            ("🔔  告警记录", 1),
            ("🎛  设备控制", 2),
            ("📋  历史数据", 3),
            ("📈  统计分析", 4),
        ]
        self.nav_buttons = []
        for text, index in pages:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("class", "nav-btn")
            if index == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=index: self._change_page(idx))
            self.nav_group.addButton(btn)
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #334155; max-height: 1px;")
        sidebar_layout.addWidget(line)

        # 全局设备筛选
        dev_title = QLabel("设备选择")
        dev_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold; margin-top: 4px;")
        sidebar_layout.addWidget(dev_title)

        self.device_combo = QComboBox()
        self.device_combo.addItem("🌐 全部设备", None)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        sidebar_layout.addWidget(self.device_combo)

        # API 状态指示
        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        self.api_status_dot = QLabel("●")
        self.api_status_dot.setStyleSheet("color: #e74c3c; font-size: 14px;")
        self.api_status_lbl = QLabel("API 未连接")
        self.api_status_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        status_layout.addWidget(self.api_status_dot)
        status_layout.addWidget(self.api_status_lbl)
        status_layout.addStretch()
        sidebar_layout.addLayout(status_layout)

        main_layout.addWidget(sidebar)

        # 2. 右侧主工作区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(16)

        # 右侧页眉标题
        self.header_title = QLabel("实时监控")
        self.header_title.setStyleSheet("color: #1e2a38; font-size: 24px; font-weight: bold;")
        right_layout.addWidget(self.header_title)

        # 页面容器 QStackedWidget
        self.stack = QStackedWidget()
        self.dashboard = DashboardWidget(self.api)
        self.alarm = AlarmWidget(self.api)
        self.control = ControlWidget(self.api)
        self.history = HistoryWidget(self.api)
        self.stats = StatsWidget(self.api)

        # 信号连接：双击设备表格行时，切换全局下拉框选项
        self.control.device_selected.connect(self._select_device_in_combo)

        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.alarm)
        self.stack.addWidget(self.control)
        self.stack.addWidget(self.history)
        self.stack.addWidget(self.stats)

        right_layout.addWidget(self.stack)
        main_layout.addWidget(right_panel)

        self.setCentralWidget(central_widget)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #ffffff; border-top: 1px solid rgba(104, 159, 210, 0.15); color: #7f8c8d;")
        self.status_bar.showMessage(f"API 地址: {self.api._base}")
        self.setStatusBar(self.status_bar)

    def _setup_menu(self):
        menu = self.menuBar()
        menu.setStyleSheet("background-color: #0b0f19; color: #f1f5f9; border-bottom: 1px solid #1e293b;")

        settings_action = QAction("⚙ 连接设置", self)
        settings_action.triggered.connect(self._open_settings)

        about_action = QAction("ℹ 关于", self)
        about_action.triggered.connect(lambda: QMessageBox.about(
            self, "关于", "农眼卫士 v1.1\n小麦/茶叶病虫害监控上位机系统\n现代重构版"))

        file_menu = menu.addMenu("文件")
        file_menu.addAction(settings_action)
        file_menu.addAction(about_action)

    def _change_page(self, index):
        self.stack.setCurrentIndex(index)
        titles = ["实时监控", "告警记录", "设备控制", "历史数据", "统计分析"]
        self.header_title.setText(titles[index])

    def _on_device_changed(self, index):
        device_id = self.device_combo.itemData(index)
        self.current_device_id = device_id

        # 广播给各个 widget
        for widget in [self.dashboard, self.alarm, self.control, self.history, self.stats]:
            if hasattr(widget, "set_device_filter"):
                widget.set_device_filter(device_id)

    def _select_device_in_combo(self, device_id):
        # 查找 device_id 并设置 combobox 的索引
        for i in range(self.device_combo.count()):
            if self.device_combo.itemData(i) == device_id:
                self.device_combo.setCurrentIndex(i)
                break

    def _refresh_devices_combo(self):
        res = self.api.device_list()
        if res.get("code") == 0:
            devices = res.get("data", [])
            current_selected = self.device_combo.currentData()

            self.device_combo.blockSignals(True)
            self.device_combo.clear()
            self.device_combo.addItem("🌐 全部设备", None)

            for d in devices:
                dev_id = d.get("device_id")
                dev_name = d.get("device_name") or dev_id
                online = d.get("online", False)
                status_str = "🟢" if online else "🔴"
                self.device_combo.addItem(f"{status_str} {dev_name}", dev_id)

            # 恢复之前选择的设备
            index = 0
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == current_selected:
                    index = i
                    break
            self.device_combo.setCurrentIndex(index)
            self.device_combo.blockSignals(False)

            self.api_status_dot.setText("●")
            self.api_status_dot.setStyleSheet("color: #10b981; font-size: 14px;")
            self.api_status_lbl.setText("API 已连接")
        else:
            self.api_status_dot.setText("●")
            self.api_status_dot.setStyleSheet("color: #ef4444; font-size: 14px;")
            self.api_status_lbl.setText("API 连接异常")

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg)
        if dlg.exec_() == QDialog.Accepted:
            self.api = ApiClient(self.cfg)
            self._restart()

    def _restart(self):
        # 停止已有定时器，防内存泄露
        self.device_timer.stop()
        self.dashboard.cleanup()
        self.alarm.cleanup()
        if hasattr(self.control, "cleanup"):
            self.control.cleanup()

        self._setup_ui()
        self.device_timer.start(15000)
        self._refresh_devices_combo()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 全局 QSS 样式表
    app.setStyleSheet("""
        QWidget {
            font-family: "Segoe UI", "Microsoft YaHei", "Arial";
            background-color: #f5f7fa;
            color: #34495e;
            font-size: 13px;
        }

        /* 侧边栏 QFrame */
        QFrame#sidebar {
            background-color: #ffffff;
            border-right: 1px solid rgba(104, 159, 210, 0.15);
        }

        /* 导航按钮 */
        QPushButton.nav-btn {
            background-color: transparent;
            color: #7f8c8d;
            border: none;
            border-left: 3px solid transparent;
            padding: 12px 20px;
            text-align: left;
            font-size: 14px;
            font-weight: 500;
            border-radius: 4px;
        }
        QPushButton.nav-btn:hover {
            background-color: rgba(104, 159, 210, 0.08);
            color: #689fd2;
        }
        QPushButton.nav-btn:checked {
            background-color: rgba(104, 159, 210, 0.12);
            color: #4cd9c0;
            border-left: 3px solid #4cd9c0;
            font-weight: 600;
        }

        /* 下拉选择框 */
        QComboBox {
            background-color: #ffffff;
            border: 1px solid rgba(104, 159, 210, 0.2);
            border-radius: 6px;
            padding: 6px 12px;
            color: #34495e;
            font-size: 13px;
            min-height: 24px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            border: 1px solid rgba(104, 159, 210, 0.2);
            selection-background-color: #4cd9c0;
            selection-color: #ffffff;
            color: #34495e;
            outline: none;
        }

        /* 文本框与时间控件 */
        QLineEdit, QDateTimeEdit {
            background-color: #ffffff;
            border: 1px solid rgba(104, 159, 210, 0.2);
            border-radius: 6px;
            padding: 6px 12px;
            color: #34495e;
        }
        QLineEdit:focus, QDateTimeEdit:focus {
            border: 1px solid #4cd9c0;
            outline: none;
        }

        /* 标准按钮 */
        QPushButton {
            background-color: #4cd9c0;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #3bc4ab;
        }
        QPushButton:pressed {
            background-color: #2eb097;
        }
        QPushButton:disabled {
            background-color: #bdc3c7;
            color: #7f8c8d;
        }

        /* 滚动条 */
        QScrollBar:vertical {
            border: none;
            background: #f5f7fa;
            width: 8px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: rgba(104, 159, 210, 0.2);
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(104, 159, 210, 0.35);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        /* 表格控件 */
        QTableWidget {
            background-color: #ffffff;
            border: 1px solid rgba(104, 159, 210, 0.15);
            gridline-color: rgba(104, 159, 210, 0.1);
            border-radius: 8px;
            color: #34495e;
            outline: none;
        }
        QTableWidget::item {
            padding: 10px;
            border-bottom: 1px solid rgba(104, 159, 210, 0.1);
        }
        QTableWidget::item:selected {
            background-color: rgba(104, 159, 210, 0.10);
            color: #689fd2;
            font-weight: 500;
        }
        QHeaderView::section {
            background-color: #edf3f7;
            color: #1e2a38;
            padding: 10px;
            border: none;
            border-bottom: 2px solid rgba(104, 159, 210, 0.15);
            font-weight: bold;
        }

        /* 框分组 */
        QGroupBox {
            border: 1px solid rgba(104, 159, 210, 0.15);
            border-radius: 8px;
            margin-top: 1.2em;
            font-weight: bold;
            color: #689fd2;
            padding-top: 12px;
            background-color: rgba(255, 255, 255, 0.4);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 4px;
            color: #689fd2;
        }
    """)

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
