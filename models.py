from pydantic import BaseModel, Field
from typing import Dict, Optional, Literal, List

class SolDrawIn(BaseModel):
    draw_id: str = Field(..., description="Произвольный идентификатор тиража")
    blocks: int = Field(3, ge=1, le=12, description="Сколько последних блоков Solana использовать")
    # Зарезервировано под будущие источники:
    include_local: bool = False
    include_quantum: bool = False

class SolDrawOut(BaseModel):
    draw_id: str
    seed_hex: str
    number_u64: str
    beacon_hex: str
    solana: List[dict]
