from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    pass


class _TimepointsModelMixin:
    created: Mapped[datetime] = mapped_column(server_default=func.now())
    modified: Mapped[datetime] = mapped_column(
        server_onupdate=func.now(), index=True
    )
