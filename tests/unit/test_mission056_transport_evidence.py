from pathlib import Path

import pytest

from aegis.transport_evidence import preserve_raw_response_once


def test_raw_mirror_persists_exact_bytes_once_with_explicit_correlation(tmp_path: Path) -> None:
    raw = b'[{"title":"AEGIS Verification Widget","price":{"value":599},"availability":"Available"}]'
    path = tmp_path / "raw_response.bin"
    mirror = preserve_raw_response_once(raw, path=path, aegis_operation_id="op-056", correlation_id="mission056-correlation")
    assert mirror.persisted is True
    assert mirror.secret_like_content is False
    assert path.read_bytes() == raw
    with pytest.raises(FileExistsError):
        preserve_raw_response_once(raw, path=path, aegis_operation_id="op-057", correlation_id="mission056-correlation")


def test_raw_mirror_refuses_secret_like_content_without_persisting(tmp_path: Path) -> None:
    path = tmp_path / "raw_response.bin"
    mirror = preserve_raw_response_once(b"Bearer bdapi_abcdefghijklmnopqrstuvwxyz", path=path, aegis_operation_id="op-056", correlation_id="mission056-correlation")
    assert mirror.persisted is False
    assert mirror.secret_like_content is True
    assert not path.exists()
