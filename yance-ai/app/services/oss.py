from functools import lru_cache

import oss2

from app.core.config import settings


class OSSStorage:
    def __init__(self) -> None:
        if not all(
            [
                settings.oss_endpoint,
                settings.oss_bucket,
                settings.oss_access_key_id,
                settings.oss_access_key_secret,
            ]
        ):
            raise RuntimeError("OSS is not configured")
        auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        self.public_bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)
        internal_endpoint = settings.oss_internal_endpoint or settings.oss_endpoint
        self.internal_bucket = oss2.Bucket(auth, internal_endpoint, settings.oss_bucket)

    def presign_put(self, object_key: str, content_type: str) -> str:
        return self.public_bucket.sign_url(
            "PUT",
            object_key,
            settings.oss_presign_expire_seconds,
            headers={"Content-Type": content_type},
            slash_safe=True,
        )

    def exists(self, object_key: str) -> bool:
        return self.internal_bucket.object_exists(object_key)

    def object_size(self, object_key: str) -> int:
        return int(self.internal_bucket.get_object_meta(object_key).content_length)

    def read_bytes(self, object_key: str, max_bytes: int) -> bytes:
        stream = self.internal_bucket.get_object(object_key)
        payload = stream.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError("Stored object exceeds the configured read limit")
        return payload

    def put_bytes(self, object_key: str, payload: bytes, content_type: str) -> None:
        self.internal_bucket.put_object(
            object_key,
            payload,
            headers={"Content-Type": content_type},
        )


@lru_cache
def get_oss_storage() -> OSSStorage:
    return OSSStorage()
