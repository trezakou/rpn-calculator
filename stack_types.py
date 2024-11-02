from dataclasses import dataclass
from typing import List
from uuid import UUID


@dataclass
class StackInfo:
    id: UUID
    content: List[float]

    @classmethod
    def from_db_model(cls, stack_model) -> "StackInfo":
        return cls(
            id=stack_model.id,
            content=stack_model.content,
        )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "content": self.content,
        }
