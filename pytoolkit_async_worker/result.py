from dataclasses import dataclass
from typing import Generic, TypeVar, cast

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    _value: T | Exception

    def is_error(self) -> bool:
        return isinstance(self._value, Exception)

    def is_ok(self) -> bool:
        return not self.is_error()

    @property
    def value(self) -> T:
        if self.is_error():
            raise cast(Exception, self._value)
        return cast(T, self._value)

    @property
    def error(self) -> Exception:
        if self.is_ok():
            raise ValueError("Called error on Ok")
        return cast(Exception, self._value)
