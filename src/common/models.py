import datetime
import uuid
from typing import Optional
from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    __table_args__ = {"extend_existing": True}

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False
    )
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        # sa_column_kwargs helps auto-update the timestamp on the DB level
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow}
    )

