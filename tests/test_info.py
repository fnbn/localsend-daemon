from fastapi.testclient import TestClient

from localsend_daemon.config import Config
from localsend_daemon.server import create_app


def make_client() -> TestClient:
    config = Config(alias="Test Device", port=53317, receive_dir="/tmp", pin="000000")
    return TestClient(create_app(config))


def test_info_status():
    r = make_client().get("/api/localsend/v2/info")
    assert r.status_code == 200


def test_info_shape():
    body = make_client().get("/api/localsend/v2/info").json()
    assert body["alias"] == "Test Device"
    assert body["version"] == "2.1"
    assert body["deviceType"] == "headless"
    assert body["download"] is False
    assert "fingerprint" in body
    assert "deviceModel" not in body  # excluded when None


def test_info_fingerprint_is_stable_per_app():
    client = make_client()
    r1 = client.get("/api/localsend/v2/info").json()
    r2 = client.get("/api/localsend/v2/info").json()
    assert r1["fingerprint"] == r2["fingerprint"]
