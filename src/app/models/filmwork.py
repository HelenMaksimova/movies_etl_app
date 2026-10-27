from datetime import datetime
from uuid import UUID

from sqlalchemy import UUID as SA_UUID
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from .base import BaseModel, _TimepointsModelMixin
from .genre import GenreModel
from .person import PersonFilmWorkModel

__all__ = ("FilmWorkModel",)


class FilmWorkModel(MappedAsDataclass, _TimepointsModelMixin, BaseModel):
    __tablename__ = "film_work"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True)
    title: Mapped[str]
    type: Mapped[str]
    description: Mapped[str | None]
    creation_date: Mapped[datetime | None]
    rating: Mapped[float | None]
    persons: Mapped[list["PersonFilmWorkModel"]] = relationship()
    genres: Mapped[list["GenreModel"]] = relationship(
        secondary="genre_film_work"
    )
