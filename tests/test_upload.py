import tempfile
import threading
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


@pytest.fixture()
def tmp_dir(tmp_path):
    return str(tmp_path)


def make_client(receive_dir: str) -> TestClient:
    config = Config(alias="Test", port=53317, receive_dir=receive_dir, pin="123456")
    return TestClient(create_app(config))


def prepare(client: TestClient) -> dict:
    return client.post(
        "/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"}
    ).json()


def test_upload_single_file(tmp_dir):
    client = make_client(tmp_dir)
    session = prepare(client)
    sid = session["sessionId"]
    token = session["files"]["f1"]

    r = client.post(
        "/api/localsend/v2/upload",
        params={"sessionId": sid, "fileId": "f1", "token": token},
        content=b"hello",
    )
    assert r.status_code == 200
    assert (Path(tmp_dir) / "hello.txt").read_bytes() == b"hello"


def test_upload_all_files_clears_session(tmp_dir):
    client = make_client(tmp_dir)
    session = prepare(client)
    sid = session["sessionId"]

    for file_id, file_name, content in [("f1", "hello.txt", b"hello"), ("f2", "img.png", b"data")]:
        client.post(
            "/api/localsend/v2/upload",
            params={"sessionId": sid, "fileId": file_id, "token": session["files"][file_id]},
            content=content,
        )

    # Session should be gone — new prepare-upload must succeed (not 409)
    r = client.post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"})
    assert r.status_code == 200


def test_upload_wrong_token(tmp_dir):
    client = make_client(tmp_dir)
    session = prepare(client)
    r = client.post(
        "/api/localsend/v2/upload",
        params={"sessionId": session["sessionId"], "fileId": "f1", "token": "badtoken"},
        content=b"hello",
    )
    assert r.status_code == 403


def test_upload_wrong_session(tmp_dir):
    client = make_client(tmp_dir)
    session = prepare(client)
    token = session["files"]["f1"]
    r = client.post(
        "/api/localsend/v2/upload",
        params={"sessionId": "nosuchsession", "fileId": "f1", "token": token},
        content=b"hello",
    )
    assert r.status_code == 403


def test_upload_filename_collision(tmp_dir):
    existing = Path(tmp_dir) / "hello.txt"
    existing.write_bytes(b"old")

    client = make_client(tmp_dir)
    session = prepare(client)
    sid = session["sessionId"]
    token = session["files"]["f1"]

    r = client.post(
        "/api/localsend/v2/upload",
        params={"sessionId": sid, "fileId": "f1", "token": token},
        content=b"new",
    )
    assert r.status_code == 200
    assert existing.read_bytes() == b"old"  # original untouched
    assert (Path(tmp_dir) / "hello (1).txt").read_bytes() == b"new"


def test_upload_parallel_files(tmp_dir):
    client = make_client(tmp_dir)
    session = prepare(client)
    sid = session["sessionId"]

    statuses = {}

    def do_upload(file_id, content):
        r = client.post(
            "/api/localsend/v2/upload",
            params={"sessionId": sid, "fileId": file_id, "token": session["files"][file_id]},
            content=content,
        )
        statuses[file_id] = r.status_code

    threads = [
        threading.Thread(target=do_upload, args=("f1", b"hello")),
        threading.Thread(target=do_upload, args=("f2", b"data")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert statuses == {"f1": 200, "f2": 200}
    assert (Path(tmp_dir) / "hello.txt").read_bytes() == b"hello"
    assert (Path(tmp_dir) / "img.png").read_bytes() == b"data"


def test_upload_parallel_same_filename(tmp_dir):
    """Two files with identical fileNames in one session both land on disk without clobbering."""
    files = {
        "f1": {"id": "f1", "fileName": "dup.txt", "size": 5, "fileType": "text/plain"},
        "f2": {"id": "f2", "fileName": "dup.txt", "size": 3, "fileType": "text/plain"},
    }
    client = make_client(tmp_dir)
    session = client.post(
        "/api/localsend/v2/prepare-upload",
        json={"info": {}, "files": files},
        params={"pin": "123456"},
    ).json()
    sid = session["sessionId"]

    statuses = {}

    def do_upload(file_id, content):
        r = client.post(
            "/api/localsend/v2/upload",
            params={"sessionId": sid, "fileId": file_id, "token": session["files"][file_id]},
            content=content,
        )
        statuses[file_id] = r.status_code

    threads = [
        threading.Thread(target=do_upload, args=("f1", b"hello")),
        threading.Thread(target=do_upload, args=("f2", b"bye")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert statuses == {"f1": 200, "f2": 200}
    names = {p.name for p in Path(tmp_dir).iterdir()}
    assert "dup.txt" in names
    assert "dup (1).txt" in names


def test_upload_exceeds_declared_size(tmp_dir):
    files = {"f1": {"id": "f1", "fileName": "small.txt", "size": 3, "fileType": "text/plain"}}
    client = make_client(tmp_dir)
    session = client.post(
        "/api/localsend/v2/prepare-upload",
        json={"info": {}, "files": files},
        params={"pin": "123456"},
    ).json()
    r = client.post(
        "/api/localsend/v2/upload",
        params={"sessionId": session["sessionId"], "fileId": "f1", "token": session["files"]["f1"]},
        content=b"toolarge",
    )
    assert r.status_code == 400
    assert not (Path(tmp_dir) / "small.txt").exists()
