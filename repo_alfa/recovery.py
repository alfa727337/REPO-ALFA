from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class RecoveryEvent:
    operation: str
    attempt: int
    error: str
    recovered: bool = False


@dataclass
class RecoveryEngine:
    retries: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0
    events: list[RecoveryEvent] = field(default_factory=list)

    async def run(self, operation: str, fn: Callable[[], Awaitable[T]]) -> T:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                result = await fn()
                if attempt:
                    self.events.append(
                        RecoveryEvent(operation=operation, attempt=attempt, error="", recovered=True)
                    )
                return result
            except Exception as exc:
                last_error = exc
                self.events.append(
                    RecoveryEvent(operation=operation, attempt=attempt, error=repr(exc))
                )
                if attempt >= self.retries:
                    break
                delay = min(self.max_delay, self.base_delay * (2**attempt))
                delay += random.random() * min(0.25, delay / 4)
                await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    def summary(self) -> dict[str, Any]:
        return {
            "attempts": len(self.events),
            "recovered": sum(1 for event in self.events if event.recovered),
            "failures": [asdict(event) for event in self.events if event.error],
        }
