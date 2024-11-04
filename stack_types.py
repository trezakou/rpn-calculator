from dataclasses import dataclass
from typing import List
from uuid import UUID


@dataclass
class StackInfo:
    id: UUID
    content: List[float]
    created_at: str

    @classmethod
    def from_db_model(cls, stack_model) -> "StackInfo":
        return cls(
            id=stack_model.id,
            content=stack_model.content,
            created_at=stack_model.created_at.strftime("%a %b %d %H:%M:%S %Y"),
        )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "content": self.content,
            "created_at": self.created_at,
        }
