# api/entropy.py
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from models import UserEntropyIn
from streams import hub
from rng.local_pool import add_packet, bytes_total, packet_count, root_hex
from sources.loc_entropy import cpu_jitter_bytes

router = APIRouter()

@router.post("/entropy/{draw_id}/user")
async def entropy_user(draw_id: str, body: UserEntropyIn = Body(...)):
    try:
        data = bytes.fromhex(body.payload_hex)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "payload_hex must be hex"})
    add_packet(draw_id, data)
    await hub.emit(draw_id, {
        "type":"loc.progress","drawId":draw_id,"source":"USER",
        "bytesTotal": bytes_total(draw_id),"packets": packet_count(draw_id),
        "rootHex": root_hex(draw_id),
    })
    return {"ok": True, "root_hex": root_hex(draw_id)}

@router.post("/entropy/{draw_id}/server-jitter")
async def entropy_server_jitter(draw_id: str, samples: int = 20000):
    data = cpu_jitter_bytes(samples=samples)
    add_packet(draw_id, data)
    await hub.emit(draw_id, {
        "type":"loc.progress","drawId":draw_id,"source":"SRV",
        "bytesTotal": bytes_total(draw_id),"packets": packet_count(draw_id),
        "rootHex": root_hex(draw_id),
    })
    return {"ok": True, "added_bytes": len(data), "root_hex": root_hex(draw_id)}
