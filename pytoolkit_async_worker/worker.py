"""
非同期ワーカー処理のためのモジュール。

複数のワーカーを使用してタスクを並列処理し、結果を効率的に収集する機能を提供する。
"""

import asyncio
from typing import AsyncGenerator, Callable, TypeVar

from pytoolkit_rustlike import Err, Ok, Option, as_option

from .task import Task, TaskResult

T = TypeVar("T")
PendingTaskQueue = asyncio.Queue[Task[T]]
Worker = Callable[[PendingTaskQueue[T]], AsyncGenerator[TaskResult[T]]]


async def worker(
    pending_task_queue: PendingTaskQueue[T],
) -> AsyncGenerator[TaskResult[T]]:
    while not pending_task_queue.empty():
        try:
            task = await asyncio.wait_for(pending_task_queue.get(), timeout=1)

        except asyncio.TimeoutError:
            continue

        try:
            return_value = await task.execute()
            result = Ok[Option[T]](as_option(return_value))

        except Exception as e:
            result = Err[Option[T]](e)

        yield TaskResult(task=task, result=result)
        pending_task_queue.task_done()
