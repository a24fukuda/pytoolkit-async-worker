"""Worker implementation for download operations."""

from asyncio import Queue
from typing import Any, Callable, Coroutine

from .logger import logger
from .task import Task

type WorkerId = int


Worker = Callable[[WorkerId, Queue[Task], Queue[Task]], Coroutine[Any, Any, None]]


async def worker(
    worker_id: WorkerId,
    pending_task_queue: Queue[Task],
    completed_task_queue: Queue[Task],
) -> None:
    logger.debug(f"Worker {worker_id} started")

    while not pending_task_queue.empty():
        task = await pending_task_queue.get()
        await task.execute()
        await completed_task_queue.put(task)
        pending_task_queue.task_done()

    logger.debug(f"Worker {worker_id} finished")
