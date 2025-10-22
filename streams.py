import asyncio, json
from typing import AsyncGenerator, Dict, List

class StreamHub:
    def __init__(self):
        self._subs: Dict[str, List[asyncio.Queue]] = {}

    async def subscribe(self, draw_id: str) -> AsyncGenerator[str, None]:
        q = asyncio.Queue()
        self._subs.setdefault(draw_id, []).append(q)
        try:
            while True:
                event = await q.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            self._subs[draw_id].remove(q)

    async def emit(self, draw_id: str, event: dict):
        for q in self._subs.get(draw_id, []):
            q.put_nowait(event)

hub = StreamHub()
