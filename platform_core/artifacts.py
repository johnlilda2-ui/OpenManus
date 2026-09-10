from __future__ import annotations

from pathlib import Path
import shutil
from typing import BinaryIO

import boto3

from platform_core.settings import settings


class ArtifactStorage:
    def __init__(self) -> None:
        self.root = Path(settings.artifact_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.bucket = settings.s3_bucket
        self.s3 = None
        if self.bucket:
            self.s3 = boto3.client("s3", endpoint_url=settings.s3_endpoint_url or None, region_name=settings.s3_region or None)

    def put(self, storage_key: str, stream: BinaryIO) -> int:
        if self.s3:
            self.s3.upload_fileobj(stream, self.bucket, storage_key)
            return 0
        target = self.root / storage_key
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as output:
            shutil.copyfileobj(stream, output, length=1024 * 1024)
        return target.stat().st_size

    def open(self, storage_key: str):
        if self.s3:
            return None
        return (self.root / storage_key).open("rb")

    def delete(self, storage_key: str) -> None:
        if self.s3:
            self.s3.delete_object(Bucket=self.bucket, Key=storage_key)
            return
        target = self.root / storage_key
        if target.exists():
            target.unlink()

    def presigned_url(self, storage_key: str, expires: int = 900) -> str | None:
        if not self.s3:
            return None
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=expires,
        )


storage = ArtifactStorage()
