from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import uuid4 as uuid

from .optional import Optionl

TaskArgs = TypeVar("TaskArgs")
TaskResult = TypeVar("TaskResult")


class BaseTask(ABC, Generic[TaskArgs, TaskResult]):
    def __init__(self, args: TaskArgs):
        self.id = uuid()
        self.args = args
        self.result = Optionl[TaskResult](None)

    @abstractmethod
    async def execute(self) -> TaskResult:
        pass


Task = TypeVar("Task", bound=BaseTask[Any, Any])
type AnyTask = BaseTask[Any, Any]
