import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegisforge_agents.queue import EventQueue


async def test_publish_and_consume():
    q = EventQueue()
    await q.publish({"event_id": "x"})
    evt = await q.next()
    assert evt.payload["event_id"] == "x"
    q.ack()


async def test_nack_dead_letters_after_max_attempts():
    q = EventQueue()
    await q.publish({"event_id": "y"})
    evt = await q.next()
    for _ in range(3):
        q.nack(evt, error="boom", max_attempts=3)
    # give the loop a chance
    await asyncio.sleep(0)
    assert any(e.payload["event_id"] == "y" for e in q.dead_letter)
