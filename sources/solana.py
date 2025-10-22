# app/sources/solana.py
import base58, httpx, asyncio
from typing import List, Dict, Tuple, Any, Optional
from settings import settings

SOLSCAN_BLOCK = "https://solscan.io/block/{}"

# параметры сканирования (можно вынести в settings)
BATCH_SIZE = 20       # сколько слотов проверяем за итерацию
CONCURRENCY = 6       # параллелизм запросов getBlock
MAX_SCAN = 400        # максимум слотов, которые готовы отсканировать назад

async def _rpc(method: str, params: list[Any], timeout: float = 20.0):
    async with httpx.AsyncClient(timeout=timeout) as cli:
        r = await cli.post(settings.SOLANA_RPC_URL, json={
            "jsonrpc": "2.0", "id": 1, "method": method, "params": params
        })
        r.raise_for_status()
        j = r.json()
        if "error" in j:
            # пробрасываем как исключение для верхнего уровня
            raise RuntimeError(str(j["error"]))
        return j["result"]

async def get_latest_slot() -> int:
    return int(await _rpc("getSlot", [{"commitment":"finalized"}]))

async def _get_block_safe(slot: int) -> Optional[dict]:
    """
    Возвращает dict блока или None (если слот пропущен/не найден/ошибка).
    Агрессивно гасим “улетающие” ошибки RPC, чтобы цикл не зависал.
    """
    try:
        params = [slot, {
            "transactionDetails": "none",
            "rewards": False,
            "commitment": "finalized",
            # поддерживаем v0 (legacy тоже ок)
            "maxSupportedTransactionVersion": 0
        }]
        return await _rpc("getBlock", params, timeout=15.0)
    except Exception:
        return None  # пропускаем слот

async def _gather_with_limit(tasks, limit: int):
    sem = asyncio.Semaphore(limit)
    async def run(coro):
        async with sem:
            return await coro
    return await asyncio.gather(*(run(t) for t in tasks))

async def solana_beacon(last_n: int) -> Tuple[bytes, List[Dict[str, Any]]]:
    """
    Ищем не менее last_n финализированных блоков, сканируя назад BATCHами,
    с параллельными запросами и верхней границей MAX_SCAN.
    """
    latest = await get_latest_slot()
    details: List[Dict[str, Any]] = []
    concat = b""

    scanned = 0
    cursor = latest

    while len(details) < last_n and cursor > 0 and scanned < MAX_SCAN:
        # берём окно слотов [cursor .. cursor-BATCH_SIZE+1]
        window = list(range(cursor, max(0, cursor - BATCH_SIZE), -1))
        scanned += len(window)

        # параллельно тянем блоки
        blocks = await _gather_with_limit(
            [ _get_block_safe(s) for s in window ],
            limit=CONCURRENCY
        )

        for slot, blk in zip(window, blocks):
            if blk and blk.get("blockhash"):
                bh = blk["blockhash"]
                try:
                    raw = base58.b58decode(bh)
                except Exception:
                    continue
                details.append({
                    "slot": slot,
                    "blockhash": bh,
                    "explorerUrl": SOLSCAN_BLOCK.format(slot),
                })
                concat += raw
                if len(details) >= last_n:
                    break

        cursor = window[-1] - 1  # двигаем курсор дальше назад

    if len(details) == 0:
        raise RuntimeError("No finalized Solana blocks found (RPC/scan window exhausted)")

    return concat, details
