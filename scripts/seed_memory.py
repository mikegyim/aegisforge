"""Seed the local incident memory with a handful of analyses.

Run after `uvicorn aegisforge.main:app --reload` is up:

    python scripts/seed_memory.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

EXAMPLES = [
    "examples/events/node-memory-pressure.json",
    "examples/events/falco-shell-event.json",
    "examples/events/cost-anomaly.json",
]


async def main() -> int:
    root = Path(__file__).resolve().parents[1]
    base = "http://localhost:8000"
    async with httpx.AsyncClient(timeout=30) as client:
        for example in EXAMPLES:
            payload = json.loads((root / example).read_text())
            r = await client.post(f"{base}/events", json=payload)
            r.raise_for_status()
            d = r.json()
            print(f"{example} -> incident {d['incident_id']} risk={d['simulation']['risk_score']}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
