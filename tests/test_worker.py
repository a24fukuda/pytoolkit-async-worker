"""workerモジュールのテスト。"""

import asyncio
from dataclasses import dataclass

import pytest

from pytoolkit_async_worker.task import Task
from pytoolkit_async_worker.worker import (
    PendingTaskQueue,
    worker,
)


@dataclass(frozen=True)
class MockTask(Task[int]):
    value: int

    async def execute(self) -> int:
        return self.value * 2


@dataclass(frozen=True)
class SlowMockTask(Task[int]):
    value: int

    async def execute(self) -> int:
        await asyncio.sleep(0.1)
        return self.value * 2


@dataclass(frozen=True)
class FailingMockTask(Task[int]):
    value: int

    async def execute(self) -> int:
        raise Exception("タスクの実行に失敗しました")


@dataclass(frozen=True)
class KwargsTask(Task[int]):
    value: int
    multiplier: int = 2

    async def execute(self) -> int:
        return self.value * self.multiplier


class TestWorker:
    @pytest.fixture
    def pending_task_queue(self) -> PendingTaskQueue[int]:
        return PendingTaskQueue[int]()

    @pytest.mark.asyncio
    async def test_worker_processes_single_task(
        self, pending_task_queue: PendingTaskQueue[int]
    ):
        task = MockTask(5)
        await pending_task_queue.put(task)
        async for task_result in worker(pending_task_queue):
            assert task_result.result.is_ok()
            assert task_result.result.unwrap().unwrap() == 10
        assert pending_task_queue.empty()

    @pytest.mark.asyncio
    async def test_worker_processes_multiple_tasks(
        self, pending_task_queue: PendingTaskQueue[int]
    ):
        tasks = [MockTask(1), MockTask(2), MockTask(3)]
        for task in tasks:
            await pending_task_queue.put(task)
        results: list[int] = []
        async for task_result in worker(pending_task_queue):
            assert task_result.result.is_ok()
            results.append(task_result.result.unwrap().unwrap())
        assert pending_task_queue.empty()
        assert 2 in results
        assert 4 in results
        assert 6 in results

    @pytest.mark.asyncio
    async def test_worker_with_empty_queue(
        self, pending_task_queue: PendingTaskQueue[int]
    ):
        results = [r async for r in worker(pending_task_queue)]
        assert pending_task_queue.empty()
        assert results == []

    @pytest.mark.asyncio
    async def test_worker_calls_task_done(
        self, pending_task_queue: PendingTaskQueue[int]
    ):
        task = MockTask(1)
        await pending_task_queue.put(task)
        original_task_done = pending_task_queue.task_done
        task_done_calls: list[bool] = []

        def mock_task_done():
            task_done_calls.append(True)
            return original_task_done()

        pending_task_queue.task_done = mock_task_done
        async for _ in worker(pending_task_queue):
            pass
        assert len(task_done_calls) == 1

    @pytest.mark.asyncio
    async def test_worker_with_kwargs(self, pending_task_queue: PendingTaskQueue[int]):
        task = KwargsTask(5, multiplier=3)
        await pending_task_queue.put(task)
        async for task_result in worker(pending_task_queue):
            assert task_result.result.is_ok()
            assert task_result.result.unwrap().unwrap() == 15
        assert pending_task_queue.empty()

    @pytest.mark.asyncio
    async def test_worker_with_failing_task(
        self, pending_task_queue: PendingTaskQueue[int]
    ):
        task = FailingMockTask(1)
        await pending_task_queue.put(task)
        results = [r async for r in worker(pending_task_queue)]
        assert pending_task_queue.empty()
        assert len(results) == 1
        assert results[0].result.is_err()
        assert "タスクの実行に失敗しました" in str(results[0].result.unwrap_err())

    @pytest.mark.asyncio
    async def test_worker_task_execution_order(
        self, pending_task_queue: PendingTaskQueue[int]
    ):
        values = [1, 2, 3, 4, 5]
        tasks = [MockTask(val) for val in values]
        for task in tasks:
            await pending_task_queue.put(task)
        results = [r.result.unwrap().unwrap() async for r in worker(pending_task_queue)]
        assert results == [val * 2 for val in values]

    @pytest.mark.asyncio
    async def test_worker_concurrent_execution(self):
        pending_queue = PendingTaskQueue[int]()
        tasks = [MockTask(i) for i in range(10)]
        for task in tasks:
            await pending_queue.put(task)
        workers = [worker(pending_queue) for _ in range(3)]
        results: list[int] = []
        for coro in workers:
            results.extend([r.result.unwrap().unwrap() async for r in coro])
        assert pending_queue.empty()
        assert sorted(results) == [i * 2 for i in range(10)]

    @pytest.mark.asyncio
    async def test_worker_with_slow_task(
        self, pending_task_queue: PendingTaskQueue[int]
    ):
        task = SlowMockTask(5)
        await pending_task_queue.put(task)
        results: list[int] = [
            r.result.unwrap().unwrap() async for r in worker(pending_task_queue)
        ]
        assert pending_task_queue.empty()
        assert results == [10]
