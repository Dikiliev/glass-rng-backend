# api/stream.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from streams import hub
from services.store import get_current_draw

router = APIRouter()

@router.get("/draws/{draw_id}/stream")
async def stream(draw_id: str):
    async def gen():
        async for chunk in hub.subscribe(draw_id):
            yield chunk
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)


@router.get("/stream/current")
async def stream_current():
    async def gen():
        cur = get_current_draw()
        if cur:
            yield f"data: {{\"type\":\"current\",\"drawId\":\"{cur}\"}}\n\n"
        async for chunk in hub.subscribe("__current__"):
            yield chunk
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)


@router.get("/draws/current/stream")
async def stream_current_compat():
    async def gen():
        cur = get_current_draw()
        if cur:
            yield f"data: {{\"type\":\"current\",\"drawId\":\"{cur}\"}}\n\n"
        async for chunk in hub.subscribe("__current__"):
            yield chunk
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)
