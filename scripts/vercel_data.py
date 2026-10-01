"""Package verified canonical data locally or restore it during a Vercel build."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlsplit
from zipfile import ZipFile, ZIP_DEFLATED

from backend.repository import CanonicalRepository

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("interim/02_clean", "interim/03_scr15", "processed/04_features", "processed/05_modeling")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("package", "restore"))
    args = parser.parse_args()
    if args.command == "package":
        repo = CanonicalRepository()
        archive = ROOT / "artifacts" / "vercel-canonical-data.zip"
        archive.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(archive, "w", ZIP_DEFLATED) as target:
            for directory in repo.stage_dirs.values():
                target.write(directory / "contract.json", (directory / "contract.json").relative_to(repo.root).as_posix())
            for artifact in repo._artifacts.values():
                target.write(artifact.path, artifact.path.relative_to(repo.root).as_posix())
        print("Archive: artifacts/vercel-canonical-data.zip")
        print("Bytes:", archive.stat().st_size)
        with archive.open("rb") as stream:
            print("SHA256:", hashlib.file_digest(stream, "sha256").hexdigest())
        return
    url = os.environ.get("CORNERSCOUT_DATA_ARCHIVE_URL", "")
    checksum = os.environ.get("CORNERSCOUT_DATA_ARCHIVE_SHA256", "")
    if urlsplit(url).scheme != "https" or len(checksum) != 64:
        raise ValueError("Configure HTTPS data archive URL and SHA256 in Vercel")
    archive = ROOT / ".vercel-canonical-data.zip"
    try:
        with urlopen(url, timeout=120) as response, archive.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        with archive.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != checksum:
                raise ValueError("Data archive SHA256 mismatch")
        destination = ROOT / "data"
        with ZipFile(archive) as source:
            for item in source.infolist():
                path = (destination / item.filename).resolve()
                if not path.is_relative_to(destination.resolve()) or not any(item.filename.startswith(stage + "/") for stage in STAGES):
                    raise ValueError("Archive contains unexpected paths")
            source.extractall(destination)
        CanonicalRepository(destination)
        print("OK: restored and verified canonical data for Vercel")
    finally:
        archive.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
