# api/draws.py
import binascii
from time import time
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from settings import settings
from streams import hub
from models import SolDrawIn, SolDrawOut
from rng.local_pool import clear_draw, root_hex, bytes_total
from sources.solana import solana_beacon
from services.collect import CollectParams, collect_server_entropy
from services.mix import emit_mix_and_result
from services.store import save_draw, set_current_draw, get_current_draw, list_draws  # <<-- добавь импорт

router = APIRouter()


@router.post("/draws/solana", response_model=SolDrawOut)
async def draw_solana(body: SolDrawIn = Body(...)):
    draw_id = body.draw_id
    blocks = body.blocks or settings.SOL_BLOCKS

    clear_draw(draw_id)

    await hub.emit(draw_id, {"type": "commit", "drawId": draw_id, "blocks": blocks, "source": "SOLANA"})
    await hub.emit(draw_id, {"type": "block.waiting", "drawId": draw_id,
                             "note": f"Fetching last {blocks} finalized Solana blocks"})

    try:
        beacon_bytes, details = await solana_beacon(blocks)
    except Exception as e:
        msg = f"Solana RPC error: {e}"
        await hub.emit(draw_id, {"type": "error", "drawId": draw_id, "stage": "solana", "message": msg})
        return JSONResponse(status_code=500, content={"error": msg})

    beacon_hex = binascii.hexlify(beacon_bytes).decode()
    await hub.emit(draw_id, {
        "type": "block.finalized_all", "drawId": draw_id,
        "explorers": details, "beaconHex": beacon_hex
    })

    p = CollectParams(
        collect_ms=getattr(body, "collect_ms", 8000) or 0,
        srv_jitter=getattr(body, "srv_jitter", True),
        srv_jitter_samples=getattr(body, "srv_jitter_samples", 12000) or 12000,
        srv_urandom_bytes=getattr(body, "srv_urandom_bytes", 1024) or 0,
        require_loc=getattr(body, "require_loc", False),
        min_loc_bytes=getattr(body, "min_loc_bytes", 0) or 0,
    )
    try:
        await collect_server_entropy(draw_id, p)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    # ——— MIX + RESULT (возвращает inputs/compare/trace для истории)
    mix_res = await emit_mix_and_result(draw_id, beacon_bytes, beacon_hex)
    seed_hex = mix_res["seed_hex"]
    number_u64 = mix_res["number_u64"]
    inputs = mix_res["inputs"]
    compare_obj = mix_res["compare"]
    trace_obj = mix_res["trace"]

    # ——— СНИМОК ДЛЯ ИСТОРИИ
    record = {
        "drawId": draw_id,
        "createdAt": int(time() * 1000),
        "sources": {
            "SOL": {
                "blocks": details,  # список блоков (slot/hash/url)
                "beaconHex": beacon_hex
            }
        },
        "inputs": inputs,  # например ["PUB"] или ["PUB","LOC"]
        "entropy": {
            "locRoot": root_hex(draw_id) if bytes_total(draw_id) > 0 else None
            # при желании: сюда можно добавить summary из collect_server_entropy
        },
        "compare": compare_obj,  # PUB vs PUB+LOC
        "trace": trace_obj,  # пошаговая трассировка
        "result": {
            "seedHex": seed_hex,
            "u64": number_u64
        }
    }
    save_draw(record)
    set_current_draw(draw_id)

    # ——— HTTP-ответ (как раньше)
    return SolDrawOut(
        draw_id=draw_id,
        seed_hex=seed_hex,
        number_u64=number_u64,
        beacon_hex=beacon_hex,
        solana=details
    )


@router.get("/draws/current")
async def draws_current():
    """Вернёт текущий (последний сгенерированный) drawId.
    Если в памяти нет — возьмём самый свежий элемент из хранилища.
    """
    cur = get_current_draw()
    if not cur:
        try:
            latest = list_draws(limit=1, offset=0)
            if latest:
                cur = latest[0]["drawId"]
        except Exception:
            cur = None
    return {"drawId": cur}
