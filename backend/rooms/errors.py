"""Errors for the room system."""


class RoomError(Exception):
    """A room-level operation failed.

    ``code`` is a stable machine-readable error code, ``http_status`` maps the
    error onto an HTTP status when it is surfaced over the REST API.
    """

    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
