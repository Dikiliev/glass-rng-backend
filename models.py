from pydantic import BaseModel, Field
from typing import Literal

class SolDrawIn(BaseModel):
    draw_id: str
    blocks: int = 3

    # окно сбора серверной энтропии
    collect_ms: int = 8000

    # авто-источники
    srv_jitter: bool = True
    srv_jitter_samples: int = 12000
    srv_urandom_bytes: int = 1024

    # строгие требования (по желанию)
    require_loc: bool = False
    min_loc_bytes: int = 0

class SolDrawOut(BaseModel):
    draw_id: str
    seed_hex: str
    number_u64: str
    beacon_hex: str
    solana: list

class UserEntropyIn(BaseModel):
    payload_hex: str = Field(..., description="raw bytes (hex)")

class BitsBySeedIn(BaseModel):
    seed_hex: str = Field(..., description="HKDF seed в hex (32 байта)")
    bits: int = Field(1_000_000, ge=1, description="Сколько бит сгенерировать")
    fmt: Literal["txt","bin"] = "txt"            # txt = ASCII '0'/'1', bin = сырые байты
    sep: Literal["none","newline"] = "none"      # для txt: без разделителей или по строкам
