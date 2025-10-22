import asyncio, binascii
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from settings import settings
from streams import hub
from models import SolDrawIn, SolDrawOut
from sources.solana import solana_beacon
from rng.mix import hkdf_seed, prng_chacha20, u64_be, domain_hash

from decimal import Decimal, getcontext
getcontext().prec = 50

app = FastAPI(title="ChainMix RNG (Solana-only v1)")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/draws/{draw_id}/stream")
async def stream(draw_id: str):
    async def gen():
        async for chunk in hub.subscribe(draw_id):
            yield chunk
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.post("/draws/solana", response_model=SolDrawOut)
async def draw_solana(body: SolDrawIn):
    draw_id = body.draw_id
    blocks = body.blocks or settings.SOL_BLOCKS

    await hub.emit(draw_id, {"type":"commit", "drawId": draw_id, "blocks": blocks, "source":"SOLANA"})
    await hub.emit(draw_id, {"type":"block.waiting", "drawId": draw_id, "note": f"Fetching last {blocks} finalized Solana blocks"})

    print('solana_beacon...')
    try:
        beacon_bytes, details = await solana_beacon(blocks)
    except Exception as e:
        # важно: сообщаем на фронт и возвращаем понятную ошибку
        msg = f"Solana RPC error: {e}"
        await hub.emit(draw_id, {"type":"error", "drawId": draw_id, "stage": "solana", "message": msg})
        return JSONResponse(status_code=500, content={"error": msg})

    beacon_hex = binascii.hexlify(beacon_bytes).decode()

    print('finalizing_all...')
    await hub.emit(draw_id, {
        "type": "block.finalized_all",
        "drawId": draw_id,
        "explorers": details,
        "beaconHex": beacon_hex,  # <-- отдадим в SSE
    })

    await hub.emit(draw_id, {"type": "mix.start", "drawId": draw_id, "inputs": ["PUB"]})
    pub_component = domain_hash(b"SOL", beacon_bytes)  # H("SOL"||beacon)

    seed = hkdf_seed(draw_id, {"PUB": pub_component})
    rnd = prng_chacha20(seed, 64)
    num = u64_be(rnd)

    # u in [0,1) как строка и как дробь
    TWO64 = 1 << 64
    u01_decimal = str((Decimal(num) / Decimal(TWO64)).quantize(Decimal(1) / Decimal(10 ** 18)))  # 18 знаков
    u01_num = str(num)
    u01_den = str(TWO64)

    # Отдадим пошаговую трассировку отдельным событием
    await hub.emit(draw_id, {
        "type": "mix.trace",
        "drawId": draw_id,
        "beaconHex": beacon_hex,
        "pubComponentHex": pub_component.hex(),
        "hkdfSaltHex": __import__("binascii").hexlify(
            __import__("blake3").blake3(b"CM|" + draw_id.encode()).digest()).decode(),
        "seedHex": seed.hex(),
        "chachaFirst16Hex": rnd[:16].hex(),
        "u64": str(num),
        "u01": {"fraction": {"num": u01_num, "den": u01_den}, "decimal18": u01_decimal}
    })

    await hub.emit(draw_id, {"type": "result", "drawId": draw_id, "seedHex": seed.hex(), "number": str(num)})

    # и вернём в ответе тоже:
    return SolDrawOut(
        draw_id=draw_id,
        seed_hex=seed.hex(),
        number_u64=str(num),
        beacon_hex=beacon_hex,
        solana=details,
    )
