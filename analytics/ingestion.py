"""Canonical ingestion primitives extracted from notebook 01."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(payload: bytes) -> str:
    """Return the SHA-256 digest of an in-memory payload."""
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it all in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_bytes(path: Path, payload: bytes) -> None:
    """Create a raw file atomically with respect to existing data.

    ``xb`` is intentional: ingestion must fail rather than overwrite raw data.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def event_name(value: object) -> object:
    """Read a StatsBomb name from nested or already-flat data."""
    return value.get("name") if isinstance(value, dict) else value


def event_pass_type(record: dict[str, Any]) -> object:
    """Read pass type from either supported StatsBomb representation."""
    return event_name(record.get("pass_type")) or event_name(
        (record.get("pass") or {}).get("type")
    )


def inspect_event_file(path: Path) -> tuple[int, int]:
    """Validate one immutable JSONL.GZ event file and count rows and corners."""
    rows = 0
    corners = 0
    ids: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            event_id = record.get("id")
            if not isinstance(event_id, str) or not event_id or event_id in ids:
                raise ValueError(f"Missing or duplicate event IDs in {path.name}")
            ids.add(event_id)
            rows += 1
            corners += int(
                event_name(record.get("type")) == "Pass"
                and event_pass_type(record) == "Corner"
            )
    if not rows:
        raise ValueError(f"Empty event file: {path}")
    return rows, corners
