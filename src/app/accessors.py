from ..utils import (
    BaseElasticsearchConnectAccessor,
    BasePostgresConnectAccessor,
    BaseRedisConnectAccessor,
)

__all__ = (
    "ElasticsearchConnectAccessor",
    "PostgresConnectAccessor",
    "RedisConnectAccessor",
)


class PostgresConnectAccessor(BasePostgresConnectAccessor):
    pass


class RedisConnectAccessor(BaseRedisConnectAccessor):
    pass


class ElasticsearchConnectAccessor(BaseElasticsearchConnectAccessor):
    pass
