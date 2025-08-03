from fastapi import HTTPException
from typing import Optional


class PDFProcessingError(Exception):
    """Base exception for PDF processing errors."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class InvalidFileError(PDFProcessingError):
    """Raised when file is invalid or corrupted."""

    pass


class FileSizeError(PDFProcessingError):
    """Raised when file size exceeds limits."""

    pass


class APICallError(PDFProcessingError):
    """Raised when OpenAI API call fails."""

    pass


class ProcessingTimeoutError(PDFProcessingError):
    """Raised when processing times out."""

    pass


def create_http_exception(
    error: PDFProcessingError, status_code: int = 400
) -> HTTPException:
    """Convert custom exception to HTTP exception."""
    return HTTPException(
        status_code=status_code,
        detail={"error": error.message, "details": error.details},
    )
