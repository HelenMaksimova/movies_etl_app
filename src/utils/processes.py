from typing import TYPE_CHECKING, Any, Generator, TypeVar, get_args

from elastic_transport import (
    ConnectionError as ElasticsearchConnectionError,
    ConnectionTimeout as ElasticsearchTimeoutError,
)
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase

from .decorators import backoff

if TYPE_CHECKING:
    from .app import ETLApplication

__all__ = ("ETLProcess",)


class ETLProcess[_DbModel: DeclarativeBase, _TargetSchema: BaseModel]:
    """Базовый класс ETL-процесса. Оперирует методами для получения,
    обработки и передачи данных из базы в целевой сервис.
    Для доступа к сервисам и логгеру использует объект ETL-приложения"""

    def __init__(
        self, app: "ETLApplication", butch_size: int | None = None
    ) -> None:
        self.app = app
        self.butch_size: int | None = butch_size
        self.is_executed: bool = True
        self._target_schema: type[_TargetSchema] | None = None
        self._set_target_schema()

    @property
    def target_schema(self) -> type[_TargetSchema]:
        """Класс-схема итогового формата данных для передачи в целевой сервис
        (предполагается использование pydentic схемы)"""
        if self._target_schema:
            return self._target_schema

        raise ValueError(
            f"[{self.__class__.__name__}] Target schema was not set"
        )

    def _set_target_schema(self):
        """Метод получения и установки класса-схемы из Generic"""
        for base_type in get_args(self.__orig_bases__[-1]):
            if not isinstance(base_type, TypeVar) and issubclass(
                base_type, BaseModel
            ):
                self._target_schema = base_type

    def _convert_data(self, updated_data: list[dict[str, Any]]):
        """Базовый метод конвертации данных в формат целевого сервиса"""
        results = [
            self.target_schema.model_validate(item).model_dump()
            for item in updated_data
        ]
        self.app.logger.debug(
            f"[{self.__class__.__name__}] Data for update: %s",
            results,
        )

        return results

    def _get_updated_data(
        self, limit: int = 0, offset: int = 0
    ) -> Generator[list[_DbModel], None, None]:
        """Метод получения данных из базы.
        Должен быть определён в наследниках класса"""
        raise NotImplementedError

    @backoff(
        exceptions={ElasticsearchConnectionError, ElasticsearchTimeoutError}
    )
    def _update_target_data(self, converted_data: list[dict[str, Any]]):
        """Метод обновления данных в целевом сервисе.
        Должен быть определён в наследниках класса"""
        raise NotImplementedError

    def _pipline(self, limit: int = 0, offset: int = 0) -> None:
        """Метод пайплайна процесса.
        Получает из базы, преобразует в нужный формат и
        обновляет данные в целевом сервисе"""
        updated_data = self._get_updated_data(limit, offset)
        # Так как updated_data - генератор, мы не можем просто проверить объект
        # через приведение типов, условие if updated_data всегда вернёт True.
        # Поэтому мы проверяем, была ли итерация по объекту через дополнительный флаг
        is_iterated = False

        for data in updated_data:
            is_iterated = True
            converted_data = self._convert_data(data)
            self._update_target_data(converted_data)

        if not is_iterated:
            self.is_executed = False

    def execute(self) -> None:
        """Основной метод процесса. Запускает пайплайн"""
        self.is_executed = True
        offset = 0

        while self.is_executed:
            self._pipline(self.butch_size, offset)
            offset += self.butch_size

        self.app.logger.info(f"[{self.__class__.__name__}] Data is up to date")
