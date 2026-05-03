from fastapi.testclient import TestClient

from localsend_daemon.config import Config
from localsend_daemon.server import create_app

PEER = {
    "alias": "Sending Device",
    "version": "2.1",
    "deviceType": "mobile",
    "fingerprint": "peer-fingerprint",
    "port": 53317,
    "protocol": "http",
}


def make_client() -> TestClient:
    config = Config(alias="Test Device", port=53317, receive_dir="/tmp", pin="000000")
    return TestClient(create_app(config))


def test_register_status():
    r = make_client().post("/api/localsend/v2/register", json=PEER)
    assert r.status_code == 200


def test_register_returns_own_identity():
    body = make_client().post("/api/localsend/v2/register", json=PEER).json()
    assert body["alias"] == "Test Device"
    assert body["version"] == "2.1"
    assert body["deviceType"] == "headless"
    assert "fingerprint" in body
    assert body["download"] is False


def test_register_ignores_extra_fields():
    peer = {**PEER, "unknownField": "value"}
    r = make_client().post("/api/localsend/v2/register", json=peer)
    assert r.status_code == 200


def test_register_without_optional_fields():
    minimal = {"alias": "Peer", "version": "2.1", "fingerprint": "abc"}
    r = make_client().post("/api/localsend/v2/register", json=minimal)
    assert r.status_code == 200
