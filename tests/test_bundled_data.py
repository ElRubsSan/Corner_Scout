import hashlib
from zipfile import ZipFile

import pytest

from analytics.bundled_data import bundled_data_dir


def test_archive_extracted_once_and_checksum_required(tmp_path, monkeypatch):
    archive = tmp_path / "canonical.zip"
    with ZipFile(archive, "w") as target:
        target.writestr("interim/02_clean/contract.json", "{}")
    monkeypatch.setenv("CORNERSCOUT_DATA_ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    bundled_data_dir.cache_clear()
    destination = bundled_data_dir(archive)
    assert (destination / "interim/02_clean/contract.json").read_text() == "{}"
    assert bundled_data_dir(archive) == destination
    bundled_data_dir.cache_clear()
    monkeypatch.setenv("CORNERSCOUT_DATA_ARCHIVE_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        bundled_data_dir(archive)


def test_archive_rejects_paths_outside_canonical_stages(tmp_path, monkeypatch):
    archive = tmp_path / "canonical.zip"
    with ZipFile(archive, "w") as target:
        target.writestr("interim/02_clean/../../../escape.json", "{}")
    monkeypatch.setenv("CORNERSCOUT_DATA_ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    bundled_data_dir.cache_clear()
    with pytest.raises(ValueError, match="unexpected paths"):
        bundled_data_dir(archive)
