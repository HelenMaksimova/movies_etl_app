from logging import Logger
from time import sleep
from typing import Any, TypeVar, Awaitable

from elasticsearch import Elasticsearch
from redis import Redis
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, close_all_sessions, sessionmaker

from .configs import (
    ConnectConfigDC,
    ElasticsearchConfigDC,
    PostgresConfigDC,
    RedisConfigDC,
)

__all__ = (
    "BaseElasticsearchConnectAccessor",
    "BasePostgresConnectAccessor",
    "BaseRedisConnectAccessor",
    "ConfigAccessor",
    "ConnectAccessor",
)

_ConnectConfig = TypeVar("_ConnectConfig", bound=ConnectConfigDC)


class ConfigAccessor[_Config]:
    """Класс-обработчик с установкой конфига и логгера"""

    _name: str | None = None

    def __init__(
        self, config: _Config | None, logger: Logger | None = None
    ) -> None:
        self._config: _Config | None = config
        self._logger = logger

    @property
    def config(self) -> _Config:
        if self._config:
            return self._config

        raise ValueError(f"[{self.__class__.__name__}] Config was not set")

    @property
    def logger(self) -> Logger:
        if self._logger:
            return self._logger

        raise ValueError(f"[{self.__class__.__name__}] Logger was not set")

    @classmethod
    @property
    def name(cls) -> str:
        if cls._name:
            return cls._name

        raise ValueError(f"[{cls.__name__}] Name was not set")


class ConnectAccessor(ConfigAccessor[_ConnectConfig]):
    """Класс-обработчик для сервисов, требующих установки соединения.
    Реализует backoff при первичной установке соединения"""

    def __init__(self, config: _ConnectConfig, *args, **kwargs) -> None:
        super().__init__(config, *args, **kwargs)
        self.is_connected: bool = False

    def _connect(self) -> None:
        raise NotImplementedError

    def _disconnect(self) -> None:
        raise NotImplementedError

    def connect(self) -> None:
        backoff = self.config.connect_backoff_base
        failures = 0
        while (
            not self.is_connected
            and failures < self.config.connect_failures_cap
        ):
            try:
                self._connect()
                self.is_connected = True

            except Exception as err:
                failures += 1
                self.logger.warning(
                    f"[{self.__class__.__name__}] Connection was failed with error: %s."
                    f" Backoff for next connection: %s",
                    err,
                    backoff,
                )

                sleep(backoff)
                if backoff < self.config.connect_backoff_cap:
                    backoff = self.config.connect_backoff_base * 2**failures

        if self.is_connected:
            self.logger.info(
                f"[{self.__class__.__name__}] Service connected on %s:%s",
                self.config.host,
                self.config.port,
            )
        else:
            self.logger.error(
                f"[{self.__class__.__name__}] Service wasn't connected on %s:%s",
                self.config.host,
                self.config.port,
            )

    def disconnect(self) -> None:
        self._disconnect()
        self.is_connected = False
        self.logger.info(f"[{self.__class__.__name__}] Service disconnected")


class BasePostgresConnectAccessor(ConnectAccessor[PostgresConfigDC]):
    _name = "postgres"

    def __init__(self, config: PostgresConfigDC, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self._engine: Engine | None = None
        self._session: sessionmaker[Session] | None = None

    @property
    def engine(self) -> Engine:
        if self._engine:
            return self._engine

        raise ValueError(f"[{self.__class__.__name__}] Engine was not set")

    @property
    def session(self) -> sessionmaker[Session]:
        if self._session:
            return self._session

        raise ValueError(f"[{self.__class__.__name__}] Session was not set")

    def _create_engine(self) -> Engine:
        connect_args: dict[str, Any] = {
            "connect_timeout": self.config.timeout,
        }
        if "asyncpg" in self.config.drivername:
            connect_args["server_settings"] = {
                "search_path": self.config.search_path,
                "statement_timeout": str(self.config.statement_timeout),
            }
        elif "psycopg" in self.config.drivername:
            connect_args["options"] = " ".join(
                [
                    f"-c search_path={self.config.search_path}",
                    f"-c statement_timeout={self.config.statement_timeout}",
                ]
            )
        else:
            self.logger.warning(
                f"[{self.__class__.__name__}] Unknown driver for Postgres: %s, connect_args was not set",
                self.config.drivername,
            )

        return create_engine(
            URL.create(
                drivername=self.config.drivername,
                host=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                database=self.config.database,
            ),
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=True,
            connect_args=connect_args,
        )

    def _create_session(self) -> sessionmaker[Session]:
        return sessionmaker(self.engine)

    def _connect(self) -> None:
        self._engine = self._create_engine()
        self._session = self._create_session()

        # Проверяем соединение с базой:
        with self.engine.connect() as conn:
            conn.close()

    def _disconnect(self) -> None:
        close_all_sessions()
        self.is_connected = False
        self._engine = None
        self._session = None


class BaseRedisConnectAccessor(ConnectAccessor[RedisConfigDC]):
    _name = "redis"

    def __init__(self, config: RedisConfigDC, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        if self._client:
            return self._client

        raise ValueError(f"[{self.__class__.__name__}] Client was not set")

    def _create_client(self) -> Redis:
        return Redis(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password,
            db=self.config.db,
            decode_responses=self.config.decode_responses,
        )

    def _connect(self) -> None:
        self._client = self._create_client()
        self.client.ping()

    def _disconnect(self) -> None:
        self.client.close()
        self.is_connected = False
        self._client = None

    def save_state(self, state: dict[str, str | bytes]) -> None:
        for key, value in state.items():
            self.client.hset(self.config.state_key, key, value)

    def retrieve_state(self) -> Awaitable[dict] | dict:
        return self.client.hgetall(self.config.state_key)


class BaseElasticsearchConnectAccessor(ConnectAccessor[ElasticsearchConfigDC]):
    _name = "elastic"

    def __init__(self, config: ElasticsearchConfigDC, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self._client: Elasticsearch | None = None

    @property
    def client(self) -> Elasticsearch | None:
        if self._client:
            return self._client

        raise ValueError(f"[{self.__class__.__name__}] Client was not set")

    def _create_client(self) -> Elasticsearch:
        return Elasticsearch(f"http://{self.config.host}:{self.config.port}")

    def _connect(self) -> None:
        self._client = self._create_client()
        self.client.info()

    def _disconnect(self) -> None:
        self.client.close()
        self.is_connected = False
        self._client = None
