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
from ..models import (
    FilmWorkModel,
    GenreFilmWorkModel,
    GenreModel,
    PersonFilmWorkModel,
    PersonModel,
)
from ..schemas import FilmWorkDC

__all__ = (
    "MoviesFilmWorkETLProcess",
    "MoviesGenreETLProcess",
    "MoviesPersonETLProcess",
)


class _MoviesETLProcess(ETLProcess[FilmWorkModel, FilmWorkDC]):
    def _update_target_data(self, converted_data: list[dict[str, Any]]):
        actions = [
            {
                "_op_type": "update",
                "_index": "movies",
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


class MoviesPersonETLProcess(_MoviesETLProcess):
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

    @backoff(exceptions={SqlalchemyOperationalError, SqlalchemyTimeoutError})
    def _get_film_works_by_person_ids(
        self,
        session: Session,
        person_ids: list[UUID],
        limit: int = 0,
        offset: int = 0,
    ) -> Iterable[FilmWorkModel]:
        query = (
            select(FilmWorkModel)
            .join(PersonFilmWorkModel)
            .options(
                joinedload(FilmWorkModel.persons),
                joinedload(FilmWorkModel.genres),
            )
            .where(PersonFilmWorkModel.person_id.in_(person_ids))
            .distinct()
            .order_by(FilmWorkModel.id)
        )
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return session.scalars(query).unique().all()

    def _get_updated_data(
        self, limit: int = 0, offset: int = 0
    ) -> Generator[Iterable[FilmWorkModel], None, None]:
        with self.app.db.session() as session:
            updated_person_ids = self._get_updated_person_ids(
                session, limit, offset
            )
            if updated_person_ids:
                film_work_offset = 0
                while True:
                    film_works = self._get_film_works_by_person_ids(
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


class MoviesGenreETLProcess(_MoviesETLProcess):
    @backoff(exceptions={SqlalchemyOperationalError, SqlalchemyTimeoutError})
    def _get_updated_genre_ids(
        self,
        session: Session,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[UUID]:
        query = select(GenreModel).order_by(GenreModel.id)
        if self.app.state:
            query = query.where(GenreModel.modified >= self.app.state)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        results = session.scalars(query).all()

        return [item.id for item in results]

    @backoff(exceptions={SqlalchemyOperationalError, SqlalchemyTimeoutError})
    def _get_film_works_by_genre_ids(
        self,
        session: Session,
        genre_ids: list[UUID],
        limit: int = 0,
        offset: int = 0,
    ) -> Iterable[FilmWorkModel]:
        query = (
            select(FilmWorkModel)
            .join(GenreFilmWorkModel)
            .options(
                joinedload(FilmWorkModel.persons),
                joinedload(FilmWorkModel.genres),
            )
            .where(GenreFilmWorkModel.genre_id.in_(genre_ids))
            .distinct()
            .order_by(FilmWorkModel.id)
        )
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return session.scalars(query).unique().all()

    def _get_updated_data(
        self, limit: int = 0, offset: int = 0
    ) -> Generator[Iterable[FilmWorkModel], None, None]:
        with self.app.db.session() as session:
            updated_genre_ids = self._get_updated_genre_ids(
                session, limit, offset
            )
            if updated_genre_ids:
                film_work_offset = 0
                while True:
                    film_works = self._get_film_works_by_genre_ids(
                        session,
                        updated_genre_ids,
                        self.butch_size,
                        film_work_offset,
                    )
                    film_work_offset += self.butch_size

                    if film_works:
                        yield film_works
                    else:
                        break


class MoviesFilmWorkETLProcess(_MoviesETLProcess):
    @backoff(exceptions={SqlalchemyOperationalError, SqlalchemyTimeoutError})
    def _get_film_works(
        self, session: Session, limit: int = 0, offset: int = 0
    ) -> Iterable[FilmWorkModel]:
        query = (
            select(FilmWorkModel)
            .options(
                joinedload(FilmWorkModel.persons),
                joinedload(FilmWorkModel.genres),
            )
            .distinct()
            .order_by(FilmWorkModel.id)
        )
        if self.app.state:
            query = query.where(FilmWorkModel.modified > self.app.state)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return session.scalars(query).unique().all()

    def _get_updated_data(
        self, limit: int = 0, offset: int = 0
    ) -> Generator[Iterable[FilmWorkModel], None, None]:
        with self.app.db.session() as session:
            film_works = self._get_film_works(session, limit, offset)
            if film_works:
                yield film_works
