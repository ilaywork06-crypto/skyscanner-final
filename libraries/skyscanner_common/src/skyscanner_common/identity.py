"""
Translation of the headers injected by the authenticating reverse proxy into the identity the services work with.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Mapping

from skyscanner_models.common import UserContext
from skyscanner_models.enums import Permission, Role

from skyscanner_common.settings import AuthSettings
from skyscanner_common.text import split_list

# ----- CONSTS ----- #

ANONYMOUS_USER: str = "anonymous"

VIEWER_PERMISSIONS: tuple[Permission, ...] = (
    Permission.EVENT_READ,
    Permission.FILE_DOWNLOAD,
    Permission.SUBSCRIPTION_MANAGE,
)

EDITOR_PERMISSIONS: tuple[Permission, ...] = VIEWER_PERMISSIONS + (
    Permission.EVENT_CREATE,
    Permission.EVENT_UPDATE,
    Permission.ENTITY_MANAGE,
    Permission.FILE_UPLOAD,
    Permission.TEMPLATE_MANAGE,
)

ADMIN_PERMISSIONS: tuple[Permission, ...] = EDITOR_PERMISSIONS + (
    Permission.EVENT_DELETE,
    Permission.FIELD_MANAGE,
    Permission.INDUSTRY_MANAGE,
)

ROLE_PERMISSIONS: dict[Role, tuple[Permission, ...]] = {
    Role.VIEWER: VIEWER_PERMISSIONS,
    Role.EDITOR: EDITOR_PERMISSIONS,
    Role.ADMIN: ADMIN_PERMISSIONS,
}

# ----- FUNCTIONS ----- #


def permissions_for_roles(roles: list[Role]) -> list[Permission]:
    """
    Collect the union of the capabilities granted by a set of roles.

    :param roles: Roles the caller was granted by the reverse proxy.
    :return: The capabilities the caller may use, without duplicates.
    """
    granted: list[Permission] = []
    for role in roles:
        for permission in ROLE_PERMISSIONS.get(role, ()):
            if permission not in granted:
                granted.append(permission)

    return granted


def parse_roles(raw_roles: str) -> list[Role]:
    """
    Turn the comma separated roles header into the roles the system knows, dropping anything unknown.

    :param raw_roles: Raw value of the roles header.
    :return: The recognised roles carried by the header.
    """
    roles: list[Role] = []
    for candidate in split_list(raw_roles):
        try:
            role = Role(candidate.lower())
        except ValueError:
            continue
        if role not in roles:
            roles.append(role)

    return roles


def build_user_context(headers: Mapping[str, str], settings: AuthSettings) -> UserContext:
    """
    Build the caller identity from the request headers, falling back to the configured anonymous identity.

    :param headers: Headers of the incoming request.
    :param settings: Names of the headers the reverse proxy injects.
    :return: The identity the request is handled on behalf of.
    """
    lowered = {key.lower(): value for key, value in headers.items()}
    username = lowered.get(settings.user_header.lower(), "").strip()
    raw_roles = lowered.get(settings.roles_header.lower(), "").strip()

    if not username and settings.allow_anonymous:
        username = ANONYMOUS_USER
        raw_roles = raw_roles or settings.anonymous_roles_raw

    roles = parse_roles(raw_roles)

    return UserContext(
        username=username or ANONYMOUS_USER,
        email=lowered.get(settings.email_header.lower()) or None,
        roles=roles,
        industries=split_list(lowered.get(settings.industries_header.lower(), "")),
        permissions=permissions_for_roles(roles),
    )
