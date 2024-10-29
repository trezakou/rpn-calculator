from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
from uuid import UUID, uuid4


class Stackbase(SQLModel):
    content: list[float] = Field(sa_column=Column(JSON))


class Stack(Stackbase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class StackCreate(Stackbase):
    ...
