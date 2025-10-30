import asyncio, json
from typing import AsyncGenerator, Dict, List, Tuple

class StreamHub:
    def __init__(self):
        self._subs: Dict[str, List[Tuple[asyncio.Queue, asyncio.Task]]] = {}

    async def subscribe(self, draw_id: str) -> AsyncGenerator[str, None]:
        q: asyncio.Queue = asyncio.Queue()
        # создадим heartbeat-задачу, чтобы периодически пинговать клиента и не давать соединению засыпать/буферизоваться
        async def _heartbeat():
            try:
                while True:
                    await asyncio.sleep(2)
                    # пинги не обязаны парситься фронтом; важен сам чанк для анти-буферизации
                    try:
                        q.put_nowait({"type": "ping", "t": asyncio.get_event_loop().time()})
                    except Exception:
                        pass
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(_heartbeat())
        self._subs.setdefault(draw_id, []).append((q, task))
        try:
            # отправим первичное событие, чтобы клиент понял, что подключение живо
            yield f"data: {json.dumps({'type':'connected','drawId': draw_id})}\n\n"
            while True:
                event = await q.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            subs = self._subs.get(draw_id) or []
            for i, (qq, tt) in enumerate(list(subs)):
                if qq is q:
                    try:
                        tt.cancel()
                    except Exception:
                        pass
                    subs.pop(i)
                    break

    async def emit(self, draw_id: str, event: dict):
        for q, _task in self._subs.get(draw_id, []):
            q.put_nowait(event)

hub = StreamHub()
