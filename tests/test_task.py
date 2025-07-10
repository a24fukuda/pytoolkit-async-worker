"""Tests for task module."""

import pytest

from pytoolkit_async_worker.result import Result
from pytoolkit_async_worker.worker import Task, TaskResult


class TestTask:
    """Taskデータクラスのテストクラス。"""

    def test_task_creation(self) -> None:
        """Taskインスタンスが正しい属性で作成される。"""

        async def sample_func(x: int) -> int:
            return x * 2

        task = Task(func=sample_func, args=(5,), kwargs={"test": "value"})

        assert task.func == sample_func
        assert task.args == (5,)
        assert task.kwargs == {"test": "value"}

    def test_task_equality(self) -> None:
        """同じ属性を持つTaskインスタンスが等価と判定される。"""

        async def sample_func(x: int) -> int:
            return x * 2

        task1 = Task(func=sample_func, args=(5,), kwargs={"test": "value"})
        task2 = Task(func=sample_func, args=(5,), kwargs={"test": "value"})
        task3 = Task(func=sample_func, args=(10,), kwargs={"test": "value"})

        assert task1 == task2
        assert task1 != task3

    def test_task_immutability(self) -> None:
        """Taskインスタンスが不変オブジェクトであることを確認。"""

        async def sample_func(x: int) -> int:
            return x * 2

        task = Task(func=sample_func, args=(5,), kwargs={"test": "value"})

        with pytest.raises(AttributeError):
            task.args = (10,)  # type: ignore

        with pytest.raises(AttributeError):
            task.kwargs = {"new": "value"}  # type: ignore


class TestTaskResult:
    """TaskResultデータクラスのテストクラス。"""

    def test_task_result_creation(self) -> None:
        """TaskResultインスタンスが正しい属性で作成される。"""
        result = TaskResult(args=(5,), kwargs={"test": "value"}, result=Result(10))

        assert result.args == (5,)
        assert result.kwargs == {"test": "value"}
        assert result.result.is_ok()
        assert result.result.value == 10

    def test_task_result_equality(self) -> None:
        """同じ属性を持つTaskResultインスタンスが等価と判定される。"""
        result1 = TaskResult(args=(5,), kwargs={"test": "value"}, result=Result(10))
        result2 = TaskResult(args=(5,), kwargs={"test": "value"}, result=Result(10))
        result3 = TaskResult(args=(5,), kwargs={"test": "value"}, result=Result(20))

        assert result1 == result2
        assert result1 != result3

    def test_task_result_immutability(self) -> None:
        """TaskResultインスタンスが不変オブジェクトであることを確認。"""
        result = TaskResult(args=(5,), kwargs={"test": "value"}, result=Result(10))

        with pytest.raises(AttributeError):
            result.args = (10,)  # type: ignore

        with pytest.raises(AttributeError):
            result.result = Result(20)  # type: ignore

    def test_task_result_with_different_types(self) -> None:
        """異なる結果型でもTaskResultが正しく動作する。"""
        string_result = TaskResult(args=("hello",), kwargs={}, result=Result("HELLO"))
        list_result = TaskResult(args=([1, 2, 3],), kwargs={}, result=Result([2, 4, 6]))
        dict_result = TaskResult(
            args=({"key": "value"},), kwargs={}, result=Result({"key": "VALUE"})
        )

        assert string_result.result.is_ok()
        assert string_result.result.value == "HELLO"
        assert list_result.result.is_ok()
        assert list_result.result.value == [2, 4, 6]
        assert dict_result.result.is_ok()
        assert dict_result.result.value == {"key": "VALUE"}

    def test_task_result_with_empty_args_kwargs(self) -> None:
        """空の引数とキーワード引数でもTaskResultが正しく動作する。"""
        result = TaskResult(args=(), kwargs={}, result=Result(42))

        assert result.args == ()
        assert result.kwargs == {}
        assert result.result.is_ok()
        assert result.result.value == 42

    def test_task_result_with_error(self) -> None:
        """エラー結果でもTaskResultが正しく動作する。"""
        error = ValueError("計算エラー")
        result = TaskResult(args=(10,), kwargs={}, result=Result[int](error))

        assert result.args == (10,)
        assert result.kwargs == {}
        assert result.result.is_error()
        assert result.result.error == error
        assert isinstance(result.result.error, ValueError)

    def test_task_result_error_access(self) -> None:
        """エラー結果から値にアクセスすると例外が発生する。"""
        error = RuntimeError("処理失敗")
        result = TaskResult(args=(5,), kwargs={}, result=Result[str](error))

        assert result.result.is_error()
        with pytest.raises(RuntimeError, match="処理失敗"):
            _ = result.result.value
