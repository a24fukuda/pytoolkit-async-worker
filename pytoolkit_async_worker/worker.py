"""
非同期ワーカー処理のためのモジュール。

複数のワーカーを使用してタスクを並列処理し、結果を効率的に収集する機能を提供する。
"""

import asyncio
from dataclasses import dataclass
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Coroutine,
    Generic,
    ParamSpec,
    TypeAlias,
    TypeVar,
)

from pytoolkit_rustlike import Err, Ok, Option, Result, Some

P = ParamSpec("P")
R = TypeVar("R")

TaskFunc = Callable[P, Awaitable[R]]


@dataclass(frozen=True)
class Task(Generic[P, R]):
    """
    実行するタスクを表すデータクラス。

    Attributes:
        func: 実行する非同期関数
        args: 関数の位置引数
        kwargs: 関数のキーワード引数
    """

    func: TaskFunc[P, R]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


@dataclass(frozen=True)
class TaskResult(Generic[R]):
    """
    タスクの実行結果を表すデータクラス。

    Attributes:
        args: 実行時の位置引数
        kwargs: 実行時のキーワード引数
        result: 実行結果
    """

    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    result: Result[Option[R]]


AsyncioTask = asyncio.Task[Any]
PendingTaskQueue = asyncio.Queue[Task[P, R]]
TaskResultQueue = asyncio.Queue[TaskResult[R]]


Worker: TypeAlias = Callable[
    [PendingTaskQueue[P, R], TaskResultQueue[R]], Coroutine[Any, Any, None]
]


async def worker(
    pending_task_queue: PendingTaskQueue[P, R],
    task_result_queue: TaskResultQueue[R],
) -> None:
    """
    タスクキューからタスクを取得し、実行結果を結果キューに送信するワーカー関数。

    Args:
        pending_task_queue: 実行待ちタスクのキュー
        task_result_queue: 実行結果のキュー
    """
    while not pending_task_queue.empty():
        task = await pending_task_queue.get()

        try:
            return_value = await task.func(*task.args, **task.kwargs)
            result = Ok[Option[R]](Some(return_value))
        except Exception as e:
            result = Err[Option[R]](e)

        task_result = TaskResult(args=task.args, kwargs=task.kwargs, result=result)
        await task_result_queue.put(task_result)
        pending_task_queue.task_done()


class WorkerManager(Generic[P, R]):
    """
    非同期ワーカーの管理を行うクラス。

    複数のワーカーを並列実行し、タスクの分散処理と結果の収集を行う。
    タスクキューを通じて効率的な負荷分散を実現する。
    """

    def __init__(
        self,
        worker: Worker[P, R],
        max_workers: int,
    ):
        """
        WorkerManagerを初期化する。

        Args:
            worker: ワーカー関数
            max_workers: 最大ワーカー数
        """
        self.worker = worker
        self.workers: list[AsyncioTask] = []
        self.max_workers = max_workers
        self.pending_task_queue = PendingTaskQueue[P, R]()
        self.task_result_queue = TaskResultQueue[R]()

    async def add_task(
        self,
        func: TaskFunc[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """
        タスクを実行キューに追加する。

        Args:
            func: 実行する非同期関数
            *args: 関数の位置引数
            **kwargs: 関数のキーワード引数
        """
        await self.pending_task_queue.put(
            Task[P, R](func=func, args=args, kwargs=kwargs)
        )

    async def execute(self) -> AsyncGenerator[TaskResult[R]]:
        """
        ワーカーを起動してタスクを実行し、結果を順次yield する。

        Yields:
            TaskResult[R]: 各タスクの実行結果
        """

        async with asyncio.TaskGroup() as tg:
            self.workers = [
                tg.create_task(
                    self.worker(
                        self.pending_task_queue,
                        self.task_result_queue,
                    )
                )
                for _ in range(self.max_workers)
            ]

            while True:
                is_all_workers_done = all([worker.done() for worker in self.workers])
                if is_all_workers_done and self.task_result_queue.empty():
                    break

                if is_all_workers_done:
                    try:
                        croutine = self.task_result_queue.get()
                        yield await asyncio.wait_for(croutine, 1.0)
                    except TimeoutError:
                        break

                yield await self.task_result_queue.get()
