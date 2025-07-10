"""resultモジュールのテスト。"""

import pytest

from pytoolkit_async_worker.result import Result


class TestResult:
    """Resultクラスのテストクラス。"""

    def test_result_ok_creation(self) -> None:
        """正常値でResultインスタンスが作成される。"""
        result = Result[int](42)

        assert result.is_ok()
        assert not result.is_error()
        assert result.value == 42

    def test_result_error_creation(self) -> None:
        """例外でResultインスタンスが作成される。"""
        error = ValueError("テストエラー")
        result = Result[int](error)

        assert result.is_error()
        assert not result.is_ok()
        assert result.error == error

    def test_result_ok_value_access(self) -> None:
        """正常値のResultから値にアクセスできる。"""
        result = Result[str]("成功")

        assert result.value == "成功"

    def test_result_error_value_access_raises(self) -> None:
        """エラーのResultから値にアクセスすると例外が発生する。"""
        error = RuntimeError("実行時エラー")
        result = Result[int](error)

        with pytest.raises(RuntimeError, match="実行時エラー"):
            _ = result.value

    def test_result_ok_error_access_raises(self) -> None:
        """正常値のResultからエラーにアクセスすると例外が発生する。"""
        result = Result[int](42)

        with pytest.raises(ValueError, match="Called error on Ok"):
            _ = result.error

    def test_result_error_error_access(self) -> None:
        """エラーのResultからエラーにアクセスできる。"""
        error = TypeError("型エラー")
        result = Result[str](error)

        assert result.error == error

    def test_result_different_types(self) -> None:
        """異なる型でもResultが正しく動作する。"""
        # 文字列型
        string_result = Result[str]("テスト文字列")
        assert string_result.is_ok()
        assert string_result.value == "テスト文字列"

        # リスト型
        list_result = Result[list[int]]([1, 2, 3])
        assert list_result.is_ok()
        assert list_result.value == [1, 2, 3]

        # 辞書型
        dict_result = Result[dict[str, int]]({"key": 123})
        assert dict_result.is_ok()
        assert dict_result.value == {"key": 123}

    def test_result_none_value(self) -> None:
        """None値でもResultが正しく動作する。"""
        result = Result[None](None)

        assert result.is_ok()
        assert result.value is None

    def test_result_equality(self) -> None:
        """同じ値を持つResultインスタンスが等価と判定される。"""
        result1 = Result[int](42)
        result2 = Result[int](42)
        result3 = Result[int](100)

        assert result1 == result2
        assert result1 != result3

        # エラーの場合
        error = ValueError("同じエラー")
        error_result1 = Result[int](error)
        error_result2 = Result[int](error)
        different_error = ValueError("異なるエラー")
        error_result3 = Result[int](different_error)

        assert error_result1 == error_result2
        assert error_result1 != error_result3

    def test_result_immutability(self) -> None:
        """Resultインスタンスが不変オブジェクトであることを確認。"""
        result = Result[int](42)

        # Frozen dataclass should prevent modification
        with pytest.raises(AttributeError):
            result._value = 100  # type: ignore

    def test_result_with_complex_objects(self) -> None:
        """複雑なオブジェクトでもResultが正しく動作する。"""

        class CustomObject:
            def __init__(self, name: str, value: int) -> None:
                self.name = name
                self.value = value

            def __eq__(self, other: object) -> bool:
                if not isinstance(other, CustomObject):
                    return False
                return self.name == other.name and self.value == other.value

        obj = CustomObject("テスト", 42)
        result = Result[CustomObject](obj)

        assert result.is_ok()
        assert result.value == obj
        assert result.value.name == "テスト"
        assert result.value.value == 42

    def test_result_exception_types(self) -> None:
        """様々な例外タイプでResultが正しく動作する。"""
        # ValueError
        value_error = ValueError("値エラー")
        result1 = Result[int](value_error)
        assert result1.is_error()
        assert isinstance(result1.error, ValueError)

        # TypeError
        type_error = TypeError("型エラー")
        result2 = Result[str](type_error)
        assert result2.is_error()
        assert isinstance(result2.error, TypeError)

        # RuntimeError
        runtime_error = RuntimeError("実行時エラー")
        result3 = Result[bool](runtime_error)
        assert result3.is_error()
        assert isinstance(result3.error, RuntimeError)

        # カスタム例外
        class CustomError(Exception):
            pass

        custom_error = CustomError("カスタムエラー")
        result4 = Result[float](custom_error)
        assert result4.is_error()
        assert isinstance(result4.error, CustomError)
