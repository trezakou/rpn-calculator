from enum import Enum
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.db.models import Stack
from app.db.sessions import async_engine
from stack_types import StackInfo


class Operation(Enum):
    ADD = "add"
    MULTIPLY = "multiply"
    SUBTRACT = "subtract"
    DIVIDE = "divide"


class RPNCalculatorActivities:
    @staticmethod
    @activity.defn
    async def get_stack_from_db(stack_id: UUID) -> StackInfo:
        """Retrieve stack from database."""
        async with AsyncSession(async_engine) as session:
            statement = select(Stack).where(Stack.id == stack_id)
            result = await session.execute(statement)
            stack = result.scalar_one_or_none()

            if not stack:
                raise ApplicationError("Stack not found")

            return StackInfo.from_db_model(stack)

    @staticmethod
    @activity.defn
    async def validate_stack(content: List[float]) -> bool:
        """Validate that the stack contains valid numerical values."""
        if not isinstance(content, list):
            raise ApplicationError("Stack content should be a list")
        if not all(isinstance(x, (int, float)) for x in content):
            raise ApplicationError(
                "All elements in the stack should be float or integer"
            )
        return True  # Removed the minimum length check for initial creation

    @staticmethod
    @activity.defn
    async def perform_operation(content: List[float], op: str) -> List[float]:
        """Perform operation."""
        if len(content) < 2:
            raise ApplicationError("Insufficient elements in stack")

        content_copy = (
            content.copy()
        )  # Create a copy to avoid modifying the original
        b = content_copy.pop()
        a = content_copy.pop()

        match op:
            case Operation.ADD.value:
                content_copy.append(a + b)
            case Operation.SUBTRACT.value:
                content_copy.append(a - b)
            case Operation.MULTIPLY.value:
                content_copy.append(a * b)
            case Operation.DIVIDE.value:
                if b == 0:
                    raise ApplicationError("Cannot divide by 0")
                content_copy.append(a / b)
            case _:
                raise ApplicationError("Operation not implemented")

        return content_copy

    @staticmethod
    @activity.defn
    async def update_stack_in_db(
        stack_id: UUID, new_content: List[float]
    ) -> StackInfo:
        """Update stack content in database."""
        async with AsyncSession(async_engine) as session:
            statement = select(Stack).where(Stack.id == stack_id)
            result = await session.execute(statement)
            stack = result.scalar_one_or_none()

            if not stack:
                raise ApplicationError("Stack not found")

            stack.content = new_content
            session.add(stack)
            await session.commit()
            await session.refresh(stack)
            return StackInfo.from_db_model(stack)
