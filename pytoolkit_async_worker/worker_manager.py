"""
非同期ワーカー処理のためのモジュール。

複数のワーカーを使用してタスクを並列処理し、結果を効率的に収集する機能を提供する。
"""

import asyncio
from typing import AsyncGenerator, Generic, TypeVar

from .counter import Counter
from .task import Task
from .worker import PendingTaskQueue, TaskResult, Worker, worker

T = TypeVar("T")
TaskResultQueue = asyncio.Queue[TaskResult[T]]


class WorkerManager(Generic[T]):
    """
    非同期ワーカーの管理を行うクラス。

    複数のワーカーを並列実行し、タスクの分散処理と結果の収集を行う。
    タスクキューを通じて効率的な負荷分散を実現する。
    """

    def __init__(
        self,
        max_workers: int,
        worker: Worker[T] = worker,
    ):
        """
        WorkerManagerを初期化する。

        Args:
            worker: ワーカー関数
            max_workers: 最大ワーカー数
        """
        self.worker = worker
        self.max_workers = max_workers
        self.pending_task_queue = PendingTaskQueue[T]()

    async def add_task(
        self,
        task: Task[T],
    ) -> None:
        await self.pending_task_queue.put(task)

    async def execute(self) -> AsyncGenerator[TaskResult[T]]:
        generators = [
            self.worker(self.pending_task_queue) for _ in range(self.max_workers)
        ]

        finished_workers = Counter(0)
        total_workers = len(generators)
        result_queue = TaskResultQueue[T]()

        def increment(value: int) -> int:
            return value + 1

        async def forward(generator: AsyncGenerator[TaskResult[T]]) -> None:
            nonlocal finished_workers
            async for result in generator:
                await result_queue.put(result)
            await finished_workers.update(increment)

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(forward(generator)) for generator in generators]

            while await finished_workers.get() < total_workers:
                try:
                    yield await asyncio.wait_for(result_queue.get(), timeout=1)

                except asyncio.TimeoutError:
                    continue

            # Drain remaining results from the queue
            while not result_queue.empty():
                try:
                    yield await asyncio.wait_for(result_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    break

            # ensure cleanup
            await asyncio.gather(*tasks)
