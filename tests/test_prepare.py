from fastapi.testclient import TestClient

from localsend_daemon.config import Config
from localsend_daemon.server import create_app

FILES = {
    "file1": {"id": "file1", "fileName": "hello.txt", "size": 5, "fileType": "text/plain"},
    "file2": {"id": "file2", "fileName": "img.png", "size": 1024, "fileType": "image/png"},
}

BODY = {"info": {}, "files": FILES}


def make_client() -> TestClient:
    config = Config(alias="Test", port=53317, receive_dir="/tmp", pin="123456")
    return TestClient(create_app(config))


def test_missing_pin():
    r = make_client().post("/api/localsend/v2/prepare-upload", json=BODY)
    assert r.status_code == 401


def test_wrong_pin():
    r = make_client().post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "wrong"})
    assert r.status_code == 401


def test_valid_pin():
    body = make_client().post(
        "/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"}
    ).json()
    assert "sessionId" in body
    assert set(body["files"].keys()) == {"file1", "file2"}


def test_conflict():
    client = make_client()
    client.post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"})
    r = client.post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"})
    assert r.status_code == 409
