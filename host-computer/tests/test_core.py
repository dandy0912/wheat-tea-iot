"""
上位机核心层单元测试
测试范围: config.py + api_client.py (无 UI 依赖)
"""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


# ============================================================
# config.py  — 配置管理
# ============================================================
class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cfg_path = os.path.join(self.tmpdir, "config.json")

    def _patch_path(self):
        return patch("config.CONFIG_FILE", self.cfg_path)

    def test_load_defaults_when_no_file(self):
        from config import load
        with self._patch_path():
            cfg = load()
            self.assertEqual(cfg["device_id"], "farmeye_guard_ws63")
            self.assertEqual(cfg["server_url"], "http://127.0.0.1:8000")
            self.assertEqual(cfg["refresh_interval"], 3000)

    def test_save_and_load(self):
        from config import load, save
        data = {
            "server_url": "https://vps.example.com",
            "server_api_key": "key123",
            "refresh_interval": 5000,
            "device_id": "device_01",
        }
        with self._patch_path():
            save(data)
            loaded = load()
            for k, v in data.items():
                self.assertEqual(loaded[k], v)

    def test_load_merge_user_over_defaults(self):
        from config import load
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump({"device_id": "custom"}, f)
        with patch("config.CONFIG_FILE", self.cfg_path):
            cfg = load()
            self.assertEqual(cfg["device_id"], "custom")
            self.assertEqual(cfg["server_url"], "http://127.0.0.1:8000")

    def test_api_base_construction(self):
        from config import api_base
        cfg = {"server_url": "http://vps:8080"}
        self.assertEqual(api_base(cfg), "http://vps:8080/api/v1")


# ============================================================
# api_client.py — API 请求封装
# ============================================================
class TestApiClient(unittest.TestCase):
    def setUp(self):
        from api_client import ApiClient
        self.cfg = {
            "server_url": "http://test:8000",
            "server_api_key": "test-key",
            "device_id": "dev_01",
            "refresh_interval": 3000,
        }
        self.client = ApiClient(self.cfg)

    def _mock_resp(self, data, status=200):
        resp = MagicMock(spec=requests.Response)
        resp.ok = status == 200
        resp.status_code = status
        resp.reason = "OK" if status == 200 else "Error"
        resp.json.return_value = data
        return resp

    # -- config --
    def test_client_api_key_header(self):
        with patch("requests.get", return_value=self._mock_resp({"code": 0, "data": {}})) as m:
            self.client.latest()
            headers = m.call_args[1]["headers"]
            self.assertEqual(headers["X-Api-Key"], "test-key")

    def test_no_api_key_header_when_key_empty(self):
        from api_client import ApiClient
        c = ApiClient({**self.cfg, "server_api_key": ""})
        with patch("requests.get", return_value=self._mock_resp({"code": 0, "data": {}})) as m:
            c.latest()
            headers = m.call_args[1].get("headers", {})
            self.assertNotIn("X-Api-Key", headers)

    # -- latest --
    def test_latest_success(self):
        payload = {"code": 0, "data": {"temperature": 25.5}}
        with patch("requests.get", return_value=self._mock_resp(payload)):
            res = self.client.latest("dev_01")
            self.assertEqual(res["data"]["temperature"], 25.5)

    def test_latest_http_404(self):
        with patch("requests.get", return_value=self._mock_resp({}, status=404)):
            res = self.client.latest()
            self.assertEqual(res["code"], 404)

    def test_latest_connection_error(self):
        with patch("requests.get", side_effect=requests.ConnectionError("no route")):
            res = self.client.latest()
            self.assertEqual(res["code"], -1)

    def test_latest_timeout(self):
        with patch("requests.get", side_effect=requests.Timeout("timeout")):
            res = self.client.latest()
            self.assertEqual(res["code"], -1)

    # -- history --
    def test_history_success(self):
        payload = {"code": 0, "data": {"records": [{"temperature": 26}], "total": 1}}
        with patch("requests.get", return_value=self._mock_resp(payload)) as m:
            self.client.history("dev_01", start="2026-01-01T00:00:00")
            params = m.call_args[1]["params"]
            self.assertIn("start", params)

    # -- alarm_list --
    def test_alarm_list_filters(self):
        payload = {"code": 0, "data": {"records": [], "pagination": {"total": 0}}}
        with patch("requests.get", return_value=self._mock_resp(payload)) as m:
            self.client.alarm_list(severity="Mild", crop_type="wheat")
            params = m.call_args[1]["params"]
            self.assertEqual(params["severity"], "Mild")
            self.assertEqual(params["crop_type"], "wheat")

    def test_alarm_list_no_filters(self):
        payload = {"code": 0, "data": {"records": [], "pagination": {"total": 0}}}
        with patch("requests.get", return_value=self._mock_resp(payload)):
            res = self.client.alarm_list()
            self.assertEqual(res["code"], 0)

    # -- alarm_stats --
    def test_alarm_stats_filters(self):
        payload = {"code": 0, "data": {"total_detections": 50}}
        with patch("requests.get", return_value=self._mock_resp(payload)) as m:
            self.client.alarm_stats(disease_type="rust")
            self.assertEqual(m.call_args[1]["params"]["disease_type"], "rust")

    # -- device_control --
    def test_device_control_body(self):
        payload = {"code": 0, "msg": "sent"}
        with patch("requests.post", return_value=self._mock_resp(payload)) as m:
            self.client.device_control("dev_01", "irrig ON")
            body = m.call_args[1]["json"]
            self.assertEqual(body["command"], "irrig ON")
            self.assertEqual(body["device_id"], "dev_01")
            self.assertEqual(body["source"], "manual_pc")

    def test_device_control_with_operator(self):
        payload = {"code": 0}
        with patch("requests.post", return_value=self._mock_resp(payload)) as m:
            self.client.device_control("dev_01", "led OFF", operator="admin")
            self.assertEqual(m.call_args[1]["json"]["operator"], "admin")

    # -- command_logs --
    def test_command_logs_with_source(self):
        payload = {"code": 0, "data": {"records": []}}
        with patch("requests.get", return_value=self._mock_resp(payload)) as m:
            self.client.command_logs(source="manual_pc")
            self.assertEqual(m.call_args[1]["params"]["source"], "manual_pc")

    # -- device_list --
    def test_device_list(self):
        payload = {"code": 0, "data": [{"device_id": "dev_01", "online": True}]}
        with patch("requests.get", return_value=self._mock_resp(payload)):
            res = self.client.device_list()
            self.assertEqual(len(res["data"]), 1)

    # -- exception wrapping --
    def test_all_exceptions_return_minus_one(self):
        for exc in [ConnectionError("fail"), TimeoutError("timeout"), ValueError("bad")]:
            with patch("requests.get", side_effect=exc):
                res = self.client.latest()
                self.assertEqual(res["code"], -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
