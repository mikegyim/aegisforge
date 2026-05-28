"""Background worker that pulls events off the queue and posts them to the API.

The worker is the thing you point Prometheus alertmanager / Falco webhook /
Kubernetes-events-watcher at; it normalizes payloads and forwards to the
control plane. In production it would also batch + de-dup, which the queue
abstraction is set up to support.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import httpx
import structlog

from .queue import EventQueue, QueuedEvent

log = structlog.get_logger(__name__)


class AegisForgeWorker:
    def __init__(
        self,
        queue: EventQueue,
        api_base: str,
        api_key: str | None = None,
        max_concurrency: int = 4,
    ) -> None:
        self._queue = queue
        self._api_base = api_base.rstrip("/")
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["X-API-Key"] = api_key
        self._sem = asyncio.Semaphore(max_concurrency)
        self._stop = asyncio.Event()

    async def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        async with httpx.AsyncClient(timeout=30.0, headers=self._headers) as client:
            while not self._stop.is_set():
                try:
                    evt = await asyncio.wait_for(self._queue.next(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                asyncio.create_task(self._handle(client, evt))

    async def _handle(self, client: httpx.AsyncClient, evt: QueuedEvent) -> None:
        async with self._sem:
            try:
                resp = await client.post(f"{self._api_base}/events", json=evt.payload)
                if resp.status_code >= 400:
                    raise RuntimeError(f"api {resp.status_code}: {resp.text[:200]}")
                self._queue.ack()
                log.info(
                    "event.forwarded",
                    event_id=evt.payload.get("event_id"),
                    risk=resp.json().get("simulation", {}).get("risk_score"),
                )
            except Exception as exc:
                log.warning("event.forward_failed", error=str(exc), attempts=evt.attempts)
                self._queue.nack(evt, error=str(exc))


def _example_event() -> dict[str, Any]:
    return {
        "event_id": "evt-demo-001",
        "event_type": "observability",
        "cluster": "dev-us-east-1",
        "namespace": "ci",
        "workload": "gitlab-runner",
        "severity": "critical",
        "signal": "node_memory_pressure",
        "message": "Memory pressure detected after CI workload spike",
        "metadata": {"source": "worker-demo"},
    }


async def main() -> None:
    queue = EventQueue()
    await queue.publish(_example_event())
    worker = AegisForgeWorker(
        queue=queue,
        api_base=os.environ.get("AEGIS_API_BASE", "http://localhost:8000"),
        api_key=os.environ.get("AEGIS_API_KEY"),
    )

    async def _shutdown() -> None:
        await asyncio.sleep(2.0)
        await worker.stop()

    print(json.dumps({"dispatched": _example_event()}, indent=2), file=sys.stdout)
    await asyncio.gather(worker.run(), _shutdown())


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
