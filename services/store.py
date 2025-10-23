# services/store.py
import os, json, tempfile, time
from typing import Any, Dict, List, Optional

STORE_DIR = os.environ.get("STORE_DIR", "./storage/draws")

def _ensure_dir():
    os.makedirs(STORE_DIR, exist_ok=True)

def _path(draw_id: str) -> str:
    return os.path.join(STORE_DIR, f"{draw_id}.json")

def save_draw(record: Dict[str, Any]) -> None:
    """Атомарная запись JSON-снимка тиража."""
    _ensure_dir()
    draw_id = record["drawId"]
    record.setdefault("createdAt", int(time.time() * 1000))
    tmp_fd, tmp_path = tempfile.mkstemp(dir=STORE_DIR, prefix=f".{draw_id}.", suffix=".tmp")
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, _path(draw_id))

def load_draw(draw_id: str) -> Optional[Dict[str, Any]]:
    p = _path(draw_id)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def list_draws(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    _ensure_dir()
    items: List[Dict[str, Any]] = []
    for name in os.listdir(STORE_DIR):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(STORE_DIR, name), "r", encoding="utf-8") as f:
                j = json.load(f)
            items.append({
                "drawId": j["drawId"],
                "createdAt": j.get("createdAt"),
                "sources": list((j.get("sources") or {}).keys()),
                "numberU64": (j.get("result") or {}).get("u64"),
            })
        except Exception:
            continue
    items.sort(key=lambda x: x.get("createdAt") or 0, reverse=True)
    return items[offset:offset+limit]
