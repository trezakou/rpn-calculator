from copy import deepcopy
from enum import Enum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.db.models import Stack, StackCreate
from app.db.sessions import SessionDep

router = APIRouter(prefix="/rpn", tags=["RPN API"])


class Calculator:
    """Reverse polish notation operations handler."""

    class OpEnum(Enum):
        """All available operations."""

        add = "add"
        multiply = "multiply"
        substract = "substract"
        divide = "divide"

    def __init__(self, content: list[float]):
        self.content: list[float] = content
        if not isinstance(self.content, list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stack content should be a list",
            )
        if not all(isinstance(x, (int, float)) for x in self.content):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="All elements in the stack should be float or integer",
            )
        if len(self.content) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="stack should contain at least twos elements",
            )

    def apply_operand(self, op: OpEnum) -> list:
        b = self.content.pop()
        a = self.content.pop()
        match op:
            case self.OpEnum.add:
                self.content.append(a + b)
            case self.OpEnum.substract:
                self.content.append(a - b)
            case self.OpEnum.multiply:
                self.content.append(a * b)
            case self.OpEnum.divide:
                if not b:
                    raise HTTPException(
                        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                        detail="Cannot divide by 0",
                    )
                self.content.append(a / b)
            case _:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Operation not implemented",
                )
        return self.content


@router.get("/op")
def get_all_available_operands():
    return list(Calculator.OpEnum._member_map_.values())


@router.post("/stack", response_model=Stack, summary="Create a new stack")
def create_stack(stack: StackCreate, session: SessionDep):
    db_stack = Stack.model_validate(stack)
    session.add(db_stack)
    session.commit()
    session.refresh(db_stack)
    return db_stack


@router.get(
    "/stack", response_model=list[Stack], summary="List the available stacks"
)
def read_stacks(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    stacks = session.exec(select(Stack).offset(offset).limit(limit)).all()
    return stacks


@router.delete("/stack/{stack_id}", summary="Delete a stack")
def delete_stack(session: SessionDep, stack_id: UUID):
    stack = session.get(Stack, stack_id)
    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")
    session.delete(stack)
    session.commit()
    return {"ok": True}


@router.post(
    "/stack/{stack_id}",
    response_model=Stack,
    summary="Push a new value to a stack",
)
def update_stack(session: SessionDep, stack_id: UUID, new_value: float):
    stack_db = session.get(Stack, stack_id)
    if not stack_db:
        raise HTTPException(status_code=404, detail="Stack not found")
    stack_db.content = stack_db.content + [new_value]
    session.add(stack_db)
    session.commit()
    session.refresh(stack_db)
    return stack_db


@router.get("/stack/{stack_id}", response_model=Stack, summary="Get a stack")
def get_stack(session: SessionDep, stack_id: UUID):
    stack_db = session.get(Stack, stack_id)
    if not stack_db:
        raise HTTPException(status_code=404, detail="Stack not found")
    return stack_db


@router.post(
    "/op/{op}/stack/{stack_id}",
    response_model=Stack,
    summary="Apply an operand to a stack",
)
def apply_operand_to_stack(
    session: SessionDep, stack_id: UUID, op: Calculator.OpEnum
):
    stack_db = session.get(Stack, stack_id)
    if not stack_db:
        raise HTTPException(status_code=404, detail="Stack not found")
    stack_db.content = Calculator(deepcopy(stack_db.content)).apply_operand(
        op=op
    )
    session.add(stack_db)
    session.commit()
    session.refresh(stack_db)
    return stack_db
