import pytest

from adapters.inbound.auth.identity import UnauthenticatedError, identity_from_claims, parse_groups


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("[admin ventas]", ("admin", "ventas")),
        ("[admin]", ("admin",)),
        ("admin,ventas", ("admin", "ventas")),
        (["admin", "ventas"], ("admin", "ventas")),
        ("[]", ()),
        (None, ()),
        (42, ()),
    ],
)
def test_parse_groups(raw: object, expected: tuple[str, ...]) -> None:
    assert parse_groups(raw) == expected


def test_sin_claims_es_no_autenticado() -> None:
    with pytest.raises(UnauthenticatedError):
        identity_from_claims(None)
