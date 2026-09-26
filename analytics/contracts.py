"""Validated contracts for canonical offline stage boundaries."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Artifact(BaseModel):
    """One immutable file referenced by a stage contract."""

    model_config = ConfigDict(extra="allow")

    file: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int | None = Field(default=None, ge=0)
    rows: int | None = Field(default=None, ge=0)
    columns: int | None = Field(default=None, ge=0)
    role: str | None = None

    @field_validator("file")
    @classmethod
    def safe_relative_file(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise ValueError("artifact file must be a safe relative path")
        return normalized


class StageContract(BaseModel):
    """Common external contract accepted at every offline stage boundary."""

    model_config = ConfigDict(extra="allow")

    stage: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    exports: list[Artifact] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    raw_files: dict[str, str] | None = None

    @field_validator("raw_files")
    @classmethod
    def safe_raw_files(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        for name, checksum in value.items():
            normalized = name.replace("\\", "/")
            path = PurePosixPath(normalized)
            if not normalized or path.is_absolute() or ".." in path.parts:
                raise ValueError("raw file must be a safe relative path")
            if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
                raise ValueError(f"invalid SHA-256 for raw file {name}")
        return {name.replace("\\", "/"): checksum for name, checksum in value.items()}

    @model_validator(mode="after")
    def unique_artifacts(self) -> "StageContract":
        files = [item.file for item in self.all_artifacts]
        if len(files) != len(set(files)):
            raise ValueError("contract contains duplicate artifact paths")
        return self

    @property
    def all_artifacts(self) -> tuple[Artifact, ...]:
        return tuple(self.exports + self.artifacts)

    def require_artifact(self, file: str) -> Artifact:
        """Return a declared artifact or reject an undeclared dependency."""
        normalized = file.replace("\\", "/")
        for item in self.all_artifacts:
            if item.file == normalized:
                return item
        raise ValueError(f"{self.stage} contract does not declare required artifact: {normalized}")


def contract_payload(
    *,
    stage: str,
    contract_version: str,
    run_id: str,
    exports: list[Artifact],
    **metadata: Any,
) -> StageContract:
    """Create and validate a contract before it reaches the filesystem."""
    return StageContract(
        stage=stage,
        contract_version=contract_version,
        run_id=run_id,
        exports=exports,
        **metadata,
    )
