from datetime import datetime, timezone
from logging import Logger
from sys import exit
from time import sleep
from typing import Any, Type, TypeVar, get_args

from pydantic import BaseModel

from .accessors import ConfigAccessor, ConnectAccessor
from .configs import ConfigDC
from .decorators import exceptions_handler
from .processes import ETLProcess

__all__ = ("ETLApplication",)


class ETLApplication[
    _Config,
    _DBConnectAccessor,
    _StorageConnectAccessor,
    _TargetConnectAccessor,
]:
    """Класс-приложение для работы с ETL процессами.
    Содержит в себе ссылки на классы-обработчики для работы с
    необходимыми сервисами, а также логику получения текущего
    состояния и запуска процессов"""

    _name: str | None = None
    _components_attrs: tuple[str] = ("db", "storage", "target")
    _processes_types: tuple[type[ETLProcess]] = tuple()

    def __init__(self, config: BaseModel, logger: Logger | None = None) -> None:
        self.db: _DBConnectAccessor | None = None
        self.storage: _StorageConnectAccessor | None = None
        self.target: _TargetConnectAccessor | None = None
        self.state: Any = None

        self.is_running: bool = False

        self._logger: Logger | None = logger
        self._connectors: list[ConnectAccessor] = []
        self._processes: list[ETLProcess] = []

        self._config: _Config | None = getattr(config, self.name, None)

        self._set_components(config)
        self._set_processes()

    @classmethod
    @property
    def name(cls) -> str:
        if cls._name:
            return cls._name

        raise ValueError(f"[{cls.__name__}] Name was not set")

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

    @property
    def connectors(self) -> list[ConnectAccessor]:
        return self._connectors

    @property
    def processes(self) -> list[ETLProcess]:
        return self._processes

    def _get_components_types(
        self,
    ) -> list[Type[ConfigAccessor | ConnectAccessor]]:
        """Метод получения классов-обработчиков из Generic"""
        return [
            base_type
            for base_type in get_args(self.__orig_bases__[-1])
            if not (
                isinstance(base_type, TypeVar)
                or issubclass(base_type, ConfigDC)
            )
        ]

    def _set_components(self, config: BaseModel) -> None:
        """Метод установки атрибутов класса-приложения, отвечающих за доступ
        к параметрам конфигурации и сторонним сервисам"""
        components_types = self._get_components_types()
        for component_type, attr in zip(
            components_types, self._components_attrs
        ):
            component = component_type(
                getattr(config, attr, None), self._logger
            )

            if issubclass(component_type, ConnectAccessor):
                self._connectors.append(component)

            setattr(self, attr, component)

    def _set_processes(self):
        """Метод инициализации ETL-процессов приложения"""
        for process_type in self._processes_types:
            self._processes.append(process_type(self, self.config.butch_size))

    def _set_start_state(self) -> None:
        """Метод установки состояния приложения перед
        началом цикла процессов"""
        if self.config.reload:
            state = None
            self.config.reload = False
        else:
            state = self.get_storage_state(self.config.state_key)

        if state:
            self.state = datetime.fromisoformat(state)

    def _set_finish_state(self, current_data: datetime) -> None:
        """Метод установки состояния приложения после
        успешного завершения цикла процессов"""
        self.set_storage_state(self.config.state_key, current_data.isoformat())

    @exceptions_handler()
    def _cycle(self) -> None:
        """Метод основного цикла приложения.
        Логика:
        - определяет и фиксирует время начала выполнения цикла
        - устанавливает текущее состояние перед запуском процессов
        - запускает процессы
        - если процессы завершились успешно, устанавливает новое текущее
          состояние, равное времени начала выполнения цикла
        Декорирован перехватчиком ошибок для обеспечения стабильной работы"""
        current_date = datetime.now(tz=timezone.utc)
        self._set_start_state()
        self.logger.info(
            f"[{self.__class__.__name__}] Start update cycle with current state: %s",
            self.state,
        )

        for process in self.processes:
            process.execute()

        self._set_finish_state(current_date)
        self.logger.info(
            f"[{self.__class__.__name__}] Finish update cycle. Set new state: %s",
            current_date,
        )

    def run(self) -> None:
        """Метод запуска приложения. Выполняет стартовое подключение к сервисам,
        запускает основной цикл приложения. В случае ручного прерывания работы
        приложения запускает метод остановки"""
        self.is_running = True

        for connector in self.connectors:
            if not connector.is_connected:
                connector.connect()

        try:
            while self.is_running:
                self._cycle()
                sleep(self.config.cycle_delay)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Метод для остановки работы приложения"""
        self.is_running = False

        for connector in self.connectors:
            connector.disconnect()

        exit(0)

    def get_storage_state(self, key: str) -> Any:
        """Метод получения состояния из хранилища"""
        state = self.storage.retrieve_state() or {}
        return state.get(key)

    def set_storage_state(self, key: str, value: Any) -> None:
        """Метод записи состояния в хранилище"""
        self.storage.save_state({key: value})
