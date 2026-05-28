"""In-process async event queue with retries and a dead-letter buffer.

The default implementation is intentionally dependency-free so the worker is
useful out of the box. The :class:`EventQueue` interface is the right shape to
swap in NATS, Redis Streams, or SQS later.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class QueuedEvent:
    payload: dict[str, Any]
    attempts: int = 0
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class EventQueue:
    def __init__(self, max_size: int = 1024) -> None:
        self._queue: asyncio.Queue[QueuedEvent] = asyncio.Queue(maxsize=max_size)
        self._dead_letter: deque[QueuedEvent] = deque(maxlen=256)

    async def publish(self, payload: dict[str, Any]) -> None:
        await self._queue.put(QueuedEvent(payload=payload))

    async def next(self) -> QueuedEvent:
        return await self._queue.get()

    def ack(self) -> None:
        self._queue.task_done()

    def nack(self, evt: QueuedEvent, error: str, max_attempts: int = 3) -> None:
        evt.attempts += 1
        evt.last_error = error
        self._queue.task_done()
        if evt.attempts >= max_attempts:
            self._dead_letter.append(evt)
            log.warning("event_dead_lettered attempts=%s error=%s", evt.attempts, error)
        else:
            asyncio.get_event_loop().call_later(
                min(2 ** evt.attempts, 30),
                lambda: asyncio.ensure_future(self._queue.put(evt)),
            )

    @property
    def dead_letter(self) -> list[QueuedEvent]:
        return list(self._dead_letter)

    def qsize(self) -> int:
        return self._queue.qsize()
