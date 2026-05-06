from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from localsend_daemon.config import Config
from localsend_daemon.server import create_app

FILES = {
    "file1": {"id": "file1", "fileName": "hello.txt", "size": 5, "fileType": "text/plain"},
    "file2": {"id": "file2", "fileName": "img.png", "size": 1024, "fileType": "image/png"},
}

BODY = {"info": {}, "files": FILES}
TRUSTED_FP = "A" * 64
UNTRUSTED_FP = "B" * 64

_PATCH = "localsend_daemon.transfer.prepare.extract_peer_fingerprint"


def make_client(
    pin: str = "123456",
    protocol: str = "https",
    trusted_fp: str | None = None,
    trust_on_first_pin: bool = False,
    tmp_path: Path | None = None,
) -> TestClient:
    kwargs: dict = dict(alias="Test", port=53317, receive_dir="/tmp", pin=pin, protocol=protocol)
    if trusted_fp is not None:
        fp_file = tmp_path / "fps"
        fp_file.write_text(trusted_fp + "\n")
        kwargs["trusted_fingerprints_path"] = str(fp_file)
    if trust_on_first_pin:
        kwargs["trust_on_first_pin"] = True
    return TestClient(create_app(Config(**kwargs)))


# --- Existing PIN tests (behavior unchanged) ---

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


# --- Fingerprint bypass tests ---

def test_trusted_fp_no_pin_accepted(tmp_path):
    client = make_client(trusted_fp=TRUSTED_FP, tmp_path=tmp_path)
    with patch(_PATCH, AsyncMock(return_value=TRUSTED_FP)):
        r = client.post("/api/localsend/v2/prepare-upload", json=BODY)
    assert r.status_code == 200


def test_trusted_fp_wrong_pin_still_bypassed(tmp_path):
    client = make_client(trusted_fp=TRUSTED_FP, tmp_path=tmp_path)
    with patch(_PATCH, AsyncMock(return_value=TRUSTED_FP)):
        r = client.post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "wrong"})
    assert r.status_code == 200


def test_unknown_fp_no_pin_rejected(tmp_path):
    client = make_client(trusted_fp=TRUSTED_FP, tmp_path=tmp_path)
    with patch(_PATCH, AsyncMock(return_value=UNTRUSTED_FP)):
        r = client.post("/api/localsend/v2/prepare-upload", json=BODY)
    assert r.status_code == 401


def test_unknown_fp_correct_pin_accepted(tmp_path):
    client = make_client(trusted_fp=TRUSTED_FP, tmp_path=tmp_path)
    with patch(_PATCH, AsyncMock(return_value=UNTRUSTED_FP)):
        r = client.post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"})
    assert r.status_code == 200


def test_http_mode_bypass_disabled(tmp_path):
    """Even with a trusted FP configured, protocol=http must always require the PIN."""
    client = make_client(trusted_fp=TRUSTED_FP, tmp_path=tmp_path, protocol="http")
    with patch(_PATCH, AsyncMock(return_value=TRUSTED_FP)):
        r = client.post("/api/localsend/v2/prepare-upload", json=BODY)
    assert r.status_code == 401


def test_body_fp_field_not_used_for_bypass(tmp_path):
    """Anti-regression: info.fingerprint in the request body must not bypass the PIN.

    A LAN attacker can put any string in the body.  Only the fingerprint extracted
    from the live TLS connection (Option A or C) may trigger the bypass.
    """
    client = make_client(trusted_fp=TRUSTED_FP, tmp_path=tmp_path)
    body_with_trusted_fp = {**BODY, "info": {"fingerprint": TRUSTED_FP}}
    # TLS fingerprint is untrusted; body field is trusted — must still require PIN
    with patch(_PATCH, AsyncMock(return_value=UNTRUSTED_FP)):
        r = client.post("/api/localsend/v2/prepare-upload", json=body_with_trusted_fp)
    assert r.status_code == 401


def test_auto_add_on_first_pin(tmp_path):
    fp_file = tmp_path / "fps"
    config = Config(
        alias="Test",
        port=53317,
        receive_dir="/tmp",
        pin="123456",
        trusted_fingerprints_path=str(fp_file),
        trust_on_first_pin=True,
    )
    client = TestClient(create_app(config))
    with patch(_PATCH, AsyncMock(return_value=UNTRUSTED_FP)):
        r = client.post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"})
    assert r.status_code == 200
    assert UNTRUSTED_FP in fp_file.read_text()


def test_no_auto_add_without_trust_on_first_pin(tmp_path):
    fp_file = tmp_path / "fps"
    config = Config(
        alias="Test",
        port=53317,
        receive_dir="/tmp",
        pin="123456",
        trusted_fingerprints_path=str(fp_file),
        trust_on_first_pin=False,
    )
    client = TestClient(create_app(config))
    with patch(_PATCH, AsyncMock(return_value=UNTRUSTED_FP)):
        r = client.post("/api/localsend/v2/prepare-upload", json=BODY, params={"pin": "123456"})
    assert r.status_code == 200
    assert not fp_file.exists()
