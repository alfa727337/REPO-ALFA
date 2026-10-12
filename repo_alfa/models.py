from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


ScanMode = Literal["quick", "standard", "deep", "forensic", "reconstruction", "exhaustive"]


class ScanConfig(BaseModel):
    target: HttpUrl
    mode: ScanMode = "standard"
    output_root: Path = Path("output")
    max_depth: int = Field(default=2, ge=0, le=25)
    timeout_seconds: float = Field(default=30.0, gt=0)
    retries: int = Field(default=3, ge=0, le=20)
    browser: bool = True
    same_origin_only: bool = True
    screenshot: bool = True


class ModuleResult(BaseModel):
    name: str
    status: Literal["complete", "partial", "failed", "skipped"]
    started_at: datetime
    finished_at: datetime
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    recovered_failures: int = 0


class ScanReport(BaseModel):
    target: str
    mode: ScanMode
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    modules: list[ModuleResult] = Field(default_factory=list)
    routes: list[str] = Field(default_factory=list)
    observed_endpoints: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    fatal_errors: list[str] = Field(default_factory=list)

    @property
    def completed(self) -> bool:
        return self.finished_at is not None and not self.fatal_errors
