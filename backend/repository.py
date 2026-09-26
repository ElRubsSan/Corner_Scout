"""Verified, read-only access to canonical notebook artifacts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import duckdb
from pydantic import ValidationError

from analytics.contracts import StageContract
from analytics.io import data_dir


EXPECTED_CONTRACTS = {
    "02": "02-clean-v2",
    "03": "03-scr15-v2",
    "04": "04-features-v2",
    "05": "05-modeling-v3-objectives",
}
EXPECTED_STAGES = {
    "02": "02_clean",
    "03": "03_scr15",
    "04": "04_features",
    "05": "05_modeling",
}


class ArtifactError(RuntimeError):
    """Raised when canonical provenance cannot be established."""


@dataclass(frozen=True)
class Artifact:
    stage: str
    path: Path
    sha256: str


class CanonicalRepository:
    TABLES = {
        "matches_clean": ("02", "matches_clean.parquet"),
        "corners_engineered": ("04", "corners_engineered.parquet"),
        "cluster_assignments": ("04", "cluster_assignments.parquet"),
        "cluster_centers": ("04", "cluster_centers.parquet"),
        "objective_winners": ("05", "objective_winners.parquet"),
        "temporal_metrics": ("05", "temporal_metrics.parquet"),
    }

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or data_dir()
        self.stage_dirs = {
            "02": self.root / "interim" / "02_clean",
            "03": self.root / "interim" / "03_scr15",
            "04": self.root / "processed" / "04_features",
            "05": self.root / "processed" / "05_modeling",
        }
        self.contracts = self._load_contracts()
        self._artifacts = self._index_artifacts()
        self._verify_lineage()
        for artifact in self._artifacts.values():
            self._verify(artifact)
        for table in self.TABLES:
            self.artifact(table)
        self._required_artifact("03", "corners_scr15.parquet")

    def _load_contracts(self) -> dict[str, StageContract]:
        contracts: dict[str, StageContract] = {}
        for stage, expected in EXPECTED_CONTRACTS.items():
            path = self.stage_dirs[stage] / "contract.json"
            try:
                contract = StageContract.model_validate_json(path.read_text(encoding="utf-8"))
            except OSError as exc:
                raise ArtifactError(f"canonical_contract_unavailable:{stage}") from exc
            except (ValidationError, ValueError) as exc:
                raise ArtifactError(f"canonical_contract_invalid:{stage}") from exc
            if contract.stage != EXPECTED_STAGES[stage] or contract.contract_version != expected:
                raise ArtifactError(f"canonical_contract_invalid:{stage}")
            contracts[stage] = contract
        return contracts

    def _index_artifacts(self) -> dict[tuple[str, str], Artifact]:
        result: dict[tuple[str, str], Artifact] = {}
        for stage, contract in self.contracts.items():
            stage_root = self.stage_dirs[stage].resolve()
            indexed_paths: set[Path] = set()
            for record in contract.all_artifacts:
                path = (stage_root / record.file).resolve()
                if path == stage_root or not path.is_relative_to(stage_root):
                    raise ArtifactError(f"canonical_artifact_path_invalid:{stage}:{record.file}")
                key = (stage, record.file)
                if key in result or path in indexed_paths:
                    raise ArtifactError(f"canonical_artifact_duplicate:{stage}:{record.file}")
                result[key] = Artifact(stage, path, record.sha256)
                indexed_paths.add(path)
        return result

    def _verify_lineage(self) -> None:
        for child, parent in (("03", "02"), ("04", "03"), ("05", "04")):
            contract = self.contracts[child]
            metadata = contract.model_extra or {}
            if metadata.get("source_contract_version") != EXPECTED_CONTRACTS[parent]:
                raise ArtifactError(f"canonical_lineage_invalid:{child}")
            if metadata.get("source_run_id") != self.contracts[parent].run_id:
                raise ArtifactError(f"canonical_run_lineage_invalid:{child}")
        source_hash = (self.contracts["04"].model_extra or {}).get("source_corners_sha256")
        if source_hash != self._required_artifact("03", "corners_scr15.parquet").sha256:
            raise ArtifactError("canonical_hash_lineage_invalid:04")

    def _required_artifact(self, stage: str, name: str) -> Artifact:
        try:
            return self._artifacts[(stage, name)]
        except KeyError as exc:
            raise ArtifactError(f"canonical_artifact_missing:{stage}:{name}") from exc

    def artifact(self, table: str) -> Artifact:
        try:
            stage, filename = self.TABLES[table]
        except KeyError as exc:
            raise ValueError("unknown_analytical_table") from exc
        return self._required_artifact(stage, filename)

    @staticmethod
    def _verify(artifact: Artifact) -> None:
        try:
            with artifact.path.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            raise ArtifactError(f"canonical_artifact_unavailable:{artifact.stage}:{artifact.path.name}") from exc
        if actual != artifact.sha256:
            raise ArtifactError(f"canonical_artifact_hash_mismatch:{artifact.stage}:{artifact.path.name}")

    @property
    def identity(self) -> dict[str, str]:
        return {EXPECTED_CONTRACTS[stage]: contract.run_id for stage, contract in self.contracts.items()}

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(self.identity, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def rows(self, table: str, clause: str = "", params: list[Any] | None = None) -> list[dict[str, Any]]:
        artifact = self.artifact(table)
        self._verify(artifact)
        if ";" in clause:
            raise ValueError("invalid_query_clause")
        with duckdb.connect(":memory:") as connection:
            result = connection.execute(
                f"SELECT * FROM read_parquet(?) {clause}", [str(artifact.path), *(params or [])]
            )
            columns = [item[0] for item in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def frame(self, table: str):
        artifact = self.artifact(table)
        self._verify(artifact)
        with duckdb.connect(":memory:") as connection:
            return connection.execute("SELECT * FROM read_parquet(?)", [str(artifact.path)]).fetch_df()


@lru_cache(maxsize=4)
def _repository(root: str) -> CanonicalRepository:
    return CanonicalRepository(Path(root))


def repository() -> CanonicalRepository:
    return _repository(str(data_dir().resolve()))
