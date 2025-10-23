# api/tests.py
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, StreamingResponse
from models import BitsBySeedIn
from services.bitstream import ascii_bits_stream, binary_stream

router = APIRouter()

@router.post("/tests/bitstream/by-seed")
async def bitstream_by_seed(body: BitsBySeedIn = Body(...)):
    try:
        seed = bytes.fromhex(body.seed_hex)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "seed_hex must be hex"})
    if len(seed) != 32:
        return JSONResponse(status_code=400, content={"error": "seed must be 32 bytes (64 hex chars)"})

    filename = f"bits_{body.bits}_{body.fmt}.{'txt' if body.fmt=='txt' else 'bin'}"

    if body.fmt == "txt":
        gen = ascii_bits_stream(seed, body.bits, body.sep)
        media = "text/plain; charset=utf-8"
    else:
        gen = binary_stream(seed, body.bits)
        media = "application/octet-stream"

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(gen, media_type=media, headers=headers)
