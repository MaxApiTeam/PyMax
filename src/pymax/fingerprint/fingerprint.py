import hashlib
import json
import struct
from importlib import resources
from typing import Any

from .models import ApkBuildFingerprint


class FingerprintGenerator:
    def __init__(
        self,
    ) -> None:
        self.path = resources.files("pymax._data") / "apk_fingerprints.json"
        self.data = self.load_fingerprints()

    def load_fingerprints(self) -> Any:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def generate_fingerprint(
        self,
        version: str,
        device_id: str,
        calls_seed: int,
        arch: str = "arm64-v8a",
    ) -> bytes | None:
        data = self.data.get(version)
        if not data:
            return None

        model = ApkBuildFingerprint.model_validate(data)

        seed_bytes = struct.pack(">q", calls_seed)
        device_bytes = device_id.encode("utf-8")

        h1 = hashlib.sha256(
            bytes.fromhex(model.certificate_meta_sha256) + seed_bytes + device_bytes
        ).digest()
        h2 = hashlib.sha256(
            bytes.fromhex(model.dex_meta_sha256) + seed_bytes + device_bytes
        ).digest()
        h3 = hashlib.sha256(
            bytes.fromhex(model.so_meta_sha256[arch]) + seed_bytes + device_bytes
        ).digest()

        return h1 + h2 + h3
