import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activities import RPNCalculatorActivities
from workflows import RPNCalculatorWorkflow


async def main() -> None:
    client: Client = await Client.connect(
        "localhost:7233", namespace="default"
    )
    task_queue: str = "rpn-task-queue"
    # Run the worker
    worker: Worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[RPNCalculatorWorkflow],
        activities=[
            RPNCalculatorActivities.validate_stack,
            RPNCalculatorActivities.perform_operation,
            RPNCalculatorActivities.get_stack_from_db,
            RPNCalculatorActivities.update_stack_in_db,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
