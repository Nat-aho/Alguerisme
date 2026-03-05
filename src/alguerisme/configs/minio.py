"""MinIO configuration models."""

from pydantic import BaseModel, Field, PrivateAttr, SecretStr

from alguerisme.utils.secrets import get_secret


class MinioConfig(BaseModel):
    """Configuration for MinIO object storage.

    Connection settings are configured in YAML.
    Credentials (access_key, secret_key) are loaded from secrets files.

    Secrets:
        minio_root_user: MinIO access key
        minio_root_password: MinIO secret key

    Attributes
    ----------
    endpoint : str
        MinIO server endpoint (host:port)
    bucket_name : str
        Bucket name for storing images
    secure : bool
        Use HTTPS instead of HTTP
    region : str
        Region name (optional, for S3 compatibility)

    """

    model_config = {"arbitrary_types_allowed": True}

    # Connection settings - configured in YAML
    endpoint: str = Field(
        default="minio:9000", description="MinIO server endpoint (host:port)"
    )
    bucket_name: str = Field(
        default="alguerisme-images", description="Bucket name for storing images"
    )
    secure: bool = Field(
        default=False, description="Use HTTPS connection (False for dev)"
    )
    region: str = Field(
        default="us-east-1", description="Region name for S3 compatibility"
    )

    # Private cached credentials
    _access_key: SecretStr | None = PrivateAttr(default=None)
    _secret_key: SecretStr | None = PrivateAttr(default=None)

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
