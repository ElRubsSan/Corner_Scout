import gzip
import json

import pytest

from analytics.ingestion import create_bytes, inspect_event_file, sha256_bytes


def test_raw_creation_is_immutable(tmp_path):
    path = tmp_path / "raw" / "value.bin"
    create_bytes(path, b"first")
    with pytest.raises(FileExistsError):
        create_bytes(path, b"second")
    assert path.read_bytes() == b"first"
    assert sha256_bytes(b"first") == "a7937b64b8caa58f03721bb6bacf5c78cb235febe0e70b1b84cd99541461a08e"


def test_inspection_supports_nested_and_flat_corner_types(tmp_path):
    path = tmp_path / "events.jsonl.gz"
    rows = [
        {"id": "nested", "type": {"name": "Pass"}, "pass": {"type": {"name": "Corner"}}},
        {"id": "flat", "type": "Pass", "pass_type": "Corner"},
    ]
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    assert inspect_event_file(path) == (2, 2)
