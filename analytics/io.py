"""Immutable raw ingestion and verified, atomic artifact I/O."""
import gzip
import hashlib
import json
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from analytics.contracts import Artifact, StageContract, contract_payload
from analytics.ingestion import create_bytes, inspect_event_file, sha256_file

REVISION = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
BASE = f"https://raw.githubusercontent.com/statsbomb/open-data/{REVISION}/data"
ROOT = Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    return Path(os.environ.get("CORNERSCOUT_DATA_DIR", ROOT / "data"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    return sha256_file(path)


def write_json(path: Path, value: object) -> None:
    """Publish JSON atomically in the target directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
            suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def artifact(path: Path, base: Path, *, rows: int | None = None) -> Artifact:
    """Describe a completed artifact relative to its contract directory."""
    return Artifact(
        file=path.relative_to(base).as_posix(),
        sha256=digest(path),
        bytes=path.stat().st_size,
        rows=rows,
    )


def verify_artifacts(contract: StageContract, directory: Path) -> None:
    """Reject missing, resized, or modified contract artifacts."""
    for item in contract.all_artifacts:
        path = directory / item.file
        if not path.is_file():
            raise FileNotFoundError(f"Missing {contract.stage} artifact: {item.file}")
        if item.bytes is not None and path.stat().st_size != item.bytes:
            raise ValueError(f"Artifact size mismatch: {item.file}")
        actual = digest(path)
        if actual != item.sha256:
            raise ValueError(f"Artifact SHA-256 mismatch: {item.file}")


def load_contract(
    path: Path, *, expected_stage: str, expected_version: str, verify: bool = True
) -> StageContract:
    """Load an external contract with explicit stage/version expectations."""
    contract = StageContract.model_validate_json(path.read_text(encoding="utf-8"))
    if contract.stage != expected_stage:
        raise ValueError(f"Expected stage {expected_stage!r}, got {contract.stage!r}")
    if contract.contract_version != expected_version:
        raise ValueError(
            f"Expected contract version {expected_version!r}, got {contract.contract_version!r}"
        )
    if verify:
        verify_artifacts(contract, path.parent)
    return contract


def publish_contract(directory: Path, contract: StageContract) -> Path:
    """Verify all outputs and atomically publish the stage contract last."""
    directory.mkdir(parents=True, exist_ok=True)
    verify_artifacts(contract, directory)
    path = directory / "contract.json"
    write_json(path, contract.model_dump(mode="json", exclude_none=True))
    return path


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
        payload = pd.json_normalize(records, sep="_").to_csv(index=False).encode("utf-8")
        create_bytes(path, payload)
    matches = pd.read_csv(path)
    if len(matches) != 380 or matches.match_id.nunique() != 380:
        raise ValueError("Expected 380 unique matches; raw preserved")
    if not (raw / "competitions.csv").exists():
        payload = pd.DataFrame(fetch("competitions.json")).to_csv(index=False).encode("utf-8")
        create_bytes(raw / "competitions.csv", payload)

    def download(match_id: int) -> dict:
        target = events_dir / f"{match_id}.jsonl.gz"
        status = "existente"
        if not target.exists():
            records = fetch(f"events/{match_id}.json")
            # Complete compressed payload before exclusively creating raw file.
            payload = gzip.compress("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in records).encode("utf-8"), mtime=0)
            create_bytes(target, payload)
            status = "descargado"
        event_count, corner_count = inspect_event_file(target)
        return {"match_id": match_id, "status": status, "events": event_count, "corners": corner_count}

    with ThreadPoolExecutor(max_workers=6) as pool:
        log = list(pool.map(download, matches.match_id.astype(int)))
    if not (raw / "registro_ingesta.csv").exists():
        create_bytes(
            raw / "registro_ingesta.csv",
            pd.DataFrame(log).to_csv(index=False).encode("utf-8"),
        )
    if not (raw / "metadata_ingesta.json").exists():
        metadata = {"provider": "statsbomb_open_data", "revision": REVISION, "exported_at": now(), "format": "provider_nested_jsonl", "competition_id": 11, "season_id": 27}
        create_bytes(
            raw / "metadata_ingesta.json",
            (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
    raw_files: dict[str, str] = {}
    for raw_path in sorted(path for path in raw.rglob("*") if path.is_file()):
        raw_files[raw_path.relative_to(raw).as_posix()] = digest(raw_path)
    fingerprint = hashlib.sha256(
        json.dumps(raw_files, sort_keys=True).encode()
    ).hexdigest()
    contract = contract_payload(
        stage="01_ingestion", contract_version="01-ingestion-v1", run_id=now(),
        exports=[], provider="statsbomb_open_data", revision=REVISION,
        competition_id=11, season_id=27, raw_manifest_sha256=fingerprint,
        raw_files=raw_files,
        counts={"matches": len(log), "event_files": len(log),
                "events": sum(item["events"] for item in log),
                "corners": sum(item["corners"] for item in log)},
    )
    publish_contract(data_dir() / "interim" / "01_ingestion", contract)
    return {"matches": len(log), "revision": REVISION, "contract_version": contract.contract_version}


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
