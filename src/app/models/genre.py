from uuid import UUID

from sqlalchemy import UUID as SA_UUID, ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from .base import BaseModel, _TimepointsModelMixin

__all__ = ("GenreFilmWorkModel", "GenreModel")


class GenreModel(MappedAsDataclass, _TimepointsModelMixin, BaseModel):
    __tablename__ = "genre"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)


class GenreFilmWorkModel(BaseModel):
    __tablename__ = "genre_film_work"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True)
    film_work_id: Mapped[int] = mapped_column(ForeignKey("film_work.id"))
    genre_id: Mapped[int] = mapped_column(ForeignKey("genre.id"))
