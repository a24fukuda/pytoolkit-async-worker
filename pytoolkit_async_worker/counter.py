import asyncio
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class Counter(Generic[T]):
    def __init__(self, value: T):
        self._value = value
        self._lock = asyncio.Lock()

    async def get(self) -> T:
        async with self._lock:
            return self._value

    async def set(self, value: T) -> None:
        async with self._lock:
            self._value = value

    async def update(self, func: Callable[[T], T]) -> T:
        async with self._lock:
            self._value = func(self._value)
            return self._value
