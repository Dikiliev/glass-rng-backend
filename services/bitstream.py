# services/bitstream.py
import itertools
from typing import Iterator
from blake3 import blake3

# Таблица «байт -> 8 символов '0'/'1'» (MSB→LSB)
_BITSTR = [format(b, "08b") for b in range(256)]

def stream_bytes_from_seed(seed: bytes, total_bytes: int, chunk: int = 65536) -> Iterator[bytes]:
    """
    Криптографический поток байтов из seed:
    keyed BLAKE3(seed) поверх счётчика (LE64). 32B на шаг.
    """
    assert len(seed) == 32, "seed must be 32 bytes"
    produced = 0
    counter = 0
    while produced < total_bytes:
        need = min(chunk, total_bytes - produced)
        buf = bytearray()
        while len(buf) < need:
            h = blake3(key=seed)
            h.update(counter.to_bytes(8, "little"))
            buf.extend(h.digest())
            counter += 1
        out = bytes(buf[:need])
        produced += len(out)
        yield out

def ascii_bits_stream(seed: bytes, total_bits: int, sep: str) -> Iterator[bytes]:
    """
    ASCII '0'/'1'. MSB-ориентация.
    sep: "none" | "newline"
    """
    total_bytes = (total_bits + 7) // 8
    produced_bits = 0
    for chunk in stream_bytes_from_seed(seed, total_bytes):
        bit_str = "".join(_BITSTR[b] for b in chunk)
        take = min(len(bit_str), total_bits - produced_bits)
        s = bit_str[:take]
        if sep == "newline":
            s = "\n".join(s) + "\n"
        produced_bits += take
        if not s:
            break
        yield s.encode("ascii")

def binary_stream(seed: bytes, total_bits: int) -> Iterator[bytes]:
    """
    Сырые байты; последний неполный байт затираем снизу (LSB), чтобы получить ровно total_bits.
    """
    total_bytes = (total_bits + 7) // 8
    rem = total_bits % 8
    produced = 0
    for chunk in stream_bytes_from_seed(seed, total_bytes):
        produced_next = produced + len(chunk)
        if produced_next < total_bytes:
            yield chunk
        else:
            if rem == 0:
                yield chunk
            else:
                cutoff = total_bytes - produced
                last = bytearray(chunk[:cutoff])
                last[-1] &= (0xFF << (8 - rem)) & 0xFF
                yield bytes(last)
        produced = produced_next
