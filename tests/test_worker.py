"""workerモジュールのテスト。"""

import asyncio

import pytest

from pytoolkit_async_worker.worker import (
    PendingTaskQueue,
    Task,
    TaskResultQueue,
    worker,
)


async def mock_task_func(value: int) -> int:
    """入力値を2倍にするモックタスク関数。"""
    return value * 2


async def slow_mock_task_func(value: int) -> int:
    """処理に時間がかかるモックタスク関数。"""
    await asyncio.sleep(0.1)
    return value * 2


async def failing_mock_task_func(value: int) -> int:
    """常に失敗するモックタスク関数。"""
    raise Exception("タスクの実行に失敗しました")


class TestWorker:
    """worker関数のテストクラス。"""

    @pytest.fixture
    def pending_task_queue(self) -> PendingTaskQueue[[int], int]:
        """未処理タスクキューのフィクスチャを作成する。"""
        return PendingTaskQueue[[int], int]()

    @pytest.fixture
    def task_result_queue(self) -> TaskResultQueue[int]:
        """タスク結果キューのフィクスチャを作成する。"""
        return TaskResultQueue[int]()

    @pytest.mark.asyncio
    async def test_worker_processes_single_task(
        self,
        pending_task_queue: PendingTaskQueue[[int], int],
        task_result_queue: TaskResultQueue[int],
    ) -> None:
        """ワーカーが単一タスクを処理し、結果が完了キューに格納される。"""
        task = Task[[int], int](func=mock_task_func, args=(5,), kwargs={})
        await pending_task_queue.put(task)

        await worker(
            pending_task_queue=pending_task_queue,
            task_result_queue=task_result_queue,
        )

        assert pending_task_queue.empty()
        assert not task_result_queue.empty()

        task_result = await task_result_queue.get()
        assert task_result.result.is_ok()
        assert task_result.result.value == 10
        assert task_result.args == (5,)
        assert task_result.kwargs == {}

    @pytest.mark.asyncio
    async def test_worker_processes_multiple_tasks(
        self,
        pending_task_queue: PendingTaskQueue[[int], int],
        task_result_queue: TaskResultQueue[int],
    ) -> None:
        """ワーカーが複数タスクを順次処理し、全ての結果が完了キューに格納される。"""
        tasks = [
            Task[[int], int](func=mock_task_func, args=(1,), kwargs={}),
            Task[[int], int](func=mock_task_func, args=(2,), kwargs={}),
            Task[[int], int](func=mock_task_func, args=(3,), kwargs={}),
        ]

        for task in tasks:
            await pending_task_queue.put(task)

        await worker(
            pending_task_queue=pending_task_queue,
            task_result_queue=task_result_queue,
        )

        assert pending_task_queue.empty()
        assert task_result_queue.qsize() == 3

        results = list[int]()
        while not task_result_queue.empty():
            task_result = await task_result_queue.get()
            assert task_result.result.is_ok()
            results.append(task_result.result.value)

        assert 2 in results
        assert 4 in results
        assert 6 in results

    @pytest.mark.asyncio
    async def test_worker_with_empty_queue(
        self,
        pending_task_queue: PendingTaskQueue[[int], int],
        task_result_queue: TaskResultQueue[int],
    ) -> None:
        """空の未処理キューでワーカーが完了し、完了キューも空のままである。"""
        await worker(
            pending_task_queue=pending_task_queue,
            task_result_queue=task_result_queue,
        )

        assert pending_task_queue.empty()
        assert task_result_queue.empty()

    @pytest.mark.asyncio
    async def test_worker_calls_task_done(
        self,
        pending_task_queue: PendingTaskQueue[[int], int],
        task_result_queue: TaskResultQueue[int],
    ) -> None:
        """ワーカーがタスク処理後にtask_done()を呼び出す。"""
        task = Task[[int], int](func=mock_task_func, args=(1,), kwargs={})
        await pending_task_queue.put(task)

        # task_doneメソッドをモックして呼び出しを追跡
        original_task_done = pending_task_queue.task_done
        task_done_calls = list[bool]()

        def mock_task_done() -> None:
            task_done_calls.append(True)
            return original_task_done()

        pending_task_queue.task_done = mock_task_done

        await worker(
            pending_task_queue=pending_task_queue,
            task_result_queue=task_result_queue,
        )

        assert len(task_done_calls) == 1

    @pytest.mark.asyncio
    async def test_worker_with_kwargs(
        self,
        pending_task_queue: PendingTaskQueue[[int], int],
        task_result_queue: TaskResultQueue[int],
    ) -> None:
        """キーワード引数を含むタスクでもワーカーが正常に動作する。"""

        async def task_with_kwargs(value: int, multiplier: int = 2) -> int:
            return value * multiplier

        task = Task[[int], int](
            func=task_with_kwargs, args=(5,), kwargs={"multiplier": 3}
        )
        await pending_task_queue.put(task)

        await worker(
            pending_task_queue=pending_task_queue,
            task_result_queue=task_result_queue,
        )

        assert pending_task_queue.empty()
        assert not task_result_queue.empty()

        task_result = await task_result_queue.get()
        assert task_result.result.is_ok()
        assert task_result.result.value == 15
        assert task_result.args == (5,)
        assert task_result.kwargs == {"multiplier": 3}

    @pytest.mark.asyncio
    async def test_worker_with_failing_task(
        self,
        pending_task_queue: PendingTaskQueue[[int], int],
        task_result_queue: TaskResultQueue[int],
    ) -> None:
        """タスク実行が失敗した場合、ワーカーが例外を発生させる。"""
        task = Task[[int], int](func=failing_mock_task_func, args=(1,), kwargs={})
        await pending_task_queue.put(task)

        # ワーカーは例外を処理して継続すべき
        await worker(
            pending_task_queue=pending_task_queue,
            task_result_queue=task_result_queue,
        )
        
        # エラー結果が格納されるべき
        assert not task_result_queue.empty()
        task_result = await task_result_queue.get()
        assert task_result.result.is_error()
        assert "タスクの実行に失敗しました" in str(task_result.result.error)

    @pytest.mark.asyncio
    async def test_worker_task_execution_order(
        self,
        pending_task_queue: PendingTaskQueue[[int], int],
        task_result_queue: TaskResultQueue[int],
    ) -> None:
        """ワーカーがタスクをFIFO順で処理し、結果が同じ順序で出力される。"""
        values = [1, 2, 3, 4, 5]
        tasks = [
            Task[[int], int](func=mock_task_func, args=(val,), kwargs={})
            for val in values
        ]

        for task in tasks:
            await pending_task_queue.put(task)

        await worker(
            pending_task_queue=pending_task_queue,
            task_result_queue=task_result_queue,
        )

        # タスクはFIFO順で処理されるべき
        results = list[int]()
        while not task_result_queue.empty():
            task_result = await task_result_queue.get()
            assert task_result.result.is_ok()
            results.append(task_result.result.value)

        expected_results = [val * 2 for val in values]
        assert results == expected_results

    @pytest.mark.asyncio
    async def test_worker_concurrent_execution(self) -> None:
        """複数ワーカーが同時実行され、全タスクが処理される。"""
        pending_queue = PendingTaskQueue[[int], int]()
        result_queue = TaskResultQueue[int]()

        # 複数のタスクを追加
        tasks = [
            Task[[int], int](func=mock_task_func, args=(i,), kwargs={})
            for i in range(10)
        ]
        for task in tasks:
            await pending_queue.put(task)

        # 複数のワーカーを並行実行
        workers = [worker(pending_queue, result_queue) for _ in range(3)]

        await asyncio.gather(*workers)

        # 全てのタスクが処理されるべき
        assert pending_queue.empty()
        assert result_queue.qsize() == 10

    @pytest.mark.asyncio
    async def test_worker_with_slow_task(
        self,
        pending_task_queue: PendingTaskQueue[[int], int],
        task_result_queue: TaskResultQueue[int],
    ) -> None:
        """実行に時間のかかるタスクでもワーカーが待機し、正しい結果を出力する。"""
        task = Task[[int], int](func=slow_mock_task_func, args=(5,), kwargs={})
        await pending_task_queue.put(task)

        await worker(
            pending_task_queue=pending_task_queue,
            task_result_queue=task_result_queue,
        )

        assert pending_task_queue.empty()
        assert not task_result_queue.empty()

        task_result = await task_result_queue.get()
        assert task_result.result.is_ok()
        assert task_result.result.value == 10
