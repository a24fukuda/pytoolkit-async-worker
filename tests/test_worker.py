"""Tests for worker module."""

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from pytoolkit_async_worker.optional import Optionl
from pytoolkit_async_worker.task import AnyTask, BaseTask
from pytoolkit_async_worker.worker import worker


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
        self.result = Optionl(MockTaskResult(result=self.args.value * 2))
        return self.result.unwrap()


class TestWorker:
    """worker関数のテストクラス。"""

    @pytest.fixture
    def pending_task_queue(self) -> asyncio.Queue[AnyTask]:
        """未処理タスクキューのフィクスチャを作成する。"""
        return asyncio.Queue()

    @pytest.fixture
    def completed_task_queue(self) -> asyncio.Queue[AnyTask]:
        """完了タスクキューのフィクスチャを作成する。"""
        return asyncio.Queue()

    @pytest.mark.asyncio
    async def test_worker_processes_single_task(
        self,
        pending_task_queue: asyncio.Queue[MockTask],
        completed_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """ワーカーが単一タスクを処理し、結果が完了キューに格納される。"""
        task = MockTask(MockTaskArgs(value=5))
        await pending_task_queue.put(task)

        await worker(
            worker_id=1,
            pending_task_queue=pending_task_queue,
            completed_task_queue=completed_task_queue,
        )

        assert pending_task_queue.empty()
        assert not completed_task_queue.empty()

        completed_task = await completed_task_queue.get()
        assert completed_task.result.unwrap().result == 10

    @pytest.mark.asyncio
    async def test_worker_processes_multiple_tasks(
        self,
        pending_task_queue: asyncio.Queue[MockTask],
        completed_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """ワーカーが複数タスクを順次処理し、全ての結果が完了キューに格納される。"""
        tasks = [
            MockTask(MockTaskArgs(value=1)),
            MockTask(MockTaskArgs(value=2)),
            MockTask(MockTaskArgs(value=3)),
        ]

        for task in tasks:
            await pending_task_queue.put(task)

        await worker(
            worker_id=1,
            pending_task_queue=pending_task_queue,
            completed_task_queue=completed_task_queue,
        )

        assert pending_task_queue.empty()
        assert completed_task_queue.qsize() == 3

        results = list[int]()
        while not completed_task_queue.empty():
            completed_task = await completed_task_queue.get()
            results.append(completed_task.result.unwrap().result)

        assert 2 in results
        assert 4 in results
        assert 6 in results

    @pytest.mark.asyncio
    async def test_worker_with_empty_queue(
        self,
        pending_task_queue: asyncio.Queue[MockTask],
        completed_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """空の未処理キューでワーカーが完了し、完了キューも空のままである。"""
        await worker(
            worker_id=1,
            pending_task_queue=pending_task_queue,
            completed_task_queue=completed_task_queue,
        )

        assert pending_task_queue.empty()
        assert completed_task_queue.empty()

    @pytest.mark.asyncio
    async def test_worker_calls_task_done(
        self,
        pending_task_queue: asyncio.Queue[MockTask],
        completed_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """ワーカーがタスク処理後にtask_done()を呼び出す。"""
        task = MockTask(MockTaskArgs(value=1))
        await pending_task_queue.put(task)

        # Mock the task_done method to track calls
        original_task_done = pending_task_queue.task_done
        task_done_calls = list[bool]()

        def mock_task_done() -> Any:
            task_done_calls.append(True)
            return original_task_done()

        pending_task_queue.task_done = mock_task_done

        await worker(
            worker_id=1,
            pending_task_queue=pending_task_queue,
            completed_task_queue=completed_task_queue,
        )

        assert len(task_done_calls) == 1

    @pytest.mark.asyncio
    async def test_worker_id_parameter(
        self,
        pending_task_queue: asyncio.Queue[MockTask],
        completed_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """異なるworker_idでもワーカーが正常に動作し、全タスクが処理される。"""
        # Test with different worker IDs
        for worker_id in [0, 1, 5, 10]:
            await pending_task_queue.put(MockTask(MockTaskArgs(value=1)))
            await worker(
                worker_id=worker_id,
                pending_task_queue=pending_task_queue,
                completed_task_queue=completed_task_queue,
            )

        # Should process all tasks regardless of worker_id
        assert pending_task_queue.empty()
        assert completed_task_queue.qsize() == 4

    @pytest.mark.asyncio
    async def test_worker_with_failing_task(
        self,
        pending_task_queue: asyncio.Queue[AnyTask],
        completed_task_queue: asyncio.Queue[AnyTask],
    ) -> None:
        """タスク実行が失敗した場合、ワーカーが例外を発生させる。"""

        class FailingTask(BaseTask[MockTaskArgs, MockTaskResult]):
            def __init__(self, args: MockTaskArgs) -> None:
                super().__init__(args)

            async def execute(self) -> MockTaskResult:
                raise Exception("Task execution failed")

        failing_task = FailingTask(MockTaskArgs(value=1))
        await pending_task_queue.put(failing_task)

        # Worker should handle the exception and continue
        with pytest.raises(Exception):
            await worker(
                worker_id=1,
                pending_task_queue=pending_task_queue,
                completed_task_queue=completed_task_queue,
            )

    @pytest.mark.asyncio
    async def test_worker_task_execution_order(
        self,
        pending_task_queue: asyncio.Queue[MockTask],
        completed_task_queue: asyncio.Queue[MockTask],
    ) -> None:
        """ワーカーがタスクをFIFO順で処理し、結果が同じ順序で出力される。"""
        values = [1, 2, 3, 4, 5]
        tasks = [MockTask(MockTaskArgs(value=val)) for val in values]

        for task in tasks:
            await pending_task_queue.put(task)

        await worker(
            worker_id=1,
            pending_task_queue=pending_task_queue,
            completed_task_queue=completed_task_queue,
        )

        # Tasks should be processed in FIFO order
        results = list[int]()
        while not completed_task_queue.empty():
            completed_task = await completed_task_queue.get()
            results.append(completed_task.result.unwrap().result)

        expected_results = [val * 2 for val in values]
        assert results == expected_results

    @pytest.mark.asyncio
    async def test_worker_concurrent_execution(self) -> None:
        """複数ワーカーが同時実行され、全タスクが処理される。"""
        pending_queue = asyncio.Queue[MockTask]()
        completed_queue = asyncio.Queue[MockTask]()

        # Add multiple tasks
        tasks = [MockTask(MockTaskArgs(value=i)) for i in range(10)]
        for task in tasks:
            await pending_queue.put(task)

        # Run multiple workers concurrently
        workers = [worker(i, pending_queue, completed_queue) for i in range(3)]

        await asyncio.gather(*workers)

        # All tasks should be processed
        assert pending_queue.empty()
        assert completed_queue.qsize() == 10

    @pytest.mark.asyncio
    async def test_worker_with_slow_task(
        self,
        pending_task_queue: asyncio.Queue[AnyTask],
        completed_task_queue: asyncio.Queue[AnyTask],
    ) -> None:
        """実行に時間のかかるタスクでもワーカーが待機し、正しい結果を出力する。"""

        class SlowTask(BaseTask[MockTaskArgs, MockTaskResult]):
            def __init__(self, args: MockTaskArgs) -> None:
                super().__init__(args)

            async def execute(self) -> MockTaskResult:
                await asyncio.sleep(0.1)  # Simulate slow task
                self.result = Optionl(MockTaskResult(result=self.args.value * 2))
                return self.result.unwrap()

        slow_task = SlowTask(MockTaskArgs(value=5))
        await pending_task_queue.put(slow_task)

        await worker(
            worker_id=1,
            pending_task_queue=pending_task_queue,
            completed_task_queue=completed_task_queue,
        )

        assert pending_task_queue.empty()
        assert not completed_task_queue.empty()

        completed_task = await completed_task_queue.get()
        assert completed_task.result.unwrap().result == 10
