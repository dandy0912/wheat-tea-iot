"""
API 客户端 — 对接 VPS 后端（/api/v1/）
"""
import requests
from config import api_base


class ApiClient:
    def __init__(self, cfg):
        self.cfg = cfg
        self._base = api_base(cfg)
        self._headers = {}
        if cfg.get("server_api_key"):
            self._headers["X-Api-Key"] = cfg["server_api_key"]

    def _get(self, path, params=None):
        try:
            r = requests.get(self._base + path, headers=self._headers,
                             params=params, timeout=5)
            return r.json() if r.ok else {"code": r.status_code, "msg": r.reason}
        except Exception as e:
            return {"code": -1, "msg": str(e)}

    def _post(self, path, json=None, params=None):
        try:
            r = requests.post(self._base + path, headers=self._headers,
                              json=json, params=params, timeout=5)
            return r.json() if r.ok else {"code": r.status_code, "msg": r.reason}
        except Exception as e:
            return {"code": -1, "msg": str(e)}

    def _put(self, path, json=None):
        try:
            r = requests.put(self._base + path, headers=self._headers,
                             json=json, timeout=5)
            return r.json() if r.ok else {"code": r.status_code, "msg": r.reason}
        except Exception as e:
            return {"code": -1, "msg": str(e)}

    # ---------- 环境数据 ----------

    def latest(self, device_id=None):
        params = {}
        if device_id: params["device_id"] = device_id
        return self._get("/sensor/latest", params)

    def history(self, device_id, start="", end="", page=1, page_size=100):
        params = {"device_id": device_id, "page": page, "page_size": page_size}
        if start: params["start"] = start
        if end: params["end"] = end
        return self._get("/sensor/history", params)

    # ---------- 告警管理 ----------

    def alarm_list(self, page=1, page_size=20, device_id=None, severity=None):
        params = {"page": page, "page_size": page_size}
        if device_id: params["device_id"] = device_id
        if severity: params["severity"] = severity
        return self._get("/disease/list", params)

    def alarm_stats(self):
        return self._get("/disease/stats")

    def alarm_heatmap(self):
        return self._get("/disease/heatmap")

    # ---------- 设备控制 ----------

    def device_list(self, device_id=None):
        params = {}
        if device_id: params["device_id"] = device_id
        return self._get("/device/list", params)

    def device_control(self, device_id, command, source="manual_pc"):
        return self._post("/command/send", json={
            "device_id": device_id, "command": command, "source": source,
        })

    def command_logs(self, device_id=None, page=1, page_size=20):
        params = {"page": page, "page_size": page_size}
        if device_id: params["device_id"] = device_id
        return self._get("/command/logs", params)

    # ---------- 防治建议 ----------

    def advisory(self, device_id=None):
        params = {}
        if device_id: params["device_id"] = device_id
        return self._get("/advisory", params)
