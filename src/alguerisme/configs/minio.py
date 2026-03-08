"""MinIO configuration models."""

import os

from pydantic import BaseModel, Field, PrivateAttr, SecretStr

from alguerisme.utils.secrets import get_secret


class MinioConfig(BaseModel):
    """Configuration for MinIO object storage.

    Connection settings (host, port, secure) are loaded from environment variables.
    Bucket name and region are configured via YAML config file.

    Environment Variables:
        MINIO_HOST: MinIO host
        MINIO_PORT: MinIO port
        MINIO_SECURE: Use HTTPS (true/false)

    Secrets:
        minio_root_user: MinIO access key
        minio_root_password: MinIO secret key

    Attributes
    ----------
    host : str
        MinIO server host
    port : int
        MinIO server port
    secure : bool
        Use HTTPS instead of HTTP
    bucket_name : str
        Bucket name for storing images
    region : str
        Region name (optional, for S3 compatibility)

    """

    model_config = {"arbitrary_types_allowed": True}

    # Connection settings - loaded from environment
    host: str = Field(
        default_factory=lambda: os.getenv("MINIO_HOST", "minio"),
        description="MinIO server host",
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("MINIO_PORT", "9000")),
        description="MinIO server port",
    )
    secure: bool = Field(
        default_factory=lambda: os.getenv("MINIO_SECURE", "false").lower() == "true",
        description="Use HTTPS connection",
    )

    # Application settings - configured in YAML
    bucket_name: str = Field(
        default="alguerisme-images", description="Bucket name for storing images"
    )
    region: str = Field(
        default="us-east-1", description="Region name for S3 compatibility"
    )

    # Private cached credentials
    _access_key: SecretStr | None = PrivateAttr(default=None)
    _secret_key: SecretStr | None = PrivateAttr(default=None)
    _endpoint: str | None = PrivateAttr(default=None)

    @property
    def access_key(self) -> str:
        """Read and cache the MinIO access key from secrets."""
        if self._access_key is None:
            self._access_key = SecretStr(get_secret("minio_root_user"))
        return self._access_key.get_secret_value()

    @property
    def secret_key(self) -> str:
        """Read and cache the MinIO secret key from secrets."""
        if self._secret_key is None:
            self._secret_key = SecretStr(get_secret("minio_root_password"))
        return self._secret_key.get_secret_value()

    @property
    def endpoint(self) -> str:
        """Construct the MinIO endpoint from host and port."""
        if self._endpoint is None:
            self._endpoint = f"{self.host}:{self.port}"
        return self._endpoint
