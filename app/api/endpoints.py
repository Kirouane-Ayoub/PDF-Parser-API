from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import time
from typing import List

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import (
    PDFProcessResponse,
    ErrorResponse,
    PageResult,
    HealthResponse,
)
from app.services.pdf_processor import PDFProcessor
from app.services.openai_client import OpenAIClient
from app.utils.exceptions import PDFProcessingError, create_http_exception

logger = get_logger(__name__)
router = APIRouter()

# Dependency injection
def get_pdf_processor() -> PDFProcessor:
    return PDFProcessor()


def get_openai_client() -> OpenAIClient:
    return OpenAIClient()


@router.post(
    "/process-pdf",
    response_model=PDFProcessResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def process_pdf(
    file: UploadFile = File(..., description="PDF file to process"),
    pdf_processor: PDFProcessor = Depends(get_pdf_processor),
    openai_client: OpenAIClient = Depends(get_openai_client),
):
    """
    Process a PDF file by extracting pages as images and sending them to OpenAI API.

    - **file**: PDF file to upload and process
    - Returns structured JSON with page-by-page processing results
    """
    start_time = time.time()

    try:
        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        logger.info(
            "processing_pdf_started",
            filename=file.filename,
            content_type=file.content_type,
        )

        # Extract pages from PDF
        pages_data = await pdf_processor.process_pdf_stream(file.file)

        if not pages_data:
            raise HTTPException(status_code=400, detail="No pages found in PDF file")

        # Process pages through OpenAI API
        api_results = await openai_client.process_batch(pages_data)

        # Prepare response
        results: List[PageResult] = []
        errors: List[str] = []
        processed_count = 0

        for page_num, api_response, metadata, error in api_results:
            if error:
                errors.append(f"Page {page_num}: {error}")
                results.append(
                    PageResult(
                        page_number=page_num,
                        processed_output={},
                        metadata=metadata,
                        error=error,
                    )
                )
            else:
                processed_count += 1
                results.append(
                    PageResult(
                        page_number=page_num,
                        processed_output=api_response,
                        metadata=metadata,
                    )
                )

        processing_time = time.time() - start_time

        logger.info(
            "processing_pdf_completed",
            filename=file.filename,
            total_pages=len(pages_data),
            processed_pages=processed_count,
            processing_time=processing_time,
            errors_count=len(errors),
        )

        return PDFProcessResponse(
            success=len(errors) == 0,
            total_pages=len(pages_data),
            processed_pages=processed_count,
            results=results,
            processing_time=processing_time,
            errors=errors if errors else None,
        )

    except PDFProcessingError as e:
        logger.error("pdf_processing_error", error=str(e), details=e.details)
        raise create_http_exception(e)

    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Internal server error occurred during processing"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version=settings.app_version)


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
