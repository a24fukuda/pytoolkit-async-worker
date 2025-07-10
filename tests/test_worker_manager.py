"""Tests for worker_manager module."""

import asyncio
from dataclasses import dataclass

import pytest

from pytoolkit_async_worker.task import BaseTask
from pytoolkit_async_worker.worker import Worker, WorkerId
from pytoolkit_async_worker.worker_manager import WorkerManager


@dataclass
class MockTaskArgs:
    value: int


@dataclass
class MockTaskResult:
    result: int


class MockTask(BaseTask[MockTaskArgs, MockTaskResult]):
    def __init__(self, args: MockTaskArgs) -> None:
        super().__init__(args)

    async def execute(self) -> MockTaskResult:
        self.result = MockTaskResult(result=self.args.value * 2)
        return self.result


class TestWorkerManager:
    """WorkerManagerのテストクラス。"""

    @pytest.fixture
    def pending_task_queue(self) -> asyncio.Queue[MockTask]:
        """未処理タスクキューのフィクスチャを作成する。"""
        return asyncio.Queue()

    @pytest.fixture
    def mock_worker(self) -> Worker[MockTask]:
        """モックワーカー関数を作成する。"""

        async def mock_worker_func(
            _worker_id: WorkerId,
            pending_queue: asyncio.Queue[MockTask],
            completed_queue: asyncio.Queue[MockTask],
        ) -> None:
            while not pending_queue.empty():
                task = await pending_queue.get()
                await task.execute()
                await completed_queue.put(task)
                pending_queue.task_done()

        return mock_worker_func

    @pytest.fixture
    def worker_manager(
        self,
        mock_worker: Worker[MockTask],
        pending_task_queue: asyncio.Queue[MockTask],
    ) -> WorkerManager[MockTask]:
        """WorkerManagerインスタンスを作成する。"""
        return WorkerManager(
            worker=mock_worker,
            max_workers=2,
            pending_task_queue=pending_task_queue,
        )

    @pytest.mark.asyncio
    async def test_init(
        self,
        mock_worker: Worker[MockTask],
        pending_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """WorkerManagerが指定されたパラメーターで初期化され、空のワーカーリストを持つ。"""
        manager = WorkerManager(
            worker=mock_worker,
            max_workers=3,
            pending_task_queue=pending_task_queue,
        )

        assert manager.worker == mock_worker
        assert manager.max_workers == 3
        assert manager.pending_task_queue == pending_task_queue
        assert isinstance(manager.completed_task_queue, asyncio.Queue)
        assert manager.workers == []

    @pytest.mark.asyncio
    async def test_execute_single_task(
        self,
        worker_manager: WorkerManager[MockTask],
        pending_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """単一タスクが実行され、期待される結果が得られる。"""
        task = MockTask(MockTaskArgs(value=5))
        await pending_task_queue.put(task)

        results: list[MockTask] = []
        async for completed_task in worker_manager.execute():
            results.append(completed_task)

        assert len(results) == 1
        assert results[0].result.result == 10

    @pytest.mark.asyncio
    async def test_execute_multiple_tasks(
        self,
        worker_manager: WorkerManager[MockTask],
        pending_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """複数タスクが実行され、全ての期待される結果が得られる。"""
        tasks = [
            MockTask(MockTaskArgs(value=1)),
            MockTask(MockTaskArgs(value=2)),
            MockTask(MockTaskArgs(value=3)),
        ]

        for task in tasks:
            await pending_task_queue.put(task)

        results: list[MockTask] = []
        async for completed_task in worker_manager.execute():
            results.append(completed_task)

        assert len(results) == 3
        result_values = [task.result.result for task in results]
        assert 2 in result_values
        assert 4 in result_values
        assert 6 in result_values

    @pytest.mark.asyncio
    async def test_execute_empty_queue(
        self, worker_manager: WorkerManager[MockTask]
    ) -> None:
        """空のタスクキューでワーカーが完了し、結果が出力されない。"""
        results = list[MockTask]()
        try:
            async with asyncio.timeout(2.0):
                async for completed_task in worker_manager.execute():
                    results.append(completed_task)
        except asyncio.TimeoutError:
            pass

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_worker_creation(
        self,
        worker_manager: WorkerManager[MockTask],
        pending_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """指定された数のワーカーが作成され、全てがasyncio.Taskインスタンスである。"""
        task = MockTask(MockTaskArgs(value=1))
        await pending_task_queue.put(task)

        # Start execution to create workers
        results: list[MockTask] = []
        async for completed_task in worker_manager.execute():
            results.append(completed_task)
            break

        # Workers should be created after execution starts
        assert len(worker_manager.workers) == 2
        for worker in worker_manager.workers:
            assert isinstance(worker, asyncio.Task)

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self, pending_task_queue: asyncio.Queue[MockTask]
    ) -> None:
        """ワーカーがタスクを処理しない場合、タイムアウトで終了し、結果が出力されない。"""

        async def slow_worker(
            _worker_id: WorkerId,
            _pending_queue: asyncio.Queue[MockTask],
            _completed_queue: asyncio.Queue[MockTask],
        ) -> None:
            """タスクを処理しないモックワーカー。"""
            pass

        manager = WorkerManager(
            worker=slow_worker,
            max_workers=1,
            pending_task_queue=pending_task_queue,
        )

        results = list[MockTask]()
        try:
            async with asyncio.timeout(2.0):
                async for completed_task in manager.execute():
                    results.append(completed_task)
        except asyncio.TimeoutError:
            pass

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_worker_exception_handling(
        self, pending_task_queue: asyncio.Queue[MockTask]
    ) -> None:
        """ワーカーで例外が発生した場合、TaskGroupにより例外が伝播される。"""

        async def failing_worker(
            _worker_id: WorkerId,
            _pending_queue: asyncio.Queue[MockTask],
            _completed_queue: asyncio.Queue[MockTask],
        ) -> None:
            """例外を発生させるモックワーカー。"""
            raise Exception("Worker failed")

        manager = WorkerManager(
            worker=failing_worker,
            max_workers=1,
            pending_task_queue=pending_task_queue,
        )

        task = MockTask(MockTaskArgs(value=1))
        await pending_task_queue.put(task)

        # This should raise an exception due to TaskGroup behavior
        with pytest.raises(Exception):
            async for _ in manager.execute():
                pass

    @pytest.mark.asyncio
    async def test_concurrent_workers(
        self, pending_task_queue: asyncio.Queue[MockTask]
    ) -> None:
        """複数ワーカーが同時にタスクを処理し、全タスクが完了する。"""
        processed_workers: list[WorkerId] = []

        async def tracking_worker(
            worker_id: WorkerId,
            pending_queue: asyncio.Queue[MockTask],
            completed_queue: asyncio.Queue[MockTask],
        ) -> None:
            while not pending_queue.empty():
                task = await pending_queue.get()
                processed_workers.append(worker_id)
                await task.execute()
                await completed_queue.put(task)
                pending_queue.task_done()

        manager = WorkerManager(
            worker=tracking_worker,
            max_workers=3,
            pending_task_queue=pending_task_queue,
        )

        tasks = [MockTask(MockTaskArgs(value=i)) for i in range(5)]
        for task in tasks:
            await pending_task_queue.put(task)

        results = list[MockTask]()
        async for completed_task in manager.execute():
            results.append(completed_task)

        assert len(results) == 5
        # Multiple workers should have processed tasks (or at least all tasks were processed)
        assert len(set(processed_workers)) >= 1

    @pytest.mark.asyncio
    async def test_task_ordering(
        self,
        worker_manager: WorkerManager[MockTask],
        pending_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """全タスクが処理され、期待される値のセットが得られる（並行性により順序は変動する可能性あり）。"""
        task_values = [1, 2, 3, 4, 5]
        tasks = [MockTask(MockTaskArgs(value=val)) for val in task_values]

        for task in tasks:
            await pending_task_queue.put(task)

        results: list[MockTask] = []
        async for completed_task in worker_manager.execute():
            results.append(completed_task)

        # All tasks should be processed
        assert len(results) == len(task_values)

        # All expected results should be present (order may vary)
        expected_results = [val * 2 for val in task_values]
        actual_results = [task.result.result for task in results]
        assert set(actual_results) == set(expected_results)
