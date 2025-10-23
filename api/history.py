# api/history.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.store import list_draws, load_draw

router = APIRouter()

@router.get("/history")
async def history_list(limit: int = 50, offset: int = 0):
    return {"items": list_draws(limit, offset)}

@router.get("/history/{draw_id}")
async def history_item(draw_id: str):
    rec = load_draw(draw_id)
    if not rec:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return rec
