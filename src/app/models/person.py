from typing import Any
from uuid import UUID

from sqlalchemy import (
    UUID as SA_UUID,
    ForeignKey,
    func,
    select,
)
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from .base import BaseModel, _TimepointsModelMixin

__all__ = (
    "PersonFilmWorkModel",
    "PersonModel",
    "PersonWithFilmsModel",
)


class PersonModel(MappedAsDataclass, _TimepointsModelMixin, BaseModel):
    __tablename__ = "person"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True)
    full_name: Mapped[str]


class PersonFilmWorkModel(MappedAsDataclass, BaseModel):
    __tablename__ = "person_film_work"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True)
    role: Mapped[str]
    film_work_id: Mapped[int] = mapped_column(ForeignKey("film_work.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"))
    person: Mapped[PersonModel] = relationship()


films_aggregated_subquery = (
    select(
        PersonFilmWorkModel.person_id,
        PersonFilmWorkModel.film_work_id,
        func.array_agg(func.distinct(PersonFilmWorkModel.role)).label("roles"),
    )
    .group_by(PersonFilmWorkModel.person_id, PersonFilmWorkModel.film_work_id)
    .subquery("films_aggregated")
)


class PersonWithFilmsModel(BaseModel):
    __table__ = (
        select(
            films_aggregated_subquery.c.person_id.label("id"),
            PersonModel.full_name,
            func.array_agg(
                func.json_build_object(
                    "id",
                    films_aggregated_subquery.c.film_work_id,
                    "roles",
                    films_aggregated_subquery.c.roles,
                )
            ).label("films"),
        )
        .select_from(films_aggregated_subquery)
        .join(
            PersonModel, films_aggregated_subquery.c.person_id == PersonModel.id
        )
        .group_by(films_aggregated_subquery.c.person_id, PersonModel.full_name)
        .subquery("person_with_films")
    )
    __mapper_args__ = {"primary_key": [__table__.c.id]}

    id: Mapped[UUID]
    full_name: Mapped[str]
    films: Mapped[list[dict[str, Any]]]
