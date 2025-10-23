# api/range.py
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from streams import hub
from services.sample import sample_range_by_seed

router = APIRouter()

class RangeBySeedIn(BaseModel):
    seed_hex: str = Field(..., description="32-byte HKDF seed (hex)")
    n1: int
    n2: int
    label: str = "RANGE/v1"
    draw_id: str | None = None  # если хотим ещё и SSE для текущей сессии

@router.post("/range/by-seed")
async def range_by_seed(body: RangeBySeedIn = Body(...)):
    # валидация seed
    try:
        seed = bytes.fromhex(body.seed_hex)
    except Exception:
        return JSONResponse(status_code=400, content={"error":"seed_hex must be hex"})
    if len(seed) != 32:
        return JSONResponse(status_code=400, content={"error":"seed must be 32 bytes (64 hex)"})

    try:
        value, meta = sample_range_by_seed(seed, body.n1, body.n2, label=body.label)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    # опционально — отправим SSE, чтобы фронт мог логировать
    if body.draw_id:
        await hub.emit(body.draw_id, {
            "type":"range.sample", "drawId": body.draw_id,
            "n1": meta["lo"], "n2": meta["hi"], "label": meta["label"],
            "subseedHex": meta["subseedHex"],
            "attempts": meta["attempts"], "rejected": meta["rejected"],
            "value": str(value)
        })

    return {"value": value, **meta}
