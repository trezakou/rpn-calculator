from datetime import timedelta
from typing import List, Optional
from uuid import UUID

from temporalio import workflow
from temporalio.exceptions import ApplicationError

from stack_types import StackInfo

with workflow.unsafe.imports_passed_through():
    from activities import RPNCalculatorActivities


@workflow.defn
class RPNCalculatorWorkflow:
    def __init__(self) -> None:
        self._stack_id: Optional[UUID] = None
        self._stack_content: List[float] = []
        self._exit_signal_received = False

    @workflow.run
    async def run(self, stack_id: UUID) -> StackInfo:
        """Initialize the workflow with a stack ID and wait for exit signal."""
        self._stack_id = stack_id

        # Initial fetch of stack
        initial_stack = await workflow.execute_activity(
            RPNCalculatorActivities.get_stack_from_db,
            stack_id,
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Store content locally
        self._stack_content = initial_stack.content

        await workflow.execute_activity(
            RPNCalculatorActivities.validate_stack,
            self._stack_content,
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Wait for exit signal
        while not self._exit_signal_received:
            try:
                await workflow.wait_condition(
                    lambda: self._exit_signal_received,
                    timeout=timedelta(days=365),  # Long timeout
                )
            except workflow.TimeoutError:
                # Timeout occurred, continue waiting
                continue

        # Return final state
        return StackInfo(id=self._stack_id, content=self._stack_content)

    @workflow.query
    def get_current_stack(self) -> StackInfo:
        """Query current stack state from workflow memory."""
        if not self._stack_id:
            raise ApplicationError("Stack not initialized")
        return StackInfo(id=self._stack_id, content=self._stack_content)

    @workflow.signal
    async def push_value(self, value: float) -> None:
        """Push a new value onto the stack."""
        if not self._stack_id:
            raise ApplicationError("Stack not initialized")

        # Update local content first
        new_content = self._stack_content + [value]

        # Validate new content
        await workflow.execute_activity(
            RPNCalculatorActivities.validate_stack,
            new_content,
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Update in database
        stack_info = await workflow.execute_activity(
            RPNCalculatorActivities.update_stack_in_db,
            args=[self._stack_id, new_content],
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Update local state after successful database update
        self._stack_content = stack_info.content

    @workflow.signal
    async def apply_operation(self, op: str) -> None:
        """Apply an operation to the stack."""
        if not self._stack_id:
            raise ApplicationError("Stack not initialized")

        # Perform operation on local content
        new_content = await workflow.execute_activity(
            RPNCalculatorActivities.perform_operation,
            args=[self._stack_content, op],
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Update in database
        stack_info = await workflow.execute_activity(
            RPNCalculatorActivities.update_stack_in_db,
            args=[self._stack_id, new_content],
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Update local state after successful database update
        self._stack_content = stack_info.content

    @workflow.signal
    async def exit_workflow(self) -> None:
        """Signal to exit the workflow."""
        self._exit_signal_received = True
