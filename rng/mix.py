from blake3 import blake3
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from Crypto.Cipher import ChaCha20

def domain_hash(tag: bytes, data: bytes) -> bytes:
    return blake3(tag + data).digest()

def hkdf_seed(draw_id: str, sources: dict[str, bytes]) -> bytes:
    """
    sources: {"PUB": ..., "LOC": ..., "Q__": ..., "SRV": ...} – любые подмножества
    доменная сепарация тэгами ключей
    """
    ikm = b"".join(domain_hash(k.encode(), v) for k, v in sorted(sources.items()))
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=blake3(b"CM|"+draw_id.encode()).digest(),
        info=b"CM|seed",
    )
    return hkdf.derive(ikm)

def prng_chacha20(seed: bytes, nbytes: int = 64) -> bytes:
    cipher = ChaCha20.new(key=seed, nonce=b"\x00"*8)
    return cipher.encrypt(b"\x00"*nbytes)

def u64_be(first64: bytes) -> int:
    import struct
    return struct.unpack(">Q", first64[:8])[0]
