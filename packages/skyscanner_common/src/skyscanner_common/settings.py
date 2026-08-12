"""
Typed configuration objects read from the environment, so that no service ever holds a hard coded endpoint.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ----- CONSTS ----- #

ENV_FILE: str = ".env"
LIST_SEPARATOR: str = ","

# ----- CLASSES ----- #


class ServiceSettings(BaseSettings):
    """
    The settings every service shares, describing how it identifies itself and how verbose it is.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", case_sensitive=False)

    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    events_service_url: str = Field(default="http://localhost:8000", validation_alias="EVENTS_SERVICE_URL")
    storage_service_url: str = Field(default="http://localhost:8001", validation_alias="STORAGE_SERVICE_URL")
    notification_service_url: str = Field(default="http://localhost:8002", validation_alias="NOTIFICATION_SERVICE_URL")


class MongoSettings(BaseSettings):
    """
    Connection settings of the document store that keeps the events, the entities and the dynamic schema.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", case_sensitive=False)

    uri: str = Field(default="mongodb://localhost:27017", validation_alias="MONGO_URI")
    database: str = Field(default="skyscanner", validation_alias="MONGO_DATABASE")
    max_pool_size: int = Field(default=50, ge=1, validation_alias="MONGO_MAX_POOL_SIZE")
    server_selection_timeout_ms: int = Field(
        default=5000,
        ge=100,
        validation_alias="MONGO_SERVER_SELECTION_TIMEOUT_MS",
    )


class StorageSettings(BaseSettings):
    """
    Connection settings of the bucket that keeps every uploaded raw, parsed and additional file.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", case_sensitive=False)

    endpoint_url: str | None = Field(default=None, validation_alias="S3_ENDPOINT_URL")
    region: str = Field(default="us-east-1", validation_alias="S3_REGION")
    bucket: str = Field(default="skyscanner-artifacts", validation_alias="S3_BUCKET")
    access_key_id: str | None = Field(default=None, validation_alias="S3_ACCESS_KEY_ID")
    secret_access_key: str | None = Field(default=None, validation_alias="S3_SECRET_ACCESS_KEY")
    presigned_url_ttl_seconds: int = Field(default=3600, ge=60, validation_alias="S3_PRESIGNED_URL_TTL_SECONDS")
    multipart_threshold_bytes: int = Field(
        default=16 * 1024 * 1024,
        ge=1024,
        validation_alias="S3_MULTIPART_THRESHOLD_BYTES",
    )


class AuthSettings(BaseSettings):
    """
    Names of the headers the authenticating reverse proxy injects, plus the fallback used while it is absent.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", case_sensitive=False)

    user_header: str = Field(default="X-Auth-User", validation_alias="AUTH_USER_HEADER")
    email_header: str = Field(default="X-Auth-Email", validation_alias="AUTH_EMAIL_HEADER")
    roles_header: str = Field(default="X-Auth-Roles", validation_alias="AUTH_ROLES_HEADER")
    industries_header: str = Field(default="X-Auth-Industries", validation_alias="AUTH_INDUSTRIES_HEADER")
    allow_anonymous: bool = Field(default=True, validation_alias="AUTH_ALLOW_ANONYMOUS")
    anonymous_roles_raw: str = Field(default="admin", validation_alias="AUTH_ANONYMOUS_ROLES")

    @property
    def anonymous_roles(self) -> list[str]:
        """
        Split the configured fallback roles into a list.

        :return: The roles granted to a caller that arrived without identity headers.
        """
        return [role.strip() for role in self.anonymous_roles_raw.split(LIST_SEPARATOR) if role.strip()]


class CorsSettings(BaseSettings):
    """
    The browser origins the services accept, needed because the web client is served from its own container.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", case_sensitive=False)

    allow_origins_raw: str = Field(default="*", validation_alias="CORS_ALLOW_ORIGINS")

    @property
    def allow_origins(self) -> list[str]:
        """
        Split the configured origins into a list understood by the CORS middleware.

        :return: The allowed browser origins.
        """
        return [origin.strip() for origin in self.allow_origins_raw.split(LIST_SEPARATOR) if origin.strip()]


class MailSettings(BaseSettings):
    """
    Connection settings of the mail relay used to notify the users that follow an industry or an event.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", case_sensitive=False)

    host: str = Field(default="localhost", validation_alias="SMTP_HOST")
    port: int = Field(default=1025, ge=1, validation_alias="SMTP_PORT")
    username: str | None = Field(default=None, validation_alias="SMTP_USERNAME")
    password: str | None = Field(default=None, validation_alias="SMTP_PASSWORD")
    use_tls: bool = Field(default=False, validation_alias="SMTP_USE_TLS")
    sender: str = Field(default="skyscanner@example.com", validation_alias="MAIL_FROM")
    poll_interval_seconds: int = Field(default=30, ge=5, validation_alias="NOTIFICATION_POLL_INTERVAL_SECONDS")


# ----- FUNCTIONS ----- #


@lru_cache(maxsize=1)
def get_service_settings() -> ServiceSettings:
    """
    Build the shared service settings once and reuse them for the whole process life time.

    :return: The cached shared service settings.
    """
    return ServiceSettings()


@lru_cache(maxsize=1)
def get_mongo_settings() -> MongoSettings:
    """
    Build the mongo settings once and reuse them for the whole process life time.

    :return: The cached mongo settings.
    """
    return MongoSettings()


@lru_cache(maxsize=1)
def get_storage_settings() -> StorageSettings:
    """
    Build the object storage settings once and reuse them for the whole process life time.

    :return: The cached object storage settings.
    """
    return StorageSettings()


@lru_cache(maxsize=1)
def get_auth_settings() -> AuthSettings:
    """
    Build the identity header settings once and reuse them for the whole process life time.

    :return: The cached identity header settings.
    """
    return AuthSettings()


@lru_cache(maxsize=1)
def get_cors_settings() -> CorsSettings:
    """
    Build the CORS settings once and reuse them for the whole process life time.

    :return: The cached CORS settings.
    """
    return CorsSettings()


@lru_cache(maxsize=1)
def get_mail_settings() -> MailSettings:
    """
    Build the mail relay settings once and reuse them for the whole process life time.

    :return: The cached mail relay settings.
    """
    return MailSettings()
