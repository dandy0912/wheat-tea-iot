"""
上位机配置管理
连接 VPS 后端（/api/v1/）
"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "server_url": "http://127.0.0.1:8000",
    "server_api_key": "",
    "refresh_interval": 3000,
    "device_id": "wheat_001",
}


def load():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return dict(DEFAULT_CONFIG)


def save(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def api_base(cfg):
    return cfg["server_url"] + "/api/v1"
