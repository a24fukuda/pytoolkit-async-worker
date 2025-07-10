"""Tests for task module."""

import asyncio
from dataclasses import dataclass
from uuid import UUID

import pytest

from pytoolkit_async_worker.optional import Optionl
from pytoolkit_async_worker.task import BaseTask


@dataclass
class MockTaskArgs:
    """Mock task arguments."""
    value: int
    name: str


@dataclass
class MockTaskResult:
    """Mock task result."""
    result: int
    processed_name: str


class ConcreteTask(BaseTask[MockTaskArgs, MockTaskResult]):
    """Concrete implementation of Task for testing."""

    def __init__(self, args: MockTaskArgs) -> None:
        super().__init__(args)

    async def execute(self) -> MockTaskResult:
        result = MockTaskResult(
            result=self.args.value * 2, processed_name=self.args.name.upper()
        )
        self.result = Optionl(result)
        return result


class TestMockClasses:
    """Mock classes used in tests."""

    def test_mock_args_creation(self) -> None:
        """MockTaskArgsインスタンスが正しい属性で作成される。"""
        args = MockTaskArgs(value=10, name="test")
        assert args.value == 10
        assert args.name == "test"

    def test_mock_args_equality(self) -> None:
        """同じ値を持つMockTaskArgsインスタンスが等価と判定され、異なる値を持つインスタンスが非等価と判定される。"""
        args1 = MockTaskArgs(value=10, name="test")
        args2 = MockTaskArgs(value=10, name="test")
        args3 = MockTaskArgs(value=20, name="test")

        assert args1 == args2
        assert args1 != args3

    def test_mock_result_creation(self) -> None:
        """MockTaskResultインスタンスが正しい属性で作成される。"""
        result = MockTaskResult(result=20, processed_name="TEST")
        assert result.result == 20
        assert result.processed_name == "TEST"

    def test_mock_result_equality(self) -> None:
        """同じ値を持つMockTaskResultインスタンスが等価と判定される。"""
        result1 = MockTaskResult(result=20, processed_name="TEST")
        result2 = MockTaskResult(result=20, processed_name="TEST")
        result3 = MockTaskResult(result=30, processed_name="TEST")

        assert result1 == result2
        assert result1 != result3


class TestTask:
    """BaseTask基底クラスのテストクラス。"""

    def test_task_initialization(self) -> None:
        """BaseTaskインスタンスが一意のID、指定された引数、およびNoneの結果で初期化される。"""
        args = MockTaskArgs(value=5, name="test")
        task = ConcreteTask(args)

        assert task.args == args
        assert task.result.is_none()
        assert isinstance(task.id, UUID)

    def test_task_unique_ids(self) -> None:
        """異なるBaseTaskインスタンスが各々異なるUUIDを持つ。"""
        args = MockTaskArgs(value=5, name="test")
        task1 = ConcreteTask(args)
        task2 = ConcreteTask(args)

        assert task1.id != task2.id
        assert isinstance(task1.id, UUID)
        assert isinstance(task2.id, UUID)

    @pytest.mark.asyncio
    async def test_task_execution(self) -> None:
        """execute()を呼び出すと結果が設定され、同じ結果が返される。"""
        args = MockTaskArgs(value=5, name="test")
        task = ConcreteTask(args)

        assert task.result.is_none()

        result = await task.execute()

        assert result is not None
        assert result.result == 10
        assert result.processed_name == "TEST"
        assert task.result.unwrap() == result

    @pytest.mark.asyncio
    async def test_task_execution_multiple_times(self) -> None:
        """同じタスクを複数回実行しても同じ結果が得られる。"""
        args = MockTaskArgs(value=5, name="test")
        task = ConcreteTask(args)

        first_result = await task.execute()

        second_result = await task.execute()

        # Results should be the same (task is deterministic)
        assert first_result == second_result

    def test_task_args_accessibility(self) -> None:
        """BaseTask作成後に引数にアクセスできる。"""
        args = MockTaskArgs(value=5, name="test")
        task = ConcreteTask(args)

        # Args should be accessible
        assert task.args.value == 5
        assert task.args.name == "test"

    def test_task_result_accessibility(self) -> None:
        """BaseTask実行後に結果にアクセスできる。"""
        args = MockTaskArgs(value=5, name="test")
        task = ConcreteTask(args)

        # Execute the task
        import asyncio

        asyncio.run(task.execute())

        # Result should be accessible
        assert task.result.is_some()
        assert task.result.unwrap().result == 10
        assert task.result.unwrap().processed_name == "TEST"

    def test_task_generic_typing(self) -> None:
        """BaseTaskの引数と結果が正しい型でアクセスできる。"""
        args = MockTaskArgs(value=5, name="test")
        task = ConcreteTask(args)

        # Type hints should work correctly
        assert isinstance(task.args, MockTaskArgs)

        # Before execution, result should be None
        assert task.result.is_none()

        # After execution, result should be the correct type
        import asyncio

        asyncio.run(task.execute())
        assert isinstance(task.result.unwrap(), MockTaskResult)

    def test_task_with_different_arg_types(self) -> None:
        """異なる引数型でもBaseTaskが正しく動作し、期待される結果が得られる。"""

        @dataclass
        class SimpleArgs:
            count: int

        @dataclass
        class SimpleResult:
            doubled: int

        class SimpleTask(BaseTask[SimpleArgs, SimpleResult]):
            def __init__(self, args: SimpleArgs) -> None:
                super().__init__(args)

            async def execute(self) -> SimpleResult:
                result = SimpleResult(doubled=self.args.count * 2)
                self.result = Optionl(result)
                return result

        args = SimpleArgs(count=7)
        task = SimpleTask(args)

        asyncio.run(task.execute())

        assert task.result.is_some()
        assert task.result.unwrap().doubled == 14

    def test_task_str_representation(self) -> None:
        """BaseTaskインスタンスの文字列表現にクラス名が含まれる。"""
        args = MockTaskArgs(value=5, name="test")
        task = ConcreteTask(args)

        # Task should have a reasonable string representation
        task_str = str(task)
        assert "ConcreteTask" in task_str or "Task" in task_str

    def test_task_equality(self) -> None:
        """同じ引数でも異なるBaseTaskインスタンスは非等価と判定され、同じインスタンスは等価と判定される。"""
        args1 = MockTaskArgs(value=5, name="test")
        args2 = MockTaskArgs(value=5, name="test")

        task1 = ConcreteTask(args1)
        task2 = ConcreteTask(args2)

        # Tasks should not be equal even with same args (different IDs)
        assert task1 != task2
        assert task1.id != task2.id

        # Task should be equal to itself
        assert task1 == task1
