from ..utils import ETLApplication, ETLApplicationConfigDC
from .accessors import (
    ElasticsearchConnectAccessor,
    PostgresConnectAccessor,
    RedisConnectAccessor,
)
from .processes import (
    GenreETLProcess,
    MoviesFilmWorkETLProcess,
    MoviesGenreETLProcess,
    MoviesPersonETLProcess,
    PersonsFilmWorkETLProcess,
    PersonsPersonETLProcess,
)

__all__ = ("PostgresToEsApplication",)


class PostgresToEsApplication(
    ETLApplication[
        ETLApplicationConfigDC,
        PostgresConnectAccessor,
        RedisConnectAccessor,
        ElasticsearchConnectAccessor,
    ]
):
    _name = "etl_app"
    _processes_types = (
        MoviesPersonETLProcess,
        MoviesGenreETLProcess,
        MoviesFilmWorkETLProcess,
        PersonsPersonETLProcess,
        PersonsFilmWorkETLProcess,
        GenreETLProcess,
    )
