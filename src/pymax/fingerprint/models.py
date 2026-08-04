from pydantic import BaseModel


class ApkBuildFingerprint(BaseModel):
    signature_scheme: str
    certificate_count: int
    certificate_meta_sha256: str
    certificate_sha256: list[str]
    dex_meta_sha256: str
    so_meta_sha256: dict[str, str]
    build_number: int
