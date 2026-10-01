"""Extract the complete build-verified archive once per serverless instance."""
from __future__ import annotations

import hashlib
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile

STAGES = ("interim/02_clean", "interim/03_scr15", "processed/04_features", "processed/05_modeling")


@lru_cache(maxsize=1)
def bundled_data_dir(archive: Path) -> Path:
    expected = os.environ.get("CORNERSCOUT_DATA_ARCHIVE_SHA256", "")
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError("Bundled data archive SHA256 mismatch")
    destination = Path(tempfile.mkdtemp(prefix="cornerscout-data-"))
    with ZipFile(archive) as source:
        for item in source.infolist():
            path = (destination / item.filename).resolve()
            if not path.is_relative_to(destination.resolve()) or not any(
                item.filename.startswith(stage + "/") for stage in STAGES
            ):
                raise ValueError("Archive contains unexpected paths")
        source.extractall(destination)
    return destination
