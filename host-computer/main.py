"""
农眼卫士 — 上位机主入口
PyQt5 桌面应用，对接 VPS 后端
"""
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget,
                             QMenuBar, QAction, QDialog, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QMessageBox, QStatusBar)
from PyQt5.QtCore import Qt

from config import load as load_config, save as save_config
from api_client import ApiClient
from widgets.dashboard import DashboardWidget
from widgets.alarm_widget import AlarmWidget
from widgets.control_widget import ControlWidget
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
        self.url_edit = QLineEdit(cfg.get("server_url", "http://127.0.0.1:8000"))
        h1.addWidget(self.url_edit)
        layout.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("API Key:"))
        self.key_edit = QLineEdit(cfg.get("server_api_key", ""))
        h2.addWidget(self.key_edit)
        layout.addLayout(h2)

        h3 = QHBoxLayout()
        h3.addWidget(QLabel("设备 ID:"))
        self.device_edit = QLineEdit(cfg.get("device_id", "wheat_001"))
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
            "background: #1a6b3c; color: #fff; padding: 8px 24px; border: none; border-radius: 6px;")
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

        self.setWindowTitle("农眼卫士 - 上位机监控系统")
        self.setMinimumSize(1200, 750)
        self._setup_ui()
        self._setup_menu()

    def _setup_ui(self):
        self.tabs = QTabWidget()
        self.tabs.addTab(DashboardWidget(self.api), "📊 实时监控")
        self.tabs.addTab(AlarmWidget(self.api), "🔔 告警记录")
        self.tabs.addTab(ControlWidget(self.api), "🎛 设备控制")
        self.tabs.addTab(HistoryWidget(self.api), "📋 历史数据")
        self.tabs.addTab(StatsWidget(self.api), "📈 统计分析")
        self.setCentralWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.status_bar.showMessage(f"API: {self.api._base}")
        self.setStatusBar(self.status_bar)

    def _setup_menu(self):
        menu = self.menuBar()
        settings_action = QAction("⚙ 连接设置", self)
        settings_action.triggered.connect(self._open_settings)
        about_action = QAction("ℹ 关于", self)
        about_action.triggered.connect(lambda: QMessageBox.about(
            self, "关于", "农眼卫士 v1.0\n小麦茶叶病虫害监测上位机\n实训项目"))
        file_menu = menu.addMenu("文件")
        file_menu.addAction(settings_action)
        file_menu.addAction(about_action)

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg)
        if dlg.exec_() == QDialog.Accepted:
            self.api = ApiClient(self.cfg)
            self._restart()

    def _restart(self):
        self.tabs.clear()
        self._setup_ui()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
