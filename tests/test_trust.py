from pathlib import Path

import pytest

from localsend_daemon.trust import TrustStore

FP_A = "A" * 64
FP_B = "B" * 64


@pytest.fixture
def fp_path(tmp_path: Path) -> Path:
    return tmp_path / "trusted_fingerprints"


def test_load_missing_file(fp_path):
    store = TrustStore(fp_path)
    assert not store.contains(FP_A)


def test_load_with_comments_and_blanks(fp_path):
    fp_path.write_text(f"# comment\n\n{FP_A}\n  # another\n{FP_B}\n")
    store = TrustStore(fp_path)
    assert store.contains(FP_A)
    assert store.contains(FP_B)


def test_load_with_inline_alias(fp_path):
    fp_path.write_text(f"{FP_A}  # alice's laptop, added 2026-05-06\n")
    store = TrustStore(fp_path)
    assert store.contains(FP_A)


def test_load_skips_malformed_lines(fp_path):
    fp_path.write_text(f"not-a-fingerprint\n{FP_A}\nZZZZ\n")
    store = TrustStore(fp_path)
    assert store.contains(FP_A)
    assert not store.contains("not-a-fingerprint")


def test_contains_case_insensitive(fp_path):
    fp_path.write_text(FP_A + "\n")
    store = TrustStore(fp_path)
    assert store.contains(FP_A.lower())
    assert store.contains(FP_A.upper())


def test_contains_strips_colon_separators(fp_path):
    coloned = ":".join(FP_A[i:i+2] for i in range(0, len(FP_A), 2))
    fp_path.write_text(coloned + "\n")
    store = TrustStore(fp_path)
    assert store.contains(FP_A)


def test_add_appends_to_file(fp_path):
    store = TrustStore(fp_path)
    store.add(FP_A, comment="test peer")
    assert store.contains(FP_A)
    content = fp_path.read_text()
    assert FP_A in content
    assert "test peer" in content


def test_add_without_comment(fp_path):
    store = TrustStore(fp_path)
    store.add(FP_A)
    assert FP_A in fp_path.read_text()


def test_add_idempotent(fp_path):
    store = TrustStore(fp_path)
    store.add(FP_A)
    store.add(FP_A)
    assert fp_path.read_text().count(FP_A) == 1


def test_add_multiple_fingerprints(fp_path):
    store = TrustStore(fp_path)
    store.add(FP_A)
    store.add(FP_B)
    assert store.contains(FP_A)
    assert store.contains(FP_B)
    lines = [ln for ln in fp_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2


def test_add_invalid_fingerprint_ignored(fp_path):
    store = TrustStore(fp_path)
    store.add("not-valid")
    assert not fp_path.exists()


def test_file_permissions_on_create(fp_path):
    store = TrustStore(fp_path)
    store.add(FP_A)
    assert fp_path.stat().st_mode & 0o777 == 0o600


def test_add_preserves_existing_content(fp_path):
    fp_path.write_text(f"# manual entry\n{FP_A}\n")
    fp_path.chmod(0o600)
    store = TrustStore(fp_path)
    store.add(FP_B)
    content = fp_path.read_text()
    assert "# manual entry" in content
    assert FP_A in content
    assert FP_B in content
