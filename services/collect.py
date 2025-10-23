# services/collect.py
import asyncio, os
from streams import hub
from rng.local_pool import add_packet, bytes_total, packet_count, root_hex
from sources.loc_entropy import cpu_jitter_bytes

class CollectParams:
    def __init__(self, collect_ms=8000, srv_jitter=True, srv_jitter_samples=12000, srv_urandom_bytes=1024,
                 require_loc=False, min_loc_bytes=0):
        self.collect_ms = max(0, int(collect_ms or 0))
        self.srv_jitter = bool(srv_jitter)
        self.srv_jitter_samples = max(1, int(srv_jitter_samples or 1))
        self.srv_urandom_bytes = max(0, int(srv_urandom_bytes or 0))
        self.require_loc = bool(require_loc)
        self.min_loc_bytes = max(0, int(min_loc_bytes or 0))

class CollectResult:
    def __init__(self):
        self.urandom_bytes_used = 0
        self.jitter_batches = 0
        self.jitter_bytes_total = 0
        self.jitter_samples_total = 0

async def collect_server_entropy(draw_id: str, p: CollectParams) -> CollectResult:
    res = CollectResult()
    if p.collect_ms <= 0:
        return res

    # Одноразовый OS RNG
    if p.srv_urandom_bytes > 0:
        data = os.urandom(p.srv_urandom_bytes)
        res.urandom_bytes_used = len(data)
        add_packet(draw_id, data)
        await hub.emit(draw_id, {
            "type":"loc.progress","drawId":draw_id,"source":"SRV",
            "bytesTotal": bytes_total(draw_id),"packets": packet_count(draw_id),
            "rootHex": root_hex(draw_id)
        })

    await hub.emit(draw_id, {
        "type":"collect.open","drawId":draw_id,
        "deadlineMs": p.collect_ms,
        "bytes": bytes_total(draw_id),
        "rootHex": root_hex(draw_id) if bytes_total(draw_id)>0 else None
    })

    loop = asyncio.get_event_loop()
    end  = loop.time() + p.collect_ms/1000.0

    while True:
        remain = end - loop.time()
        if remain <= 0: break

        if p.srv_jitter:
            data = cpu_jitter_bytes(samples=p.srv_jitter_samples)
            add_packet(draw_id, data)
            res.jitter_batches += 1
            res.jitter_bytes_total += len(data)
            res.jitter_samples_total += p.srv_jitter_samples

            await hub.emit(draw_id, {
                "type":"loc.progress","drawId":draw_id,"source":"SRV",
                "bytesTotal": bytes_total(draw_id),"packets": packet_count(draw_id),
                "rootHex": root_hex(draw_id)
            })

        await hub.emit(draw_id, {
            "type":"collect.tick","drawId":draw_id,
            "remainingMs": int(max(0,remain)*1000),
            "bytes": bytes_total(draw_id)
        })
        await asyncio.sleep(1)

    await hub.emit(draw_id, {
        "type":"collect.close","drawId":draw_id,
        "bytes": bytes_total(draw_id),
        "rootHex": root_hex(draw_id) if bytes_total(draw_id)>0 else None
    })

    await hub.emit(draw_id, {
        "type":"collect.summary","drawId":draw_id,
        "bytes": bytes_total(draw_id),
        "rootHex": root_hex(draw_id) if bytes_total(draw_id)>0 else None,
        "urandomBytes": res.urandom_bytes_used,
        "jitterBatches": res.jitter_batches,
        "jitterBytes": res.jitter_bytes_total,
        "jitterSamplesTotal": res.jitter_samples_total,
    })

    # строгая проверка
    if p.require_loc and bytes_total(draw_id) < max(1, p.min_loc_bytes):
        msg = f"Not enough local entropy: {bytes_total(draw_id)} < {p.min_loc_bytes}"
        await hub.emit(draw_id, {"type":"error","drawId":draw_id,"stage":"collect","message":msg})
        raise ValueError(msg)

    return res
