from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = (
    "AppConfigDC",
    "ConfigDC",
    "ConnectConfigDC",
    "ETLApplicationConfigDC",
    "ElasticsearchConfigDC",
    "PostgresConfigDC",
    "RedisConfigDC",
)


class ConfigDC(BaseModel):
    pass


class ETLApplicationConfigDC(ConfigDC):
    cycle_delay: int = Field(300, alias="CYCLE_DELAY")
    state_key: str = Field("updated", alias="STATE_KEY")
    butch_size: int = Field(100, alias="BUTCH_SIZE")
    reload: bool = Field(False, alias="RELOAD")


class ConnectConfigDC(ConfigDC):
    host: str = Field(alias="HOST")
    port: int = Field(alias="PORT")
    connect_backoff_base: float = Field(0.5, alias="CONNECT_BACKOFF_BASE")
    connect_backoff_cap: float = Field(4.0, alias="CONNECT_BACKOFF_CAP")
    connect_failures_cap: int = Field(5, alias="CONNECT_FAILURES_CAP")


class PostgresConfigDC(ConnectConfigDC):
    database: str = Field("postgres", alias="DATABASE")
    drivername: str = Field("postgresql+psycopg", alias="DRIVERNAME")
    port: int = Field(5432, alias="PORT")
    username: str | None = Field(None, alias="USERNAME")
    password: str | None = Field(None, alias="PASSWORD")
    pool_recycle: int = Field(3600, alias="POOL_RECYCLE")
    timeout: float = Field(30.0, alias="TIMEOUT")
    statement_timeout: int = Field(0, alias="STATEMENT_TIMEOUT")
    search_path: str = Field("public", alias="SEARCH_PATH")


class RedisConfigDC(ConnectConfigDC):
    port: int = Field(6379, alias="PORT")
    password: str | None = Field(None, alias="PASSWORD")
    db: int = Field(0, alias="DB")
    decode_responses: bool = Field(True, alias="DECODE_RESPONSES")
    state_key: str = Field("app", alias="STATE_KEY")


class ElasticsearchConfigDC(ConnectConfigDC):
    pass


class AppConfigDC(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_nested_delimiter="__",
        env_file=".env.app.local",
    )
    etl_app: ETLApplicationConfigDC = Field(alias="ETL_APP")
    db: PostgresConfigDC = Field(alias="DB")
    storage: RedisConfigDC = Field(alias="STORAGE")
    target: ElasticsearchConfigDC = Field(alias="TARGET")
    logger_name: str = Field("etl_app", alias="LOGGER_NAME")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
