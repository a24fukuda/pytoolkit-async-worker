from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar
from uuid import UUID
from uuid import uuid4 as uuid

from pytoolkit_rustlike import Option, Result

T = TypeVar("T")


@dataclass(frozen=True)
class Task(ABC, Generic[T]):
    id: UUID = field(default_factory=uuid, init=False)

    @abstractmethod
    async def execute(self) -> T:
        raise NotImplementedError()


@dataclass(frozen=True)
class TaskResult(Generic[T]):
    task: Task[T]
    result: Result[Option[T]]
