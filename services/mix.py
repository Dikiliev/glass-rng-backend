# services/mix.py
import binascii
from decimal import Decimal, getcontext
from blake3 import blake3
from streams import hub
from rng.mix import hkdf_seed, prng_chacha20, u64_be, domain_hash
from rng.local_pool import bytes_total, root_bytes
getcontext().prec = 50
TWO64 = 1 << 64

async def emit_mix_and_result(draw_id: str, beacon_bytes: bytes, beacon_hex: str):
    # источники
    inputs = []
    sources = {}

    pub_component = domain_hash(b"SOL", beacon_bytes)     # доменное хеширование
    sources["PUB"] = pub_component; inputs.append("PUB")

    if bytes_total(draw_id) > 0:                          # локальный шум (если есть)
        loc_root = root_bytes(draw_id)
        sources["LOC"] = domain_hash(b"LOC", loc_root)
        inputs.append("LOC")

    # старт смешивания
    await hub.emit(draw_id, {"type":"mix.start","drawId":draw_id,"inputs":inputs})

    # итоговый seed + число
    seed = hkdf_seed(draw_id, sources)
    rnd  = prng_chacha20(seed, 64)
    num  = u64_be(rnd)
    u01d = str((Decimal(num) / Decimal(TWO64)).quantize(Decimal(1) / Decimal(10**18)))

    # сравнение: только PUB (без LOC)
    pub_only = {"PUB": pub_component}
    pub_seed = hkdf_seed(draw_id, pub_only)
    pub_rnd  = prng_chacha20(pub_seed, 64)
    pub_num  = u64_be(pub_rnd)
    pub_u01d = str((Decimal(pub_num) / Decimal(TWO64)).quantize(Decimal(1) / Decimal(10**18)))

    compare = {
        "pub": {
            "seedHex": pub_seed.hex(),
            "chachaFirst16Hex": pub_rnd[:16].hex(),
            "u64": str(pub_num),
            "u01": {"fraction": {"num": str(pub_num), "den": str(TWO64)}, "decimal18": pub_u01d}
        },
        "pub_loc": {
            "seedHex": seed.hex(),
            "chachaFirst16Hex": rnd[:16].hex(),
            "u64": str(num),
            "u01": {"fraction": {"num": str(num), "den": str(TWO64)}, "decimal18": u01d}
        }
    }
    await hub.emit(draw_id, {"type":"mix.compare","drawId":draw_id, **compare})

    trace = {
        "beaconHex": beacon_hex,
        "pubComponentHex": pub_component.hex(),
        "hkdfSaltHex": blake3(b"CM|"+draw_id.encode()).hexdigest(),
        "seedHex": seed.hex(),
        "chachaFirst16Hex": rnd[:16].hex(),
        "u64": str(num),
        "u01": {"fraction": {"num": str(num), "den": str(TWO64)}, "decimal18": u01d}
    }
    await hub.emit(draw_id, {"type":"mix.trace","drawId":draw_id, **trace})

    await hub.emit(draw_id, {"type":"result","drawId":draw_id,"seedHex":seed.hex(),"number":str(num)})

    # вернём всё нужное для истории
    return {
        "seed_hex": seed.hex(),
        "number_u64": str(num),
        "inputs": inputs,
        "compare": compare,
        "trace": trace,
    }
