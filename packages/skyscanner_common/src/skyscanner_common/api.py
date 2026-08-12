"""
The web layer every service shares - the application factory, the CORS policy and the domain error handlers.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from skyscanner_common.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    SkyscannerError,
    StorageError,
    ValidationError,
)
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.settings import get_cors_settings

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)
UNPROCESSABLE_CONTENT: int = 422

ERROR_STATUS_CODES: dict[type[SkyscannerError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: UNPROCESSABLE_CONTENT,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    StorageError: status.HTTP_502_BAD_GATEWAY,
}

# ----- FUNCTIONS ----- #


def build_error_body(error: SkyscannerError) -> dict[str, Any]:
    """
    Shape a domain error into the body every service answers failures with.

    :param error: Error raised by the service.
    :return: The body of the error answer.
    """
    return {"detail": error.message, "error": type(error).__name__, "details": error.details}


def register_exception_handlers(app: FastAPI) -> None:
    """
    Map every domain error onto the status code that describes it best.

    :param app: Application the handlers are installed on.
    """

    async def handle(request: Request, exc: Exception) -> JSONResponse:
        """
        Answer a domain error with the status code registered for its type.

        :param request: Request that raised the error.
        :param exc: Error raised while the request was handled.
        :return: The answer describing the failure.
        """
        error = exc if isinstance(exc, SkyscannerError) else SkyscannerError(message=str(exc))
        status_code = ERROR_STATUS_CODES.get(type(error), status.HTTP_500_INTERNAL_SERVER_ERROR)
        LOGGER.warning("%s while handling %s: %s", type(error).__name__, request.url.path, error.message)

        return JSONResponse(status_code=status_code, content=build_error_body(error=error))

    handler: Callable[[Request, Exception], Awaitable[JSONResponse]] = handle
    for error_type in (*ERROR_STATUS_CODES, SkyscannerError):
        app.add_exception_handler(error_type, handler)


def create_application(title: str, version: str, description: str, api_prefix: str = "") -> FastAPI:
    """
    Build a FastAPI application that already carries the shared CORS policy and error handling.

    The interactive documentation is published under the very prefix the reverse proxy forwards to the
    service. Left at the root it would answer only inside the container, because the gateway hands the
    service the whole path it received and nothing outside the prefix ever reaches it.

    :param title: Name the service is documented under.
    :param version: Version the service is documented under.
    :param description: One sentence describing what the service does.
    :param api_prefix: Path the reverse proxy forwards to the service, empty when it is reached directly.
    :return: The prepared application.
    """
    application = FastAPI(
        title=title,
        version=version,
        description=description,
        docs_url=f"{api_prefix}/docs",
        redoc_url=f"{api_prefix}/redoc",
        openapi_url=f"{api_prefix}/openapi.json",
        swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True},
    )
    cors = get_cors_settings()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    register_exception_handlers(app=application)

    return application
