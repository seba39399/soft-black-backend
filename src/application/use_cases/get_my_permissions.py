"""Caso de uso: qué recursos (dashboards) puede ver el usuario."""

from collections.abc import Iterable
from dataclasses import dataclass

from shared.authz import resources_for


@dataclass(frozen=True)
class MyPermissions:
    username: str
    groups: list[str]
    resources: list[str]


def get_my_permissions(username: str, groups: Iterable[str]) -> MyPermissions:
    group_list = sorted(set(groups))
    return MyPermissions(username=username, groups=group_list, resources=resources_for(group_list))
