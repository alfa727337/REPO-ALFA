from pathlib import Path

import pytest

from repo_alfa.checkpoints import Checkpoint
from repo_alfa.engine import RepoAlfaEngine
from repo_alfa.models import ScanConfig


@pytest.mark.asyncio
async def test_module_resume_uses_completed_checkpoint(tmp_path: Path):
    config = ScanConfig(target="https://example.com", output_root=tmp_path)
    engine = RepoAlfaEngine(config, resume=True)
    engine.checkpoints.save(
        Checkpoint(stage="demo", completed=True, payload={"value": 42})
    )

    async def should_not_run():
        raise AssertionError("checkpointed module was executed")

    result = await engine._module("demo", should_not_run)
    assert result.status == "complete"
    assert result.data["value"] == 42
    assert result.data["_resumed_from_checkpoint"] is True
