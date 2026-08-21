import hashlib
import struct

from .models import ApkBuildFingerprint


class FingerprintGenerator:
    def __init__(self, version_data: ApkBuildFingerprint) -> None:
        self.data = version_data

    def generate_fingerprint(
        self,
        device_id: str,
        calls_seed: int,
        arch: str = "arm64-v8a",
    ) -> bytes | None:
        seed_bytes = struct.pack(">q", calls_seed)
        device_bytes = device_id.encode("utf-8")

        h1 = hashlib.sha256(
            bytes.fromhex(self.data.certificate_meta_sha256) + seed_bytes + device_bytes
        ).digest()
        h2 = hashlib.sha256(
            bytes.fromhex(self.data.dex_meta_sha256) + seed_bytes + device_bytes
        ).digest()
        h3 = hashlib.sha256(
            bytes.fromhex(self.data.so_meta_sha256[arch]) + seed_bytes + device_bytes
        ).digest()

        return h1 + h2 + h3
