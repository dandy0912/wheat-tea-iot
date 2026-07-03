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

    # ---------- 环境数据 ----------

    def latest(self, device_id=None):
        params = {}
        if device_id:
            params["device_id"] = device_id
        return self._get("/sensor/latest", params)

    def history(self, device_id, start="", end="", page=1, page_size=100):
        params = {"device_id": device_id, "page": page, "page_size": page_size}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._get("/sensor/history", params)

    # ---------- 告警管理 ----------

    def alarm_list(self, page=1, page_size=20, device_id=None, severity=None,
                   start_time=None, end_time=None, crop_type=None, disease_type=None):
        params = {"page": page, "page_size": page_size}
        if device_id:
            params["device_id"] = device_id
        if severity:
            params["severity"] = severity
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if crop_type:
            params["crop_type"] = crop_type
        if disease_type:
            params["disease_type"] = disease_type
        return self._get("/disease/list", params)

    def alarm_stats(self, crop_type=None, disease_type=None):
        params = {}
        if crop_type:
            params["crop_type"] = crop_type
        if disease_type:
            params["disease_type"] = disease_type
        return self._get("/disease/stats", params)

    # ---------- 设备控制 ----------

    def device_list(self, device_id=None):
        params = {}
        if device_id:
            params["device_id"] = device_id
        return self._get("/device/list", params)

    def device_control(self, device_id, command, source="manual_pc", operator=None):
        body = {"device_id": device_id, "command": command, "source": source}
        if operator:
            body["operator"] = operator
        return self._post("/command/send", json=body)

    def command_logs(self, device_id=None, page=1, page_size=20, source=None):
        params = {"page": page, "page_size": page_size}
        if device_id:
            params["device_id"] = device_id
        if source:
            params["source"] = source
        return self._get("/command/logs", params)
