# main.py
from fastapi import FastAPI
from asyncio import create_task, sleep
from time import time
from settings import settings

from api.stream import router as stream_router
from api.draws import router as draws_router
from api.entropy import router as entropy_router
from api.tests import router as tests_router
from api.range import router as range_router
from api.history import router as history_router
from api.draws import draw_solana
from services.store import set_current_draw
from models import SolDrawIn
from streams import hub

app = FastAPI(title="ChainMix RNG (Solana-only v1)")

@app.get("/health")
def health():
    return {"ok": True}


# Подключаем роутеры (пути не меняем)
app.include_router(stream_router)   # /draws/{draw_id}/stream
app.include_router(draws_router)    # /draws/solana
app.include_router(entropy_router)  # /entropy/...
app.include_router(tests_router)    # /tests/bitstream/by-seed
app.include_router(range_router)
app.include_router(history_router)


@app.on_event("startup")
async def _start_auto_generator():
    async def _loop():
        while True:
            try:
                draw_id = f"auto-{int(time()*1000)}"
                body = SolDrawIn(
                    draw_id=draw_id,
                    blocks=settings.SOL_BLOCKS,
                    collect_ms=1200,
                    require_loc=False,
                    min_loc_bytes=0,
                )
                # Сначала объявим текущий ID, чтобы клиенты успели подписаться на SSE до первых событий
                set_current_draw(draw_id)
                # оповестим глобальный канал о новом текущем ID
                await hub.emit("__current__", {"type": "current", "drawId": draw_id})
                # Используем тот же путь, что и HTTP-эндпоинт, чтобы отправить SSE и сохранить историю
                await draw_solana(body)
                print(f'[{draw_id}] generate finished.')
            except Exception as e:
                # Логируем и продолжаем цикл, чтобы не останавливать генератор
                print("auto-draw error:", e)
            await sleep(10)

    create_task(_loop())