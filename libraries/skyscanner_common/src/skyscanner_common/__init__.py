"""
Infrastructure shared by every Skyscanner service - configuration, logging, mongo access, storage and identity.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from skyscanner_common.api import create_application, register_exception_handlers
from skyscanner_common.datetime_utils import ensure_utc, utc_now
from skyscanner_common.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    SkyscannerError,
    StorageError,
    ValidationError,
)
from skyscanner_common.identity import build_user_context, permissions_for_roles
from skyscanner_common.ids import new_id
from skyscanner_common.logging_utils import configure_logging, get_logger
from skyscanner_common.mongo import MongoProvider
from skyscanner_common.object_storage import ObjectStorageClient
from skyscanner_common.settings import (
    AuthSettings,
    CorsSettings,
    MailSettings,
    MongoSettings,
    ServiceSettings,
    StorageSettings,
)
from skyscanner_common.text import file_suffix, slugify
