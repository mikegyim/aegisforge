import asyncio
import json
from dataclasses import dataclass


@dataclass
class AgentEnvelope:
    event_type: str
    payload: dict


class AgentWorker:
    def __init__(self, name: str) -> None:
        self.name = name

    async def handle(self, envelope: AgentEnvelope) -> dict:
        await asyncio.sleep(0)
        return {
            "worker": self.name,
            "handled": True,
            "event_type": envelope.event_type,
            "summary": f"{self.name} processed event",
        }


async def main() -> None:
    worker = AgentWorker("aegisforge-background-agent")
    result = await worker.handle(
        AgentEnvelope(event_type="observability", payload={"signal": "memory_pressure"})
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
