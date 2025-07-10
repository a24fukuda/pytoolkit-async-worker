from typing import Generic, TypeVar

T = TypeVar("T")


class Optionl(Generic[T]):
    def __init__(self, value: T | None):
        self._value = value

    def is_some(self) -> bool:
        return self._value is not None

    def is_none(self) -> bool:
        return self._value is None

    def unwrap(self) -> T:
        if self._value is None:
            raise ValueError("Called unwrap on None")
        return self._value

    def unwrap_or(self, default: T) -> T:
        return self._value if self._value is not None else default
