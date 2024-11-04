from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel


class Stackbase(SQLModel):
    content: List[float] = Field(default=[], sa_column=Column(JSON))


class Stack(Stackbase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class StackCreate(Stackbase):
    pass
