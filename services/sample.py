# services/sample.py
from __future__ import annotations
from typing import Tuple
from blake3 import blake3

TWO64 = 1 << 64

def derive_subseed(seed: bytes, label: str) -> bytes:
    """Под-сид для независимого использования (domain separation)."""
    h = blake3(key=seed)
    h.update(b"SUB|" + label.encode("utf-8"))
    return h.digest()  # 32 байта

def _u64_stream_from_subseed(subseed: bytes):
    """Поток u64: BLAKE3-CTR (key=subseed, data=counter_le)."""
    counter = 0
    while True:
        h = blake3(key=subseed)
        h.update(counter.to_bytes(8, "little"))
        block = h.digest()  # 32B
        # возьмём первые 8 байт как big-endian u64
        x = int.from_bytes(block[:8], "big")
        yield x
        counter += 1

def sample_range_by_seed(seed: bytes, n1: int, n2: int, label: str = "RANGE/v1") -> Tuple[int, dict]:
    """
    Честная выборка в [lo, hi] с rejection sampling.
    Допустим размер диапазона R <= 2^64.
    """
    if len(seed) != 32:
        raise ValueError("seed must be 32 bytes")
    lo, hi = sorted((int(n1), int(n2)))
    R = hi - lo + 1
    if R <= 0:
        raise ValueError("empty range")
    if R > TWO64:
        raise ValueError("range size too large (>2^64)")

    subseed = derive_subseed(seed, label)
    gen = _u64_stream_from_subseed(subseed)
    # порог для честного модульного маппинга
    t = (TWO64 // R) * R

    attempts = 0
    rejected = 0
    while True:
        attempts += 1
        x = next(gen)
        if x < t:
            value = lo + (x % R)
            meta = {
                "lo": lo, "hi": hi, "rangeSize": R,
                "attempts": attempts, "rejected": rejected,
                "label": label, "subseedHex": subseed.hex(),
                "threshold": str(t), "xUsed": str(x)
            }
            return value, meta
        rejected += 1
