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
    assert q.qsize() == 0


async def test_nack_dead_letters_at_max_attempts():
    """When attempts reach max_attempts, nack moves the event to the dead-letter
    buffer. We simulate prior failed attempts by pre-setting ``evt.attempts`` so
    we only consume the queue (and call ``task_done`` via nack) once - that
    keeps task_done / put counts balanced.
    """
    q = EventQueue()
    await q.publish({"event_id": "y"})
    evt = await q.next()
    evt.attempts = 2  # pretend we already retried twice
    q.nack(evt, error="boom", max_attempts=3)
    assert any(e.payload["event_id"] == "y" for e in q.dead_letter)
    assert evt.last_error == "boom"


async def test_nack_below_max_does_not_dead_letter():
    q = EventQueue()
    await q.publish({"event_id": "z"})
    evt = await q.next()
    q.nack(evt, error="transient", max_attempts=5)
    assert all(e.payload["event_id"] != "z" for e in q.dead_letter)
