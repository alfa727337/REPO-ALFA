from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Checkpoint:
    stage: str
    completed: bool
    payload: dict[str, Any]


class CheckpointStore:
    def __init__(self, root: Path) -> None:
        self.root = root / "checkpoints"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> Path:
        path = self.root / f"{checkpoint.stage}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(checkpoint), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return path

    def load(self, stage: str) -> Checkpoint | None:
        path = self.root / f"{stage}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Checkpoint(**data)

    def completed_stages(self) -> set[str]:
        result: set[str] = set()
        for path in self.root.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("completed"):
                    result.add(str(data.get("stage")))
            except (OSError, json.JSONDecodeError):
                continue
        return result
