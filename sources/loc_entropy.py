import time
from blake3 import blake3

def cpu_jitter_bytes(samples: int = 20000) -> bytes:
    """
    Измеряем наносекундные дельты tight-loop; берём младший байт каждой дельты.
    Возвращаем "сырые" байты дельт (они попадут в transcript).
    """
    last = time.perf_counter_ns()
    out = bytearray()
    for _ in range(samples):
        now = time.perf_counter_ns()
        dt = now - last
        out.append(dt & 0xFF)  # LSB
        last = now
    return bytes(out)
