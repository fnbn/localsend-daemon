from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from localsend_daemon.config import Config
from localsend_daemon.server import create_app

FILES = {
    "f1": {"id": "f1", "fileName": "hello.txt", "size": 5, "fileType": "text/plain"},
    "f2": {"id": "f2", "fileName": "img.png", "size": 4, "fileType": "image/png"},
}
BODY = {"info": {}, "files": FILES}


def make_client(receive_dir: str) -> TestClient:
    config = Config(alias="Test", port=53317, receive_dir=receive_dir, pin="123456")
    return TestClient(create_app(config))


def prepare(client: TestClient) -> dict:
    return client.post(
        "/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"}
    ).json()


def test_cancel_removes_partial_files(tmp_path):
    client = make_client(str(tmp_path))
    session = prepare(client)
    sid = session["sessionId"]

    client.post(
        "/api/localsend/v2/upload",
        params={"sessionId": sid, "fileId": "f1", "token": session["files"]["f1"]},
        content=b"hello",
    )

    r = client.post("/api/localsend/v2/cancel", params={"sessionId": sid})
    assert r.status_code == 200
    assert not (tmp_path / "hello.txt").exists()


def test_cancel_clears_session(tmp_path):
    client = make_client(str(tmp_path))
    session = prepare(client)

    client.post("/api/localsend/v2/cancel", params={"sessionId": session["sessionId"]})

    # Session gone — new prepare must succeed
    r = client.post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"})
    assert r.status_code == 200


def test_cancel_unknown_session(tmp_path):
    client = make_client(str(tmp_path))
    r = client.post("/api/localsend/v2/cancel", params={"sessionId": "nosuchid"})
    assert r.status_code == 404


def test_cancel_without_uploads(tmp_path):
    client = make_client(str(tmp_path))
    session = prepare(client)
    r = client.post("/api/localsend/v2/cancel", params={"sessionId": session["sessionId"]})
    assert r.status_code == 200
