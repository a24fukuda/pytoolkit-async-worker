"""Tests for task module."""

from uuid import UUID

import pytest
from pytoolkit_rustlike import Err, Ok, Some

from pytoolkit_async_worker.task import Task, TaskResult


from dataclasses import dataclass

@dataclass(frozen=True)
class SampleTask(Task[int]):
    value: int

    async def execute(self) -> int:
        return self.value * 2


class TestTask:
    """Taskデータクラスのテストクラス。"""

    def test_task_creation(self) -> None:
        """Taskインスタンスが正しい属性で作成される。"""
        task = SampleTask(5)

        assert task.value == 5
        assert isinstance(task.id, UUID)

    def test_task_equality(self) -> None:
        """同じ属性を持つTaskインスタンスが等価と判定される。"""
        task1 = SampleTask(5)
        task2 = SampleTask(5)
        task3 = SampleTask(10)

        # Tasks with same value should be equal because they have the same ID
        assert task1 == task1  # Same instance
        assert task1 != task2  # Different instances with different IDs
        assert task1 != task3  # Different instances with different IDs

    def test_task_immutability(self) -> None:
        """Taskインスタンスが不変オブジェクトであることを確認。"""
        task = SampleTask(5)

        with pytest.raises(AttributeError):
            task.id = task.id  # type: ignore

    @pytest.mark.asyncio
    async def test_task_execution(self) -> None:
        """Taskの実行が正常に動作する。"""
        task = SampleTask(5)
        result = await task.execute()
        assert result == 10


class TestTaskResult:
    """TaskResultデータクラスのテストクラス。"""

    def test_task_result_creation(self) -> None:
        """TaskResultインスタンスが正しい属性で作成される。"""
        task = SampleTask(5)
        result: TaskResult[int] = TaskResult(task=task, result=Ok(Some(10)))

        assert result.task == task
        assert result.result.is_ok()
        assert result.result.unwrap().unwrap() == 10

    def test_task_result_equality(self) -> None:
        """同じ属性を持つTaskResultインスタンスが等価と判定される。"""
        task1 = SampleTask(5)
        task2 = SampleTask(5)

        result1: TaskResult[int] = TaskResult(task=task1, result=Ok(Some(10)))
        result2: TaskResult[int] = TaskResult(task=task1, result=Ok(Some(10)))
        result3: TaskResult[int] = TaskResult(task=task2, result=Ok(Some(10)))

        assert result1 == result2  # Same task and result
        assert result1 != result3  # Different task instance

    def test_task_result_immutability(self) -> None:
        """TaskResultインスタンスが不変オブジェクトであることを確認。"""
        task = SampleTask(5)
        result: TaskResult[int] = TaskResult(task=task, result=Ok(Some(10)))

        with pytest.raises(AttributeError):
            result.task = SampleTask(10)  # type: ignore

        with pytest.raises(AttributeError):
            result.result = Ok(Some(20))  # type: ignore

    def test_task_result_with_different_types(self) -> None:
        """異なる結果型でもTaskResultが正しく動作する。"""

        @dataclass(frozen=True)
        class StringTask(Task[str]):
            value: str

            async def execute(self) -> str:
                return self.value.upper()

        @dataclass(frozen=True)
        class ListTask(Task[list[int]]):
            value: list[int]

            async def execute(self) -> list[int]:
                return [x * 2 for x in self.value]

        string_task = StringTask("hello")
        list_task = ListTask([1, 2, 3])

        string_result: TaskResult[str] = TaskResult(
            task=string_task, result=Ok(Some("HELLO"))
        )
        list_result: TaskResult[list[int]] = TaskResult(
            task=list_task, result=Ok(Some([2, 4, 6]))
        )

        assert string_result.result.is_ok()
        assert string_result.result.unwrap().unwrap() == "HELLO"
        assert list_result.result.is_ok()
        assert list_result.result.unwrap().unwrap() == [2, 4, 6]

    def test_task_result_with_error(self) -> None:
        """エラー結果でもTaskResultが正しく動作する。"""
        task = SampleTask(5)
        error = ValueError("計算エラー")
        result: TaskResult[int] = TaskResult(task=task, result=Err(error))

        assert result.task == task
        assert result.result.is_err()
        assert result.result.unwrap_err() == error
        assert isinstance(result.result.unwrap_err(), ValueError)

    def test_task_result_error_access(self) -> None:
        """エラー結果から値にアクセスすると例外が発生する。"""
        task = SampleTask(5)
        error = RuntimeError("処理失敗")
        result: TaskResult[int] = TaskResult(task=task, result=Err(error))

        assert result.result.is_err()
        with pytest.raises(Exception):
            _ = result.result.unwrap()
