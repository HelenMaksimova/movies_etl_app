from typing import Any, Generator, Iterable

from elasticsearch import helpers
from sqlalchemy import select
from sqlalchemy.exc import (
    OperationalError as SqlalchemyOperationalError,
    TimeoutError as SqlalchemyTimeoutError,
)
from sqlalchemy.orm import Session

from ...utils import ETLProcess, backoff
from ..models import GenreModel
from ..schemas import GenreWithDescriptionDC

__all__ = ("GenreETLProcess",)


class GenreETLProcess(ETLProcess[GenreModel, GenreWithDescriptionDC]):
    def _update_target_data(self, converted_data: list[dict[str, Any]]):
        actions = [
            {
                "_op_type": "update",
                "_index": "genres",
                "_id": doc["id"],
                "doc": doc,
                "doc_as_upsert": True,
            }
            for doc in converted_data
        ]
        success, failed = helpers.bulk(self.app.target.client, actions)
        self.app.logger.info(
            f"[{self.__class__.__name__}] Data was updated. Success: %s, failed: %s",
            success,
            failed,
        )

    @backoff(exceptions={SqlalchemyOperationalError, SqlalchemyTimeoutError})
    def _get_genres(
        self, session: Session, limit: int = 0, offset: int = 0
    ) -> Iterable[GenreModel]:
        query = select(GenreModel).order_by(GenreModel.id)
        if self.app.state:
            query = query.where(GenreModel.modified > self.app.state)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return session.scalars(query).all()

    def _get_updated_data(
        self, limit: int = 0, offset: int = 0
    ) -> Generator[Iterable[GenreModel], None, None]:
        with self.app.db.session() as session:
            film_works = self._get_genres(session, limit, offset)
            if film_works:
                yield film_works
