# main.py
from fastapi import FastAPI
from settings import settings

from api.stream import router as stream_router
from api.draws import router as draws_router
from api.entropy import router as entropy_router
from api.tests import router as tests_router
from api.range import router as range_router
from api.history import router as history_router

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