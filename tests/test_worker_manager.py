"""Tests for worker_manager module."""

import asyncio

import pytest

from pytoolkit_async_worker.worker import (
    Task,
    TaskResult,
    WorkerManager,
    worker,
)


async def mock_task_func(value: int) -> int:
    """Mock task function that doubles the input value."""
    return value * 2


class TestWorkerManager:
    """WorkerManagerのテストクラス。"""

    @pytest.fixture
    def worker_manager(self) -> WorkerManager[[int], int]:
        """WorkerManagerインスタンスを作成する。"""
        return WorkerManager(
            worker=worker,
            max_workers=2,
        )

    @pytest.mark.asyncio
    async def test_init(self) -> None:
        """WorkerManagerが指定されたパラメーターで初期化され、空のワーカーリストを持つ。"""
        manager = WorkerManager[[int], int](
            worker=worker,
            max_workers=3,
        )

        assert manager.worker == worker
        assert manager.max_workers == 3
        assert isinstance(manager.pending_task_queue, asyncio.Queue)
        assert isinstance(manager.task_result_queue, asyncio.Queue)
        assert manager.workers == []

    @pytest.mark.asyncio
    async def test_execute_single_task(
        self,
        worker_manager: WorkerManager[[int], int],
    ) -> None:
        """単一タスクが実行され、期待される結果が得られる。"""
        await worker_manager.add_task(mock_task_func, 5)

        results = list[TaskResult[int]]()
        async for task_result in worker_manager.execute():
            results.append(task_result)

        assert len(results) == 1
        assert results[0].result.is_ok()
        assert results[0].result.value == 10
        assert results[0].args == (5,)
        assert results[0].kwargs == {}

    @pytest.mark.asyncio
    async def test_execute_multiple_tasks(
        self,
        worker_manager: WorkerManager[[int], int],
    ) -> None:
        """複数タスクが実行され、全ての期待される結果が得られる。"""
        await worker_manager.add_task(mock_task_func, 1)
        await worker_manager.add_task(mock_task_func, 2)
        await worker_manager.add_task(mock_task_func, 3)

        results = list[TaskResult[int]]()
        async for task_result in worker_manager.execute():
            results.append(task_result)

        assert len(results) == 3
        result_values = list[int]()
        for task_result in results:
            assert task_result.result.is_ok()
            result_values.append(task_result.result.value)
        assert 2 in result_values
        assert 4 in result_values
        assert 6 in result_values

    @pytest.mark.asyncio
    async def test_execute_empty_queue(
        self, worker_manager: WorkerManager[[int], int]
    ) -> None:
        """空のタスクキューでワーカーが完了し、結果が出力されない。"""
        results = list[TaskResult[int]]()
        try:
            async with asyncio.timeout(2.0):
                async for task_result in worker_manager.execute():
                    results.append(task_result)
        except asyncio.TimeoutError:
            pass

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_worker_creation(
        self,
        worker_manager: WorkerManager[[int], int],
    ) -> None:
        """指定された数のワーカーが作成され、全てがasyncio.Taskインスタンスである。"""
        await worker_manager.add_task(mock_task_func, 1)

        # Start execution to create workers
        results = list[TaskResult[int]]()
        async for task_result in worker_manager.execute():
            results.append(task_result)
            break

        # Workers should be created after execution starts
        assert len(worker_manager.workers) == 2
        for worker_task in worker_manager.workers:
            assert isinstance(worker_task, asyncio.Task)

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        """ワーカーがタスクを処理しない場合、タイムアウトで終了し、結果が出力されない。"""

        async def slow_worker(
            _pending_queue: asyncio.Queue[Task[[int], int]],
            _result_queue: asyncio.Queue[TaskResult[int]],
        ) -> None:
            """タスクを処理しないモックワーカー。"""
            pass

        manager = WorkerManager[[int], int](
            worker=slow_worker,
            max_workers=1,
        )

        results = list[TaskResult[int]]()
        try:
            async with asyncio.timeout(2.0):
                async for task_result in manager.execute():
                    results.append(task_result)
        except asyncio.TimeoutError:
            pass

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_worker_exception_handling(self) -> None:
        """ワーカーで例外が発生した場合、TaskGroupにより例外が伝播される。"""

        async def failing_worker(
            _pending_queue: asyncio.Queue[Task[[int], int]],
            _result_queue: asyncio.Queue[TaskResult[int]],
        ) -> None:
            """例外を発生させるモックワーカー。"""
            raise Exception("Worker failed")

        manager = WorkerManager[[int], int](
            worker=failing_worker,
            max_workers=1,
        )

        await manager.add_task(mock_task_func, 1)

        # This should raise an exception due to TaskGroup behavior
        with pytest.raises(Exception):
            async for _ in manager.execute():
                pass

    @pytest.mark.asyncio
    async def test_concurrent_workers(self) -> None:
        """複数ワーカーが同時にタスクを処理し、全タスクが完了する。"""
        manager = WorkerManager[[int], int](
            worker=worker,
            max_workers=3,
        )

        for i in range(5):
            await manager.add_task(mock_task_func, i)

        results = list[TaskResult[int]]()
        async for task_result in manager.execute():
            results.append(task_result)

        assert len(results) == 5
        # All tasks should be processed
        result_values = list[int]()
        for task_result in results:
            assert task_result.result.is_ok()
            result_values.append(task_result.result.value)
        expected_values = [i * 2 for i in range(5)]
        assert set(result_values) == set(expected_values)

    @pytest.mark.asyncio
    async def test_task_ordering(
        self,
        worker_manager: WorkerManager[[int], int],
    ) -> None:
        """全タスクが処理され、期待される値のセットが得られる（並行性により順序は変動する可能性あり）。"""
        task_values = [1, 2, 3, 4, 5]

        for val in task_values:
            await worker_manager.add_task(mock_task_func, val)

        results = list[TaskResult[int]]()
        async for task_result in worker_manager.execute():
            results.append(task_result)

        # All tasks should be processed
        assert len(results) == len(task_values)

        # All expected results should be present (order may vary)
        expected_results = [val * 2 for val in task_values]
        actual_results = list[int]()
        for task_result in results:
            assert task_result.result.is_ok()
            actual_results.append(task_result.result.value)
        assert set(actual_results) == set(expected_results)
