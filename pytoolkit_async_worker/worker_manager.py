"""Worker manager for coordinating download operations."""

import asyncio
from typing import Any, AsyncGenerator, Generic

from .task import Task
from .worker import Worker

type AsyncioTask = asyncio.Task[Any]


class WorkerManager(Generic[Task]):
    """
    ダウンロード処理におけるワーカー管理を行うクラス。

    ワーカーの起動、監視、終了を管理し、タスクキューを通じて
    複数のワーカーに処理を分散する。
    """

    def __init__(
        self,
        worker: Worker[Task],
        max_workers: int,
        pending_task_queue: asyncio.Queue[Task],
    ):
        """
        WorkerManagerを初期化する。

        Args:
            client (Dropbox): Dropboxクライアント
            max_workers (int): 最大ワーカー数
        """
        self.worker = worker

        self.workers: list[AsyncioTask] = []
        self.max_workers = max_workers
        self.pending_task_queue = pending_task_queue
        self.completed_task_queue = asyncio.Queue[Task]()

    async def execute(self) -> AsyncGenerator[Task]:
        """
        エントリのリストを処理し、結果を返す。

        Args:
            entries (list[SyncEntry]): 処理するエントリのリスト

        Returns:
            list[bool]: 各タスクの成功/失敗結果
        """

        async with asyncio.TaskGroup() as tg:
            self.workers = [
                tg.create_task(
                    self.worker(
                        work_id,
                        self.pending_task_queue,
                        self.completed_task_queue,
                    )
                )
                for work_id in range(self.max_workers)
            ]

            while True:
                is_all_workers_done = all([worker.done() for worker in self.workers])
                if is_all_workers_done and self.completed_task_queue.empty():
                    break

                if is_all_workers_done:
                    try:
                        yield await asyncio.wait_for(
                            self.completed_task_queue.get(), 1.0
                        )
                    except TimeoutError:
                        break

                yield await self.completed_task_queue.get()
