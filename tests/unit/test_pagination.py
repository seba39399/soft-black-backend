import pytest

from shared.pagination import (
    MAX_LIMIT,
    InvalidCursorError,
    clamp_limit,
    decode_cursor,
    encode_cursor,
)


def test_ida_y_vuelta() -> None:
    position = {"PK": "DASHBOARD_1", "SK": "INDICADOR#007"}
    assert decode_cursor(encode_cursor(position)) == position


def test_sin_posicion_no_hay_cursor() -> None:
    assert encode_cursor(None) is None
    assert decode_cursor(None) is None


@pytest.mark.parametrize("bad", ["%%%", "bm90LWpzb24", "WzEsMl0"])
def test_cursor_invalido(bad: str) -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor(bad)


def test_clamp_limit() -> None:
    assert clamp_limit(None) == 50
    assert clamp_limit(0) == 50
    assert clamp_limit(10_000) == MAX_LIMIT
