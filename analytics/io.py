"""Immutable raw ingestion and portable artifact paths."""
import csv
import gzip
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

REVISION = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
BASE = f"https://raw.githubusercontent.com/statsbomb/open-data/{REVISION}/data"
ROOT = Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    return Path(os.environ.get("CORNERSCOUT_DATA_DIR", ROOT / "data"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def fetch(relative: str) -> object:
    for attempt in range(4):
        try:
            response = httpx.get(f"{BASE}/{relative}", timeout=90, follow_redirects=True)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Unreachable")


def ingest() -> dict:
    """Download only missing files; never rewrite raw, even on reruns."""
    raw = data_dir() / "raw"
    events_dir = raw / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    path = raw / "matches_laliga_2015_16.csv"
    if not path.exists():
        records = fetch("matches/11/27.json")
        pd.json_normalize(records, sep="_").to_csv(path, index=False)
    matches = pd.read_csv(path)
    if len(matches) != 380 or matches.match_id.nunique() != 380:
        raise ValueError("Expected 380 unique matches; raw preserved")
    if not (raw / "competitions.csv").exists():
        pd.DataFrame(fetch("competitions.json")).to_csv(raw / "competitions.csv", index=False)

    def download(match_id: int) -> dict:
        target = events_dir / f"{match_id}.jsonl.gz"
        status = "existente"
        if not target.exists():
            records = fetch(f"events/{match_id}.json")
            # Complete compressed payload before exclusively creating raw file.
            payload = gzip.compress("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in records).encode("utf-8"), mtime=0)
            with target.open("xb") as stream:
                stream.write(payload)
            status = "descargado"
        return {"match_id": match_id, "status": status}

    with ThreadPoolExecutor(max_workers=6) as pool:
        log = list(pool.map(download, matches.match_id.astype(int)))
    if not (raw / "registro_ingesta.csv").exists():
        pd.DataFrame(log).to_csv(raw / "registro_ingesta.csv", index=False)
    if not (raw / "metadata_ingesta.json").exists():
        write_json(raw / "metadata_ingesta.json", {"provider": "statsbomb_open_data", "revision": REVISION, "exported_at": now(), "format": "provider_nested_jsonl", "competition_id": 11, "season_id": 27})
    return {"matches": len(log), "revision": REVISION}


def read_events(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def manifest() -> str:
    raw = data_dir() / "raw"
    rows = []
    for path in sorted(raw.rglob("*")):
        if path.is_file() and path.name != ".gitkeep":
            rows.append({"relative_path": path.relative_to(raw).as_posix(), "sha256": digest(path), "byte_size": path.stat().st_size})
    fingerprint = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    write_json(data_dir() / "manifests" / "raw.json", {"files": rows, "source_manifest_sha256": fingerprint, "processed_at": now()})
    return fingerprint
