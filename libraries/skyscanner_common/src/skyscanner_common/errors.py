"""
The domain errors every service raises, kept transport agnostic so that the API layer maps them to status codes.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- ERRORS ----- #


class SkyscannerError(Exception):
    """
    The base of every error raised on purpose by a Skyscanner service.
    """

    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        """
        Keep the human readable message together with the structured details of the failure.

        :param message: Explanation of what went wrong.
        :param details: Extra key and value pairs describing the failure.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(SkyscannerError):
    """
    Raised when a document was addressed by an identifier that does not exist.
    """


class ConflictError(SkyscannerError):
    """
    Raised when a write would break a uniqueness rule of the system.
    """


class ValidationError(SkyscannerError):
    """
    Raised when a payload does not satisfy the dynamic schema declared for its industry.
    """


class PermissionDeniedError(SkyscannerError):
    """
    Raised when the identity handed over by the reverse proxy lacks the capability the endpoint needs.
    """


class StorageError(SkyscannerError):
    """
    Raised when the object storage refused an upload, a download or a deletion.
    """
