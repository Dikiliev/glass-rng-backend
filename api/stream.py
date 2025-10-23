# api/stream.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from streams import hub

router = APIRouter()

@router.get("/draws/{draw_id}/stream")
async def stream(draw_id: str):
    async def gen():
        async for chunk in hub.subscribe(draw_id):
            yield chunk
    return StreamingResponse(gen(), media_type="text/event-stream")
