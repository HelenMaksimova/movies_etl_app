from typing import Any, Generator, Iterable
from uuid import UUID

from elasticsearch import helpers
from sqlalchemy import select
from sqlalchemy.exc import (
    OperationalError as SqlalchemyOperationalError,
    TimeoutError as SqlalchemyTimeoutError,
)
from sqlalchemy.orm import Session, joinedload

from ...utils import ETLProcess, backoff
from ..models import FilmWorkModel, PersonModel, PersonWithFilmsModel
from ..schemas import PersonWithFilmsDC

__all__ = (
    "PersonsFilmWorkETLProcess",
    "PersonsPersonETLProcess",
)


class _PersonsETLProcess(ETLProcess[PersonWithFilmsModel, PersonWithFilmsDC]):
    def _update_target_data(self, converted_data: list[dict[str, Any]]):
        actions = [
            {
                "_op_type": "update",
                "_index": "persons",
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
    def _get_updated_person_ids(
        self,
        session: Session,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[UUID]:
        raise NotImplementedError

    @backoff(exceptions={SqlalchemyOperationalError, SqlalchemyTimeoutError})
    def _get_persons_with_films_by_person_ids(
        self,
        session: Session,
        person_ids: list[UUID],
        limit: int = 0,
        offset: int = 0,
    ) -> Iterable[PersonWithFilmsModel]:
        query = (
            select(PersonWithFilmsModel)
            .where(PersonWithFilmsModel.id.in_(person_ids))
            .order_by(PersonWithFilmsModel.id)
        )
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return session.scalars(query).unique().all()

    def _get_updated_data(
        self, limit: int = 0, offset: int = 0
    ) -> Generator[Iterable[PersonWithFilmsModel], None, None]:
        with self.app.db.session() as session:
            updated_person_ids = self._get_updated_person_ids(
                session, limit, offset
            )
            if updated_person_ids:
                film_work_offset = 0
                while True:
                    film_works = self._get_persons_with_films_by_person_ids(
                        session,
                        updated_person_ids,
                        self.butch_size,
                        film_work_offset,
                    )
                    film_work_offset += self.butch_size

                    if film_works:
                        yield film_works
                    else:
                        break


class PersonsPersonETLProcess(_PersonsETLProcess):
    @backoff(exceptions={SqlalchemyOperationalError, SqlalchemyTimeoutError})
    def _get_updated_person_ids(
        self,
        session: Session,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[UUID]:
        query = select(PersonModel).order_by(PersonModel.id)
        if self.app.state:
            query = query.where(PersonModel.modified >= self.app.state)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        results = session.scalars(query).all()

        return [item.id for item in results]


class PersonsFilmWorkETLProcess(_PersonsETLProcess):
    @backoff(exceptions={SqlalchemyOperationalError, SqlalchemyTimeoutError})
    def _get_updated_person_ids(
        self,
        session: Session,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[UUID]:
        query = (
            select(FilmWorkModel)
            .options(joinedload(FilmWorkModel.persons))
            .distinct()
            .order_by(FilmWorkModel.id)
        )
        if self.app.state:
            query = query.where(FilmWorkModel.modified >= self.app.state)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        results = session.scalars(query).unique().all()
        person_ids = set()
        for item in results:
            person_ids.update((person.person_id for person in item.persons))

        return list(person_ids)
