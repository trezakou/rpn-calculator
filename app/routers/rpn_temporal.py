import asyncio
from datetime import datetime
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, HTTPException
from temporalio.client import Client

from app.db.models import Stack, StackCreate
from app.db.sessions import AsyncSessionDep
from workflows import RPNCalculatorWorkflow

router = APIRouter(
    prefix="/rpn-temporal", tags=["RPN API Temporal implementation"]
)


# Create a Pydantic-compatible enum for the API
class OperationType(str, Enum):
    ADD = "add"
    MULTIPLY = "multiply"
    SUBTRACT = "subtract"
    DIVIDE = "divide"


def get_workflow_id(stack_id: UUID) -> str:
    """Standardize workflow ID creation."""
    return f"rpn-calculator-{stack_id}"


@router.post("/stack/long-running", response_model=Stack)
async def create_long_running_stack(
    stack: StackCreate,
    session: AsyncSessionDep,
):
    """Create a stack with a long-running workflow that waits for signals."""
    try:
        # Create stack in database first
        db_stack = Stack.model_validate(stack)
        session.add(db_stack)
        await session.commit()
        await session.refresh(db_stack)

        # Initialize Temporal client
        client = await Client.connect("localhost:7233")

        # Create workflow ID from stack ID
        workflow_id = get_workflow_id(db_stack.id)

        # Start the workflow in the background
        _ = await client.start_workflow(
            RPNCalculatorWorkflow.run,
            db_stack.id,
            id=workflow_id,
            task_queue="rpn-task-queue",
        )

        return db_stack
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stack/{stack_id}", response_model=Stack)
async def push_value(stack_id: UUID, new_value: float):
    client = await Client.connect("localhost:7233")
    workflow_id = get_workflow_id(stack_id)

    try:
        # Get initial handle and send signal
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(RPNCalculatorWorkflow.push_value, new_value)

        # Small delay to allow operation to complete
        await asyncio.sleep(0.1)

        # Get a fresh handle and query the updated state
        handle = client.get_workflow_handle(workflow_id)
        result = await handle.query(RPNCalculatorWorkflow.get_current_stack)
        return Stack(id=result.id, content=result.content)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Error processing request: {str(e)}",
        )


@router.post("/op/{op}/stack/{stack_id}", response_model=Stack)
async def apply_operation(stack_id: UUID, op: OperationType):
    client = await Client.connect("localhost:7233")
    workflow_id = get_workflow_id(stack_id)

    try:
        # Get initial handle and send signal
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(RPNCalculatorWorkflow.apply_operation, op.value)

        # Small delay to allow operation to complete
        await asyncio.sleep(0.1)

        # Get a fresh handle and query the updated state
        handle = client.get_workflow_handle(workflow_id)
        result = await handle.query(RPNCalculatorWorkflow.get_current_stack)
        return Stack(id=result.id, content=result.content)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Error processing request: {str(e)}.",
        )


@router.get("/stack/{stack_id}", response_model=Stack)
async def get_stack(stack_id: UUID):
    client = await Client.connect("localhost:7233")
    workflow_id = get_workflow_id(stack_id)

    try:
        handle = client.get_workflow_handle(workflow_id)
        result = await handle.query(RPNCalculatorWorkflow.get_current_stack)
        return Stack(
            id=result.id,
            content=result.content,
            created_at=datetime.strptime(
                result.created_at, "%a %b %d %H:%M:%S %Y"
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Error processing request: {str(e)}.",
        )


@router.post("/stack/{stack_id}/exit")
async def exit_workflow(stack_id: UUID):
    """Signal the workflow to exit."""
    client = await Client.connect("localhost:7233")
    workflow_id = get_workflow_id(stack_id)

    try:
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(RPNCalculatorWorkflow.exit_workflow)
        result = await handle.query(RPNCalculatorWorkflow.get_current_stack)
        return Stack(id=result.id, content=result.content)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Error processing request: {str(e)}.",
        )
