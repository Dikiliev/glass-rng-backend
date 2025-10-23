from collections import defaultdict
from blake3 import blake3

PACKETS: dict[str, list[bytes]] = defaultdict(list)

def add_packet(draw_id: str, data: bytes):
    PACKETS[draw_id].append(data)

def clear_draw(draw_id: str):
    PACKETS.pop(draw_id, None)

def bytes_total(draw_id: str) -> int:
    return sum(len(p) for p in PACKETS.get(draw_id, []))

def packet_count(draw_id: str) -> int:
    return len(PACKETS.get(draw_id, []))

def root_hex(draw_id: str) -> str:
    h = blake3()
    for p in PACKETS.get(draw_id, []):
        h.update(p)
    return h.hexdigest()

def root_bytes(draw_id: str) -> bytes:
    return bytes.fromhex(root_hex(draw_id)) if bytes_total(draw_id) > 0 else b""
