from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = (
    "FilmWorkDC",
    "GenreDC",
    "PersonDC",
    "PersonFilmWorkDC",
    "PersonWithFilmsDC",
)


class GenreDC(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: UUID
    name: str


class GenreWithDescriptionDC(GenreDC):
    description: str | None = None


class _PersonFilmDC(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: UUID
    roles: list[str] = Field(default_factory=list)


class PersonDC(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: UUID
    name: str = Field(alias="full_name")


class PersonWithFilmsDC(PersonDC):
    films: list[_PersonFilmDC] = Field(default_factory=list)


class PersonFilmWorkDC(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    role: str
    id: UUID | None = None
    name: str | None = None
    person: PersonDC = Field(exclude=True)

    @model_validator(mode="after")
    def set_derived_fields(self):
        self.id = self.person.id
        self.name = self.person.name

        return self


class FilmWorkDC(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    imdb_rating: float | None = Field(alias="rating")
    genres: list[GenreDC] = Field(default_factory=list)
    actors: list[PersonDC] = Field(default_factory=list)
    writers: list[PersonDC] = Field(default_factory=list)
    directors: list[PersonDC] = Field(default_factory=list)
    genres_names: list[str] = Field(default_factory=list)
    actors_names: list[str] = Field(default_factory=list)
    writers_names: list[str] = Field(default_factory=list)
    directors_names: list[str] = Field(default_factory=list)
    persons: list[PersonFilmWorkDC] = Field(exclude=True, default_factory=list)

    @model_validator(mode="after")
    def set_derived_fields(self):
        persons_map = {
            "actor": (self.actors, self.actors_names),
            "director": (self.directors, self.directors_names),
            "writer": (self.writers, self.writers_names),
        }

        for genre in self.genres:
            self.genres_names.append(genre.name)

        for person in self.persons:
            if person_fields := persons_map.get(person.role):
                persons, persons_names = person_fields
                persons.append(person.person)
                persons_names.append(person.name)

        return self
